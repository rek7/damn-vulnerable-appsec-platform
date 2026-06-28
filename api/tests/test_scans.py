"""Tests for scan lifecycle with the worker client mocked (CONTRACTS.md §10, §9)."""

from __future__ import annotations

import re
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnalyzerResult, WorkerResponse

client = TestClient(app)


def _make_worker_resp(
    status: str = "completed",
    triggered: bool = True,
) -> WorkerResponse:
    return WorkerResponse(
        status=status,  # type: ignore[arg-type]
        result="scan finished",
        analyzers=[
            AnalyzerResult(
                name="checkov",
                vector="checkov_external_checks",
                triggered=triggered,
                status="ok",
                summary="external check loaded",
                duration_ms=42,
            )
        ],
        steps=[],
    )


def _mock_call_worker(resp: WorkerResponse):  # type: ignore[no-untyped-def]
    async def _inner(**kwargs: object) -> WorkerResponse:
        return resp

    return _inner


def test_create_scan_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.scans as scans_mod

    monkeypatch.setattr(
        scans_mod, "call_worker", _mock_call_worker(_make_worker_resp())
    )

    resp = client.post(
        "/api/scans",
        json={"module": "iac", "source_type": "sample"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["module"] == "iac"
    assert len(data["scan_token"]) == 12
    assert "id" in data


def test_create_scan_returns_scan_token(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.scans as scans_mod

    monkeypatch.setattr(
        scans_mod, "call_worker", _mock_call_worker(_make_worker_resp())
    )

    resp = client.post(
        "/api/scans",
        json={"module": "sca", "source_type": "sample", "vector": "setup_py_exec"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scan_token"]
    assert re.match(r"^[0-9a-f]{12}$", data["scan_token"])


def test_create_scan_snapshots_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mitigations snapshot on the scan should reflect config at scan time."""
    import app.routes.scans as scans_mod

    monkeypatch.setattr(
        scans_mod, "call_worker", _mock_call_worker(_make_worker_resp())
    )

    # Harden first
    client.post("/api/config/preset/hardened")
    resp = client.post("/api/scans", json={"module": "iac", "source_type": "sample"})
    assert resp.status_code == 200
    data = resp.json()
    mitigations = data["mitigations"]
    assert mitigations["disable_extensibility"] is True

    # Reset to vulnerable for other tests
    client.post("/api/config/preset/vulnerable")


def test_scan_failed_on_worker_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If worker raises, scan status should be failed."""
    import app.routes.scans as scans_mod

    async def error_worker(**kwargs: object) -> WorkerResponse:
        raise RuntimeError("worker unavailable")

    monkeypatch.setattr(scans_mod, "call_worker", error_worker)

    resp = client.post("/api/scans", json={"module": "iac", "source_type": "sample"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    # Error step should be appended
    assert any("Worker error" in step["message"] for step in data["steps"])


def test_list_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.scans as scans_mod

    monkeypatch.setattr(
        scans_mod, "call_worker", _mock_call_worker(_make_worker_resp())
    )

    client.post("/api/scans", json={"module": "iac", "source_type": "sample"})
    resp = client.get("/api/scans")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_scan_not_found() -> None:
    resp = client.get("/api/scans/nonexistent-id")
    assert resp.status_code == 404


def test_get_scan_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.routes.scans as scans_mod

    monkeypatch.setattr(
        scans_mod, "call_worker", _mock_call_worker(_make_worker_resp())
    )

    create_resp = client.post(
        "/api/scans", json={"module": "iac", "source_type": "sample"}
    )
    scan_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/scans/{scan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == scan_id


def test_reject_invalid_module() -> None:
    resp = client.post(
        "/api/scans",
        json={"module": "invalid_module", "source_type": "sample"},
    )
    assert resp.status_code == 422


def test_reject_vector_not_in_module() -> None:
    """Vector that doesn't belong to the module should return 400."""
    resp = client.post(
        "/api/scans",
        json={
            "module": "iac",
            "source_type": "sample",
            "vector": "symlink_traversal",  # belongs to secrets, not iac
        },
    )
    assert resp.status_code == 400


def test_reject_git_url_bad_scheme() -> None:
    resp = client.post(
        "/api/scans",
        json={
            "module": "iac",
            "source_type": "git",
            "git_url": "http://github.com/foo/bar",
        },
    )
    assert resp.status_code == 400


def test_reject_git_url_missing() -> None:
    resp = client.post(
        "/api/scans",
        json={"module": "iac", "source_type": "git"},
    )
    assert resp.status_code == 400


def test_healthz() -> None:
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_healthz_reports_store_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main_mod

    async def unhealthy() -> bool:
        return False

    main_store = cast(Any, main_mod).store
    monkeypatch.setattr(main_store, "healthcheck", unhealthy)

    resp = client.get("/api/healthz")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "store unavailable"
