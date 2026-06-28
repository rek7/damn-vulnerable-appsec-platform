"""HTTP client for calling the worker run API (CONTRACTS.md §9).

Base URL read from env DVAP_WORKER_URL (default: http://worker:8100).
Forwards the run request as multipart/form-data with a JSON `meta` field
and an optional `archive` file for upload scans.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .models import Config, SourceType, WorkerResponse

_WORKER_BASE_URL = os.environ.get("DVAP_WORKER_URL", "http://worker:8100")
# Timeout: worker may need time to clone + run analyzers
_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


async def call_worker(
    *,
    scan_id: str,
    scan_token: str,
    module: str,
    source_type: SourceType,
    vector: str | None,
    git_url: str | None,
    mitigations: Config,
    archive_bytes: bytes | None = None,
    archive_filename: str = "archive.zip",
    listener_host: str = "listener",
    listener_port: int = 9000,
) -> WorkerResponse:
    """Call POST {worker}/run and return the parsed WorkerResponse.

    Raises httpx.HTTPError or WorkerCallError on transport / non-2xx errors.
    """
    meta: dict[str, Any] = {
        "scan_id": scan_id,
        "scan_token": scan_token,
        "module": module,
        "source_type": source_type,
        "vector": vector,
        "git_url": git_url,
        "mitigations": mitigations.model_dump(),
        "listener_host": listener_host,
        "listener_port": listener_port,
    }

    files: dict[str, Any] = {
        "meta": (None, json.dumps(meta), "application/json"),
    }
    if archive_bytes is not None:
        files["archive"] = (archive_filename, archive_bytes, "application/octet-stream")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{_WORKER_BASE_URL}/run",
            files=files,
        )
        response.raise_for_status()

    return WorkerResponse.model_validate(response.json())


class WorkerCallError(RuntimeError):
    """Raised when the worker returns a non-2xx status or times out."""
