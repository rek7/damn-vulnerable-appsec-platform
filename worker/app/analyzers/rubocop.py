"""RuboCop analyzer (vector ``rubocop_require``).

Trigger: a ``.rubocop.yml`` in the repo. Vulnerable path runs real rubocop, whose
``require:`` directive loads (executes) the named Ruby file at startup. Mitigated
path (``disable_extensibility``) strips the ``require:`` block before running.
"""

from __future__ import annotations

import shutil
import subprocess

from .. import sanitize
from ..models import AnalyzerResult, AnalyzerStatus
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
    mitigated = ctx.mitigations.disable_extensibility

    if mitigated:
        sanitized = sanitize.strip_rubocop_requires(
            config_path.read_text(encoding="utf-8")
        )
        config_path.write_text(sanitized, encoding="utf-8")
        add_step(
            ctx.steps,
            "info",
            "rubocop: disable_extensibility ON -- stripped require: lines from "
            ".rubocop.yml",
        )
    else:
        add_step(
            ctx.steps,
            "warn",
            "rubocop: require: directive will load Ruby at startup "
            "(vulnerable path)",
        )

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

    status: AnalyzerStatus = "blocked" if mitigated else "ok"
    summary = "ran with require: stripped" if mitigated else "ran loading require: Ruby"
    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status=status,
        summary=summary,
        duration_ms=timer.ms,
    )
