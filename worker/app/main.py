"""DVAP worker FastAPI app: POST /run + GET /healthz (§9), watermark boot (§7).

On import the app performs the startup watermark check and refuses to serve
(``sys.exit(1)``) if any synthetic seed is missing the ``FAKE`` watermark. This
is the load-bearing containment guarantee: a compromise can only ever exfiltrate
clearly-synthetic credentials.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import ValidationError

from . import seeds
from .models import HealthResponse, RunMeta, RunResponse, Step

logger = logging.getLogger("dvap.worker")


def _run_watermark_check() -> None:
    """Enforce the synthetic-seed watermark at startup; exit(1) on failure (§7)."""
    try:
        loaded, _token = seeds.startup_watermark_check()
    except (seeds.WatermarkError, FileNotFoundError) as exc:
        logger.error("startup watermark check FAILED: %s", exc)
        print(f"DVAP worker refusing to start: {exc}", file=sys.stderr)
        sys.exit(1)
    logger.info("watermark check passed for %d synthetic seeds", len(loaded))


# Allow tests to import the module without triggering a hard exit by gating the
# boot check behind an env flag (set in the container, unset in unit tests).
if os.environ.get("DVAP_SKIP_WATERMARK_CHECK") != "1":
    _run_watermark_check()


app = FastAPI(title="DVAP Worker", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse()


@app.post("/run", response_model=RunResponse)
async def run(
    meta: str = Form(...),
    archive: UploadFile | None = File(default=None),
) -> RunResponse:
    """Execute a scan job (§9). ``meta`` is a JSON string; ``archive`` optional."""
    # Import here so importing main.py for the watermark check stays light and
    # the analyzer/job graph is only loaded when actually serving.
    from . import job

    try:
        meta_obj = RunMeta(**json.loads(meta))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        return RunResponse(
            status="failed",
            result=f"invalid meta: {exc}",
            analyzers=[],
            steps=[_now_step("error", f"invalid meta: {exc}")],
        )

    archive_path: Path | None = None
    tmp_archive: Path | None = None
    try:
        if archive is not None and meta_obj.source_type == "upload":
            tmp_archive = _save_upload(archive)
            archive_path = tmp_archive
        return job.run_job(meta_obj, archive_path)
    finally:
        if tmp_archive is not None:
            tmp_archive.unlink(missing_ok=True)


def _save_upload(archive: UploadFile) -> Path:
    """Persist an uploaded archive to a temp file, preserving its extension."""
    suffix = "".join(Path(archive.filename or "upload").suffixes) or ".bin"
    fd, name = tempfile.mkstemp(suffix=suffix, prefix="dvap-upload-")
    path = Path(name)
    with os.fdopen(fd, "wb") as out:
        out.write(archive.file.read())
    return path


def _now_step(level: str, message: str) -> Step:
    from datetime import datetime

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return Step(ts=ts, level=level, message=message)  # type: ignore[arg-type]
