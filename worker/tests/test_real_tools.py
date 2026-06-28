"""Real-tool execution tests, gated behind tool presence (skip locally).

These confirm the genuine analyzer behavior (e.g. checkov actually importing the
external check). They are SKIPPED when the toolchain is absent; real coverage
lives in the docker e2e. They run against a local listener stub so no traffic
ever leaves the host.
"""

from __future__ import annotations

import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app import fetch, templating
from app.analyzers import AnalyzerContext, checkov
from app.models import Mitigations
from tests.conftest import GOOD_SEEDS, GOOD_TOKEN


class _Recorder(BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        _Recorder.hits.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args: object) -> None:  # silence test server logs
        pass


@pytest.fixture
def listener() -> tuple[str, int]:
    _Recorder.hits = []
    server = HTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield "127.0.0.1", port  # type: ignore[misc]
    finally:
        server.shutdown()


@pytest.mark.skipif(
    shutil.which("checkov") is None, reason="checkov not installed (covered by e2e)"
)
def test_checkov_external_check_executes_and_beacons(
    tmp_path: Path, listener: tuple[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The worker-side block normally refuses 127.0.0.1; allow it for this local
    # listener stub so we can assert the payload actually fires.
    from app import ssrf

    monkeypatch.setattr(ssrf, "is_blocked_beacon_host", lambda host: False)

    host, port = listener
    fetch.copy_sample("iac", "checkov_external_checks", tmp_path)
    subs = templating.build_substitutions(
        scan_token="abcdef012345",
        vector="checkov_external_checks",
        listener_host=host,
        listener_port=port,
        block_egress=False,
    )
    templating.apply_to_tree(tmp_path, subs)

    ctx = AnalyzerContext(
        workdir=tmp_path,
        mitigations=Mitigations(),
        scan_token="abcdef012345",
        listener_host=host,
        listener_port=port,
        env={**GOOD_SEEDS},
        seeds=dict(GOOD_SEEDS),
        k8s_token=GOOD_TOKEN,
    )
    result = checkov.run(ctx)
    assert result.triggered is True
    assert result.status == "ok"
    # The imported external check should have beaconed our local listener.
    assert any("/b/abcdef012345/checkov_external_checks" in p for p in _Recorder.hits)
