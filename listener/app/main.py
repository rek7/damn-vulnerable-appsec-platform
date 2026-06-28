"""DVAP listener service — out-of-band beacon receiver (CONTRACTS.md §6).

Listens on :9000.  Accepts GET and POST beacons at /b/{scan_token}/{vector},
decodes the dotted-hex exfil, and forwards to the api.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

from app.decode import decode_dotted_hex
from app.forward import forward_beacon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DVAP Listener", version="0.1.0")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Beacon endpoints — GET and POST
# ---------------------------------------------------------------------------


async def _handle_beacon(
    request: Request,
    scan_token: str,
    vector: str,
    raw: str,
) -> JSONResponse:
    """Shared logic: log, decode, forward, return 200."""
    method = request.method
    path = str(request.url.path)
    query = str(request.url.query)
    host = request.headers.get("host", "")
    remote = request.client.host if request.client else ""

    logger.info(
        "beacon method=%s host=%s path=%s query=%s remote=%s",
        method,
        host,
        path,
        query,
        remote,
    )

    decoded = decode_dotted_hex(raw)

    await forward_beacon(
        {
            "scan_token": scan_token,
            "vector": vector,
            "raw": raw,
            "decoded": decoded,
            "method": method,
            "path": path,
            "remote": remote,
        }
    )

    return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/b/{scan_token}/{vector}")
async def beacon_get(
    request: Request,
    scan_token: str,
    vector: str,
) -> JSONResponse:
    """Receive a GET beacon; exfil is in query param *d* (dotted hex)."""
    raw: str = request.query_params.get("d", "")
    return await _handle_beacon(request, scan_token, vector, raw)


@app.post("/b/{scan_token}/{vector}")
async def beacon_post(
    request: Request,
    scan_token: str,
    vector: str,
    d: Annotated[str, Form()] = "",
) -> JSONResponse:
    """Receive a POST beacon; exfil is in form param *d* (dotted hex).

    Falls back to query param *d* if the form body is absent/empty, so
    payloads that POST with a query string still work.
    """
    raw: str = d or request.query_params.get("d", "")
    return await _handle_beacon(request, scan_token, vector, raw)
