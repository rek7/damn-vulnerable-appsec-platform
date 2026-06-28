"""ESLint analyzer (vector ``eslintrc_js_exec``).

Trigger: a ``.eslintrc.js`` in the repo. Vulnerable path runs real eslint, which
``require()``s ``.eslintrc.js`` (executing it). Mitigated path
(``disable_extensibility``) deletes the config and runs eslint with
``--no-eslintrc`` so the JS config is never loaded.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess

from .. import sanitize
from ..models import AnalyzerResult, AnalyzerStatus
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "eslintrc_js_exec"
NAME = "eslintrc"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    rc_path = find_file(ctx.workdir, ".eslintrc.js")
    if rc_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no .eslintrc.js present",
            duration_ms=0,
        )

    repo_dir = rc_path.parent
    mitigated = ctx.mitigations.disable_extensibility

    if mitigated:
        # Belt and suspenders: delete the config AND pass --no-eslintrc.
        with contextlib.suppress(OSError):
            rc_path.unlink()
        add_step(
            ctx.steps,
            "info",
            "eslintrc: disable_extensibility ON -- removed .eslintrc.js and "
            "running with --no-eslintrc",
        )
    else:
        add_step(
            ctx.steps,
            "warn",
            "eslintrc: eslint will require() .eslintrc.js (vulnerable path)",
        )

    eslint_bin = shutil.which("eslint")
    if eslint_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="eslint not found",
            duration_ms=0,
        )

    args = sanitize.eslint_args(".", disable_extensibility=mitigated)
    with Timer() as timer:
        try:
            subprocess.run(
                [eslint_bin, *args],
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
                summary="eslint timed out",
                duration_ms=timer.ms,
            )

    status: AnalyzerStatus = "blocked" if mitigated else "ok"
    summary = (
        "ran with --no-eslintrc (config ignored)"
        if mitigated
        else "ran loading .eslintrc.js"
    )
    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status=status,
        summary=summary,
        duration_ms=timer.ms,
    )
