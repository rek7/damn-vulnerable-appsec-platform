"""setup.py analyzer (vector ``setup_py_exec``).

Trigger: a ``setup.py`` in the repo. The analyzer runs ``python setup.py --name``
to read metadata, executing project package code the same way legacy metadata
collection does.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "setup_py_exec"
NAME = "setup_py"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    setup_path = find_file(ctx.workdir, "setup.py")
    if setup_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no setup.py present",
            duration_ms=0,
        )

    add_step(
        ctx.steps,
        "warn",
        "setup_py: executing `python setup.py --name` to read metadata",
    )
    python_bin = shutil.which("python3") or shutil.which("python")
    if python_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="python interpreter not found",
            duration_ms=0,
        )

    with Timer() as timer:
        try:
            subprocess.run(
                [python_bin, "setup.py", "--name"],
                cwd=str(setup_path.parent),
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
                summary="setup.py execution timed out",
                duration_ms=timer.ms,
            )

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="executed setup.py to read metadata",
        duration_ms=timer.ms,
    )
