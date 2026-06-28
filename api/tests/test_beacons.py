"""Tests for beacon ingest, scan_token correlation, and scan_id resolution."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.models import Config, Scan, ScanSource, utcnow_iso
from app.store import Store

client = TestClient(app)


async def _seed_scan(s: Store, scan_token: str, scan_id: str) -> Scan:
    now = utcnow_iso()
    scan = Scan(
        id=scan_id,
        scan_token=scan_token,
        module="iac",
        source=ScanSource(type="sample", ref="sample"),
        status="completed",
        mitigations=Config(),
        created_at=now,
        updated_at=now,
    )
    return await s.create_scan(scan)


def test_ingest_beacon_known_scan_token() -> None:
    """Beacon with a known scan_token resolves scan_id."""
    import app.routes.beacons as beacons_mod

    s = Store()
    token = "ab12cd34ef56"
    scan_id = "test-scan-id-001"
    asyncio.get_event_loop().run_until_complete(_seed_scan(s, token, scan_id))

    original = beacons_mod.store
    beacons_mod.store = s

    try:
        resp = client.post(
            "/api/beacons",
            json={
                "scan_token": token,
                "vector": "checkov_external_checks",
                "raw": "aabb",
                "decoded": "test decoded",
                "method": "GET",
                "path": f"/b/{token}/checkov_external_checks",
                "remote": "10.0.0.1",
            },
        )
    finally:
        beacons_mod.store = original

    assert resp.status_code == 200
    data = resp.json()
    assert data["scan_id"] == scan_id
    assert data["scan_token"] == token
    assert data["vector"] == "checkov_external_checks"
    assert "id" in data
    assert "received_at" in data


def test_ingest_beacon_unknown_scan_token() -> None:
    """Beacon with unknown scan_token stores with scan_id=null."""
    resp = client.post(
        "/api/beacons",
        json={
            "scan_token": "000000000000",
            "vector": "symlink_traversal",
            "raw": "",
            "decoded": "",
            "method": "GET",
            "path": "/b/000000000000/symlink_traversal",
            "remote": "",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scan_id"] is None


def test_list_beacons_filter_by_scan_token() -> None:
    """GET /api/beacons?scan_token= filters correctly."""
    token_a = "aaaaaaaaaaaa"
    token_b = "bbbbbbbbbbbb"

    pairs = [
        (token_a, "checkov_external_checks"),
        (token_b, "symlink_traversal"),
    ]
    for token, vector in pairs:
        client.post(
            "/api/beacons",
            json={
                "scan_token": token,
                "vector": vector,
                "raw": "",
                "decoded": "",
                "method": "GET",
                "path": "",
                "remote": "",
            },
        )

    resp = client.get(f"/api/beacons?scan_token={token_a}")
    assert resp.status_code == 200
    beacons = resp.json()
    assert all(b["scan_token"] == token_a for b in beacons)


def test_list_beacons_filter_by_vector() -> None:
    """GET /api/beacons?vector= filters correctly."""
    target_vector = "setup_py_exec_unique_test"
    client.post(
        "/api/beacons",
        json={
            "scan_token": "cccccccccccc",
            "vector": target_vector,
            "raw": "",
            "decoded": "",
            "method": "GET",
            "path": "",
            "remote": "",
        },
    )
    resp = client.get(f"/api/beacons?vector={target_vector}")
    assert resp.status_code == 200
    beacons = resp.json()
    assert any(b["vector"] == target_vector for b in beacons)


def test_beacon_count_increments_on_scan() -> None:
    """Scan.beacon_count increases when beacons arrive with matching scan_token."""
    import app.routes.beacons as beacons_mod
    import app.routes.scans as scans_mod

    s = Store()
    token = "deadbeef0000"
    scan_id = "test-scan-id-001"
    asyncio.get_event_loop().run_until_complete(_seed_scan(s, token, scan_id))

    original_beacons_store = beacons_mod.store
    original_scans_store = scans_mod.store
    beacons_mod.store = s
    scans_mod.store = s

    try:
        client.post(
            "/api/beacons",
            json={
                "scan_token": token,
                "vector": "checkov_external_checks",
                "raw": "",
                "decoded": "",
                "method": "GET",
                "path": "",
                "remote": "",
            },
        )
        detail = client.get(f"/api/scans/{scan_id}")
    finally:
        beacons_mod.store = original_beacons_store
        scans_mod.store = original_scans_store

    scan = asyncio.get_event_loop().run_until_complete(s.get_scan(scan_id))
    assert scan is not None
    assert scan.beacon_count == 1
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["beacon_count"] == 1
    assert len(detail_body["beacons"]) == 1
    assert detail_body["beacons"][0]["scan_token"] == token
