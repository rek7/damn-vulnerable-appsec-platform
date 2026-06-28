"""Beacon routes: POST /api/beacons, GET /api/beacons."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from ..models import Beacon, BeaconEnvelope, BeaconIngest, utcnow_iso
from ..store import store
from ..ws import hub

router = APIRouter(prefix="/api/beacons", tags=["beacons"])


@router.post("", response_model=Beacon)
async def ingest_beacon(body: BeaconIngest) -> Beacon:
    """Internal endpoint: listener posts parsed beacons here (§6b)."""
    scan_id = await store.resolve_scan_id(body.scan_token)
    beacon = Beacon(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        scan_token=body.scan_token,
        vector=body.vector,
        raw=body.raw,
        decoded=body.decoded,
        method=body.method,
        path=body.path,
        remote=body.remote,
        received_at=utcnow_iso(),
    )
    stored = await store.add_beacon(beacon)
    # Broadcast to WS clients
    await hub.broadcast(BeaconEnvelope(beacon=stored).model_dump())
    return stored


@router.get("", response_model=list[Beacon])
async def list_beacons(
    scan_token: str | None = None,
    vector: str | None = None,
) -> list[Beacon]:
    return await store.list_beacons(scan_token=scan_token, vector=vector)


__all__ = ["router", "store"]
