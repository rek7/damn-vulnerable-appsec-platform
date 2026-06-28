"""Shared helpers for analyzers: timing, step logging, and trigger detection.

Kept free of the AnalyzerContext type to avoid an import cycle with the package
``__init__`` (which defines the context). Analyzers import these helpers and pass
plain values.
"""

from __future__ import annotations

import time
from datetime import UTC
from pathlib import Path

from ..models import Step, StepLevel


def now_iso() -> str:
    """Current UTC time as an ISO8601 string with Z suffix (matches api)."""
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def add_step(steps: list[Step], level: StepLevel, message: str) -> None:
    """Append a step-log entry."""
    steps.append(Step(ts=now_iso(), level=level, message=message))


class Timer:
    """Context manager that records elapsed milliseconds."""

    def __init__(self) -> None:
        self.ms: int = 0
        self._start: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.ms = int((time.perf_counter() - self._start) * 1000)


def find_file(workdir: Path, name: str) -> Path | None:
    """Return the first file named ``name`` anywhere under ``workdir``, else None."""
    for candidate in workdir.rglob(name):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None


def find_by_suffix(workdir: Path, suffix: str) -> Path | None:
    """Return the first regular file with ``suffix`` under ``workdir``, else None."""
    for candidate in workdir.rglob(f"*{suffix}"):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None
