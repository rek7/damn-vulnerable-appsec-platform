"""Pydantic v2 data models for DVAP API (§11, §6b of CONTRACTS.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field  # noqa: F401 (Field re-exported)

# ---------------------------------------------------------------------------
# Scan models (§11, §9 analyzer/step shapes)
# ---------------------------------------------------------------------------

ModuleName = Literal["iac", "sca", "sast", "secrets"]
StatusValue = Literal["queued", "running", "completed", "failed"]
SourceType = Literal["sample", "upload", "git"]
StepLevel = Literal["info", "warn", "error"]


class ScanSource(BaseModel):
    type: SourceType
    ref: str  # git_url | filename | "sample"


class AnalyzerResult(BaseModel):
    name: str
    vector: str
    triggered: bool
    status: Literal["ok", "error"]
    summary: str
    duration_ms: int


class Step(BaseModel):
    ts: str  # ISO8601
    level: StepLevel
    message: str


class Scan(BaseModel):
    id: str  # uuid4
    scan_token: str  # §5: secrets.token_hex(6), 12 hex chars
    module: ModuleName
    vector: str | None = None
    source: ScanSource
    status: StatusValue
    result: str = ""
    analyzers: list[AnalyzerResult] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    beacon_count: int = 0  # derived, updated on beacon ingest
    created_at: str  # ISO8601
    updated_at: str  # ISO8601


# ---------------------------------------------------------------------------
# Beacon models (§6b, §11)
# ---------------------------------------------------------------------------


class BeaconIngest(BaseModel):
    """Body posted by the listener service to /api/beacons (§6b)."""

    scan_token: str
    vector: str
    raw: str = ""
    decoded: str = ""
    method: str = "GET"
    path: str = ""
    remote: str = ""


class Beacon(BeaconIngest):
    """Stored beacon including server-stamped fields."""

    id: str  # uuid4
    scan_id: str | None = None  # resolved by scan_token match; null if unknown
    received_at: str  # ISO8601


class ScanDetail(Scan):
    """GET /api/scans/{id} response with derived correlated beacons."""

    beacons: list[Beacon] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateScanJSON(BaseModel):
    """JSON body for sample/git scan creation."""

    module: ModuleName
    vector: str | None = None
    source_type: Literal["sample", "git"]
    git_url: str | None = None


class CreateScanMeta(BaseModel):
    """The `meta` JSON field in multipart upload scan creation."""

    module: ModuleName
    vector: str | None = None
    source_type: Literal["upload"] = "upload"


class ScanUpdateEnvelope(BaseModel):
    type: Literal["scan_update"] = "scan_update"
    scan: Scan


class BeaconEnvelope(BaseModel):
    type: Literal["beacon"] = "beacon"
    beacon: Beacon


# ---------------------------------------------------------------------------
# Module / vector validation helpers
# ---------------------------------------------------------------------------

MODULE_VECTORS: dict[str, list[str]] = {
    "iac": ["checkov_external_checks"],
    "sca": ["setup_py_exec", "gemspec_eval", "npm_lifecycle"],
    "sast": ["eslintrc_js_exec", "rubocop_require"],
    "secrets": ["symlink_traversal"],
}


def valid_vector_for_module(module: str, vector: str) -> bool:
    """Return True if vector belongs to module."""
    return vector in MODULE_VECTORS.get(module, [])


# ---------------------------------------------------------------------------
# Healthz
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


# ---------------------------------------------------------------------------
# Worker response (§9) — used for deserialization only
# ---------------------------------------------------------------------------


class WorkerResponse(BaseModel):
    status: Literal["completed", "failed"]
    result: str
    analyzers: list[AnalyzerResult] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Worker run request meta (§9)
# ---------------------------------------------------------------------------


class WorkerRunMeta(BaseModel):
    scan_id: str
    scan_token: str
    module: str
    source_type: SourceType
    vector: str | None = None
    git_url: str | None = None
    listener_host: str = "listener"
    listener_port: int = 9000


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------


def utcnow_iso() -> str:
    """Return current UTC time as an ISO 8601 string with Z suffix."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
