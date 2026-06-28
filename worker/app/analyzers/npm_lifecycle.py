"""npm lifecycle analyzer (vector ``npm_lifecycle``).

Trigger: a ``package.json`` in the repo. Vulnerable path runs real ``npm
install`` which executes lifecycle scripts (postinstall). Mitigated path
(``disable_extensibility``) runs ``npm install --ignore-scripts`` (a real npm
flag) so the postinstall payload never runs.
"""

from __future__ import annotations

import shutil
import subprocess

from .. import sanitize
from ..models import AnalyzerResult, AnalyzerStatus
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

    mitigated = ctx.mitigations.disable_extensibility
    args = sanitize.npm_install_args(disable_extensibility=mitigated)
    if mitigated:
        add_step(
            ctx.steps,
            "info",
            "npm_lifecycle: disable_extensibility ON -- `npm install "
            "--ignore-scripts` (lifecycle scripts skipped)",
        )
    else:
        add_step(
            ctx.steps,
            "warn",
            "npm_lifecycle: `npm install` running lifecycle scripts "
            "(vulnerable path)",
        )

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
                [npm_bin, *args],
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

    status: AnalyzerStatus = "blocked" if mitigated else "ok"
    summary = (
        "npm install --ignore-scripts (lifecycle skipped)"
        if mitigated
        else "npm install ran lifecycle scripts"
    )
    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status=status,
        summary=summary,
        duration_ms=timer.ms,
    )
