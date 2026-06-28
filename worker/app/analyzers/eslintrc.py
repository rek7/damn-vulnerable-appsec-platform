"""ESLint analyzer (vector ``eslintrc_js_exec``).

Trigger: a ``.eslintrc.js`` in the repo. The analyzer runs real eslint, which
``require()``s the JavaScript config file.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
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
    add_step(ctx.steps, "warn", "eslintrc: eslint will require() .eslintrc.js")

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

    with Timer() as timer:
        try:
            subprocess.run(
                [eslint_bin, "."],
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

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="ran loading .eslintrc.js",
        duration_ms=timer.ms,
    )
