"""RuboCop analyzer (vector ``rubocop_require``).

Trigger: a ``.rubocop.yml`` in the repo. The analyzer runs real rubocop, whose
``require:`` directive loads the named Ruby file at startup.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "rubocop_require"
NAME = "rubocop"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    config_path = find_file(ctx.workdir, ".rubocop.yml")
    if config_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no .rubocop.yml present",
            duration_ms=0,
        )

    repo_dir = config_path.parent
    add_step(ctx.steps, "warn", "rubocop: require: directive will load Ruby at startup")

    rubocop_bin = shutil.which("rubocop")
    if rubocop_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="rubocop not found",
            duration_ms=0,
        )

    with Timer() as timer:
        try:
            subprocess.run(
                [rubocop_bin],
                cwd=str(repo_dir),
                env=ctx.env,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                name=NAME,
                vector=VECTOR,
                triggered=True,
                status="error",
                summary="rubocop timed out",
                duration_ms=timer.ms,
            )

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="ran loading require: Ruby",
        duration_ms=timer.ms,
    )
