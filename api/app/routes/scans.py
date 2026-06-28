"""Scan routes: POST /api/scans, GET /api/scans, GET /api/scans/{id}.

Scan lifecycle per CONTRACTS.md §10:
  queued -> running -> completed | failed
Each transition broadcasts scan_update over WS.
"""

from __future__ import annotations

import json
import os
import secrets
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..models import (
    AnalyzerResult,
    CreateScanJSON,
    CreateScanMeta,
    Scan,
    ScanDetail,
    ScanSource,
    ScanUpdateEnvelope,
    Step,
    utcnow_iso,
    valid_vector_for_module,
)
from ..ssrf import SSRFError, validate_git_url
from ..store import store
from ..worker_client import call_worker
from ..ws import hub

router = APIRouter(prefix="/api/scans", tags=["scans"])

# Upload limits (configurable via env)
_MAX_UPLOAD_BYTES = int(os.environ.get("DVAP_MAX_UPLOAD_MB", "20")) * 1024 * 1024
_ALLOWED_EXTENSIONS = (".zip", ".tar.gz", ".tgz")


def _check_upload_filename(filename: str) -> None:
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Upload must be .zip, .tar.gz, or .tgz; got {filename!r}",
        )


def _validation_error(detail: Any) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _validate_vector(module: str, vector: str | None) -> None:
    if vector and not valid_vector_for_module(module, vector):
        raise HTTPException(
            status_code=400,
            detail=f"Vector {vector!r} does not belong to module {module!r}",
        )


async def _run_scan(scan: Scan, archive_bytes: bytes | None = None) -> Scan:
    """Drive the scan lifecycle: queued -> running -> completed/failed."""
    now = utcnow_iso()
    scan = scan.model_copy(update={"status": "running", "updated_at": now})
    await store.update_scan(scan)
    await hub.broadcast(ScanUpdateEnvelope(scan=scan).model_dump())

    archive_filename = (
        scan.source.ref if scan.source.type == "upload" else "archive.zip"
    )

    try:
        worker_resp = await call_worker(
            scan_id=scan.id,
            scan_token=scan.scan_token,
            module=scan.module,
            source_type=scan.source.type,
            vector=scan.vector,
            git_url=scan.source.ref if scan.source.type == "git" else None,
            mitigations=scan.mitigations,
            archive_bytes=archive_bytes,
            archive_filename=archive_filename,
        )
        now = utcnow_iso()
        scan = scan.model_copy(
            update={
                "status": worker_resp.status,
                "result": worker_resp.result,
                "analyzers": worker_resp.analyzers,
                "steps": worker_resp.steps,
                "updated_at": now,
            }
        )
    except Exception as exc:
        now = utcnow_iso()
        error_step = Step(ts=now, level="error", message=f"Worker error: {exc}")
        scan = scan.model_copy(
            update={
                "status": "failed",
                "result": f"Worker error: {exc}",
                "steps": list(scan.steps) + [error_step],
                "updated_at": now,
            }
        )

    scan = await store.update_scan(scan)
    await hub.broadcast(ScanUpdateEnvelope(scan=scan).model_dump())
    return scan


async def _create_and_run(
    module: str,
    vector: str | None,
    source: ScanSource,
    archive_bytes: bytes | None = None,
) -> Scan:
    config = await store.get_config()
    scan = _make_scan(module, vector, source, config)
    scan = await store.create_scan(scan)
    await hub.broadcast(ScanUpdateEnvelope(scan=scan).model_dump())
    return await _run_scan(scan, archive_bytes=archive_bytes)


async def _create_scan_from_json_payload(payload: Any) -> Scan:
    try:
        body = CreateScanJSON.model_validate(payload)
    except Exception as exc:
        errors = exc.errors() if hasattr(exc, "errors") else str(exc)
        raise _validation_error(errors) from exc

    _validate_vector(body.module, body.vector)

    if body.source_type == "git":
        if not body.git_url:
            raise HTTPException(
                status_code=400, detail="git_url is required when source_type=git"
            )
        try:
            validate_git_url(body.git_url)
        except SSRFError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        source = ScanSource(type="git", ref=body.git_url)
    else:
        source = ScanSource(type="sample", ref="sample")

    return await _create_and_run(body.module, body.vector, source)


async def _create_scan_from_upload_parts(
    meta: str,
    archive: StarletteUploadFile,
) -> Scan:
    try:
        meta_obj = CreateScanMeta.model_validate(json.loads(meta))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid meta JSON: {exc}"
        ) from exc

    _validate_vector(meta_obj.module, meta_obj.vector)

    filename = archive.filename or "archive.bin"
    _check_upload_filename(filename)

    archive_bytes = await archive.read()
    max_mb = _MAX_UPLOAD_BYTES // (1024 * 1024)
    if len(archive_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds maximum size of {max_mb} MB",
        )

    source = ScanSource(type="upload", ref=filename)
    return await _create_and_run(
        meta_obj.module,
        meta_obj.vector,
        source,
        archive_bytes=archive_bytes,
    )


async def _create_scan_from_multipart_request(request: Request) -> Scan:
    form = await request.form()
    meta_value = form.get("meta")
    archive_value = form.get("archive")

    if not isinstance(meta_value, str):
        raise HTTPException(status_code=400, detail="meta form field is required")
    if not isinstance(archive_value, StarletteUploadFile):
        raise HTTPException(status_code=400, detail="archive file field is required")

    return await _create_scan_from_upload_parts(meta_value, archive_value)


def _make_scan(
    module: str,
    vector: str | None,
    source: ScanSource,
    mitigations_snapshot: object,
) -> Scan:
    """Create a new Scan in queued state with a fresh scan_token."""
    from ..models import Config

    if not isinstance(mitigations_snapshot, Config):
        raise TypeError("mitigations_snapshot must be a Config instance")

    now = utcnow_iso()
    return Scan(
        id=str(uuid.uuid4()),
        scan_token=secrets.token_hex(6),
        module=module,  # type: ignore[arg-type]
        vector=vector,
        source=source,
        status="queued",
        mitigations=mitigations_snapshot,
        created_at=now,
        updated_at=now,
    )


@router.post("", response_model=Scan)
async def create_scan(request: Request) -> Scan:
    """Create and run a scan from JSON or contract multipart body."""
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        return await _create_scan_from_multipart_request(request)

    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON body: {exc}",
        ) from exc

    return await _create_scan_from_json_payload(payload)


@router.post("/upload", response_model=Scan)
async def create_scan_upload(
    meta: Annotated[str, Form()],
    archive: Annotated[UploadFile, File()],
) -> Scan:
    """Compatibility endpoint for multipart uploads."""
    return await _create_scan_from_upload_parts(meta, archive)


@router.get("", response_model=list[Scan])
async def list_scans() -> list[Scan]:
    return await store.list_scans()


@router.get("/{scan_id}", response_model=ScanDetail)
async def get_scan(scan_id: str) -> ScanDetail:
    scan = await store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id!r} not found")
    beacons = await store.get_scan_beacons(scan.scan_token)
    return ScanDetail(**scan.model_dump(), beacons=beacons)


# Suppress unused import — AnalyzerResult and Step are used via worker_resp
__all__ = ["router", "AnalyzerResult", "Step", "store"]
