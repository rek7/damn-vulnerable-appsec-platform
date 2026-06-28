"""Pydantic v2 models for the worker run API (CONTRACTS §9, §4).

These mirror the shapes the API agent serializes against; keep them in sync with
CONTRACTS.md. Only the worker-facing request/response shapes live here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ModuleName = Literal["iac", "sca", "sast", "secrets"]
SourceType = Literal["sample", "upload", "git"]
StepLevel = Literal["info", "warn", "error"]
AnalyzerStatus = Literal["ok", "blocked", "error"]


class Mitigations(BaseModel):
    """The four mitigation toggles (§4). Default = all off (VULNERABLE)."""

    strip_credentials: bool = False
    block_egress: bool = False
    resolve_symlinks: bool = False
    disable_extensibility: bool = False


class RunMeta(BaseModel):
    """The `meta` JSON field of POST /run (§9)."""

    scan_id: str
    scan_token: str
    module: ModuleName
    source_type: SourceType
    vector: str | None = None
    git_url: str | None = None
    mitigations: Mitigations = Field(default_factory=Mitigations)
    listener_host: str = "listener"
    listener_port: int = 9000


class AnalyzerResult(BaseModel):
    """One analyzer's outcome (§9)."""

    name: str
    vector: str
    triggered: bool
    status: AnalyzerStatus
    summary: str
    duration_ms: int


class Step(BaseModel):
    """A single step-log entry (§9)."""

    ts: str  # ISO8601
    level: StepLevel
    message: str


class RunResponse(BaseModel):
    """The 200 response body of POST /run (§9)."""

    status: Literal["completed", "failed"]
    result: str
    analyzers: list[AnalyzerResult] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
