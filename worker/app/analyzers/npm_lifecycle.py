"""npm lifecycle analyzer (vector ``npm_lifecycle``).

Trigger: a ``package.json`` in the repo. The analyzer runs real ``npm install``
which executes lifecycle scripts such as ``postinstall``.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "npm_lifecycle"
NAME = "npm_lifecycle"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    pkg_path = find_file(ctx.workdir, "package.json")
    if pkg_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no package.json present",
            duration_ms=0,
        )

    add_step(ctx.steps, "warn", "npm_lifecycle: `npm install` running lifecycle scripts")

    npm_bin = shutil.which("npm")
    if npm_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="npm not found",
            duration_ms=0,
        )

    with Timer() as timer:
        try:
            subprocess.run(
                [npm_bin, "install"],
                cwd=str(pkg_path.parent),
                env=ctx.env,
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                name=NAME,
                vector=VECTOR,
                triggered=True,
                status="error",
                summary="npm install timed out",
                duration_ms=timer.ms,
            )

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="npm install ran lifecycle scripts",
        duration_ms=timer.ms,
    )
