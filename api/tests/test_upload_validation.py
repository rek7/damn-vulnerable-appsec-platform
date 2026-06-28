"""Tests for upload validation (CONTRACTS.md §10 + §13)."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_zip(content: bytes = b"fake content") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.txt", content.decode(errors="replace"))
    return buf.getvalue()


META_VALID = json.dumps({"module": "iac", "source_type": "upload"})
META_VALID_SCA = json.dumps({"module": "sca", "source_type": "upload"})


def test_reject_non_zip_extension() -> None:
    """Non .zip/.tar.gz/.tgz extension should return 400."""
    resp = client.post(
        "/api/scans/upload",
        data={"meta": META_VALID},
        files={"archive": ("payload.exe", b"AAAA", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert ".zip" in resp.text or ".tar.gz" in resp.text or "zip" in resp.text.lower()


def test_reject_oversized_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Upload exceeding the size limit should return 413."""
    import app.routes.scans as scans_mod

    monkeypatch.setattr(scans_mod, "_MAX_UPLOAD_BYTES", 10)
    resp = client.post(
        "/api/scans/upload",
        data={"meta": META_VALID},
        files={"archive": ("archive.zip", b"X" * 100, "application/zip")},
    )
    assert resp.status_code == 413


def test_accept_zip_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid .zip file passes validation (worker is mocked)."""
    import app.routes.scans as scans_mod
    from app.models import AnalyzerResult, WorkerResponse

    async def mock_worker(**kwargs: object) -> WorkerResponse:
        return WorkerResponse(
            status="completed",
            result="ok",
            analyzers=[
                AnalyzerResult(
                    name="test",
                    vector="checkov_external_checks",
                    triggered=False,
                    status="ok",
                    summary="ok",
                    duration_ms=1,
                )
            ],
            steps=[],
        )

    monkeypatch.setattr(scans_mod, "call_worker", mock_worker)

    resp = client.post(
        "/api/scans/upload",
        data={"meta": META_VALID},
        files={"archive": ("archive.zip", _make_zip(), "application/zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"


def test_accept_upload_on_scans_contract_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTRACTS.md pins upload creation to POST /api/scans."""
    import app.routes.scans as scans_mod
    from app.models import WorkerResponse

    async def mock_worker(**kwargs: object) -> WorkerResponse:
        return WorkerResponse(status="completed", result="ok", analyzers=[], steps=[])

    monkeypatch.setattr(scans_mod, "call_worker", mock_worker)

    resp = client.post(
        "/api/scans",
        data={"meta": META_VALID},
        files={"archive": ("archive.zip", _make_zip(), "application/zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"]["type"] == "upload"
    assert data["status"] == "completed"


def test_accept_tar_gz_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid .tar.gz file passes validation."""
    import app.routes.scans as scans_mod
    from app.models import WorkerResponse

    async def mock_worker(**kwargs: object) -> WorkerResponse:
        return WorkerResponse(status="completed", result="ok", analyzers=[], steps=[])

    monkeypatch.setattr(scans_mod, "call_worker", mock_worker)

    resp = client.post(
        "/api/scans/upload",
        data={"meta": META_VALID_SCA},
        files={"archive": ("archive.tar.gz", b"fake tar content", "application/gzip")},
    )
    assert resp.status_code == 200


def test_reject_invalid_meta_json() -> None:
    """Malformed meta JSON should return 400."""
    resp = client.post(
        "/api/scans/upload",
        data={"meta": "not-json"},
        files={"archive": ("archive.zip", _make_zip(), "application/zip")},
    )
    assert resp.status_code == 400
