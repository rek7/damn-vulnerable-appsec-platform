"""DVAP API — FastAPI application entry point.

Mounts all route modules and the WebSocket hub endpoint.
Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .models import HealthResponse
from .routes.beacons import router as beacons_router
from .routes.config import router as config_router
from .routes.scans import router as scans_router
from .store import store
from .ws import hub

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("DVAP API starting up")
    await store.startup()
    try:
        yield
    finally:
        await store.shutdown()
        logger.info("DVAP API shutting down")


app = FastAPI(
    title="DVAP API",
    description=(
        "DVAP Security Platform backend API for scanner validation, controls, "
        "scan results, and event telemetry."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# -----------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------

app.include_router(config_router)
app.include_router(beacons_router)
app.include_router(scans_router)


# -----------------------------------------------------------------------
# WebSocket stream
# -----------------------------------------------------------------------


@app.websocket("/api/stream")
async def ws_stream(websocket: WebSocket) -> None:
    """Live feed: scan_update + beacon envelopes (§10)."""
    await hub.connect(websocket)
    try:
        # Keep connection alive; we only push, never expect client messages.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)


# -----------------------------------------------------------------------
# Healthz
# -----------------------------------------------------------------------


@app.get("/api/healthz", response_model=HealthResponse, tags=["health"])
async def healthz() -> HealthResponse:
    if not await store.healthcheck():
        raise HTTPException(status_code=503, detail="store unavailable")
    return HealthResponse()
