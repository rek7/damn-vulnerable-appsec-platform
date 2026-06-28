"""Checkov analyzer (vector ``checkov_external_checks``).

Trigger: a ``.checkov.yml`` in the repo. The analyzer runs real checkov with
``--external-checks-dir`` pointed at the repo's checks dir, so checkov imports
the project-supplied policy module.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "checkov_external_checks"
NAME = "checkov"
CHECKS_DIRNAME = "checkov_checks"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    config_path = find_file(ctx.workdir, ".checkov.yml")
    if config_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no .checkov.yml present",
            duration_ms=0,
        )

    repo_dir = config_path.parent
    checks_dir = repo_dir / CHECKS_DIRNAME
    add_step(
        ctx.steps,
        "warn",
        "checkov: loading external Python checks via --external-checks-dir",
    )
    external_args = (
        ["--external-checks-dir", str(checks_dir)] if checks_dir.is_dir() else []
    )

    checkov_bin = shutil.which("checkov")
    if checkov_bin is None:
        # Tool absent (local dev): report error rather than crash. Real exec is
        # covered by docker e2e.
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="checkov binary not installed",
            duration_ms=0,
        )

    cmd = [checkov_bin, "--directory", str(repo_dir), "--compact", *external_args]
    with Timer() as timer:
        try:
            subprocess.run(
                cmd,
                cwd=str(repo_dir),
                env=ctx.env,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return _result("error", "checkov timed out", timer.ms, triggered=True)

    return _result("ok", "ran loading external Python checks", timer.ms, triggered=True)


def _result(status: str, summary: str, ms: int, *, triggered: bool) -> AnalyzerResult:
    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=triggered,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        duration_ms=ms,
    )
