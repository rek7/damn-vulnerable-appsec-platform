"""End-to-end job flow + /run + /healthz, using temp synthetic seeds.

The secrets module needs no external toolchain, so its default path is exercised
here without any skipif gate. Tool-dependent analyzers are covered by docker e2e.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.job import _fetch_repo, run_job
from app.models import RunMeta


def _secrets_meta() -> RunMeta:
    return RunMeta(
        scan_id="s1",
        scan_token="abcdef012345",
        module="secrets",
        source_type="sample",
        # A non-listener host keeps the worker signal from leaving the sandbox.
        listener_host="example.com",
        listener_port=9000,
    )


def test_secrets_vulnerable_path_finds_and_triggers(seed_env: dict[str, Path]) -> None:
    resp = run_job(_secrets_meta())
    assert resp.status == "completed"
    assert len(resp.analyzers) == 1
    a = resp.analyzers[0]
    assert a.name == "secret_scanner"
    assert a.vector == "symlink_traversal"
    assert a.triggered is True
    assert a.status == "ok"  # vulnerable path ran
    assert "8 secret(s) in 1 file(s)" in a.summary


def test_token_file_is_cleaned_after_job(seed_env: dict[str, Path]) -> None:
    dest = Path(seed_env["token_dest"])
    run_job(_secrets_meta())
    assert not dest.exists()  # token always cleaned up in finally


def test_module_sample_templates_each_payload_with_its_vector(tmp_path: Path) -> None:
    meta = RunMeta(
        scan_id="s3",
        scan_token="abcdef012345",
        module="sca",
        source_type="sample",
        listener_host="listener",
        listener_port=9000,
    )
    _fetch_repo(meta, tmp_path, [], None)

    assert 'VECTOR = "setup_py_exec"' in (tmp_path / "setup.py").read_text()
    assert 'VECTOR = "gemspec_eval"' in (tmp_path / "sample.gemspec").read_text()
    assert (
        'const VECTOR = "npm_lifecycle";' in (tmp_path / "postinstall.js").read_text()
    )


def test_sast_module_sample_templates_each_payload_with_its_vector(
    tmp_path: Path,
) -> None:
    meta = RunMeta(
        scan_id="s4",
        scan_token="abcdef012345",
        module="sast",
        source_type="sample",
        listener_host="listener",
        listener_port=9000,
    )
    _fetch_repo(meta, tmp_path, [], None)

    assert (
        'const VECTOR = "eslintrc_js_exec";' in (tmp_path / ".eslintrc.js").read_text()
    )
    assert (
        'VECTOR = "rubocop_require".freeze'
        in (tmp_path / "repository_rule.rb").read_text()
    )


def test_workdir_is_wiped_after_job(seed_env: dict[str, Path]) -> None:
    import tempfile

    before = set(Path(tempfile.gettempdir()).glob("dvap-scan-*"))
    run_job(_secrets_meta())
    after = set(Path(tempfile.gettempdir()).glob("dvap-scan-*"))
    # No new dvap-scan-* workdir should be left behind.
    assert after <= before


def test_healthz() -> None:
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_run_endpoint_secrets_sample(seed_env: dict[str, Path]) -> None:
    client = TestClient(main.app)
    meta = {
        "scan_id": "s2",
        "scan_token": "abcdef012345",
        "module": "secrets",
        "source_type": "sample",
        "listener_host": "example.com",
        "listener_port": 9000,
    }
    r = client.post("/run", data={"meta": json.dumps(meta)})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["analyzers"][0]["vector"] == "symlink_traversal"
    assert body["analyzers"][0]["triggered"] is True


def test_run_endpoint_rejects_bad_meta() -> None:
    client = TestClient(main.app)
    r = client.post("/run", data={"meta": "{not json"})
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
