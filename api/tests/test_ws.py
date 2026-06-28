"""Tests for WebSocket broadcast (CONTRACTS.md §10)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnalyzerResult, WorkerResponse

client = TestClient(app)


def _make_worker_resp() -> WorkerResponse:
    return WorkerResponse(
        status="completed",
        result="ok",
        analyzers=[
            AnalyzerResult(
                name="checkov",
                vector="checkov_external_checks",
                triggered=True,
                status="ok",
                summary="test",
                duration_ms=1,
            )
        ],
        steps=[],
    )


def test_ws_receives_scan_update(monkeypatch: pytest.MonkeyPatch) -> None:
    """WS clients receive scan_update envelopes when a scan is created."""
    import app.routes.scans as scans_mod

    async def mock_worker(**kwargs: object) -> WorkerResponse:
        return _make_worker_resp()

    monkeypatch.setattr(scans_mod, "call_worker", mock_worker)

    with client.websocket_connect("/api/stream") as ws:
        # Trigger a scan in a separate thread; TestClient handles the event loop
        # POST while the WS is open
        resp = client.post(
            "/api/scans", json={"module": "iac", "source_type": "sample"}
        )
        assert resp.status_code == 200

        # Collect messages — we expect at least queued + running + completed
        messages = []
        for _ in range(3):
            try:
                raw = ws.receive_text()
                messages.append(json.loads(raw))
            except Exception:
                break

    types = [m.get("type") for m in messages]
    assert "scan_update" in types


def test_ws_scan_update_envelope_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """scan_update envelopes must contain a 'scan' key."""
    import app.routes.scans as scans_mod

    async def mock_worker(**kwargs: object) -> WorkerResponse:
        return _make_worker_resp()

    monkeypatch.setattr(scans_mod, "call_worker", mock_worker)

    with client.websocket_connect("/api/stream") as ws:
        client.post("/api/scans", json={"module": "sca", "source_type": "sample"})
        raw = ws.receive_text()
        msg = json.loads(raw)

    assert msg["type"] == "scan_update"
    assert "scan" in msg
    scan = msg["scan"]
    assert "id" in scan
    assert "scan_token" in scan


def test_ws_beacon_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    """beacon envelopes are broadcast when POST /api/beacons is called."""
    with client.websocket_connect("/api/stream") as ws:
        client.post(
            "/api/beacons",
            json={
                "scan_token": "ff00ff00ff00",
                "vector": "checkov_external_checks",
                "raw": "",
                "decoded": "",
                "method": "GET",
                "path": "",
                "remote": "",
            },
        )
        raw = ws.receive_text()
        msg = json.loads(raw)

    assert msg["type"] == "beacon"
    assert "beacon" in msg
    assert msg["beacon"]["scan_token"] == "ff00ff00ff00"
