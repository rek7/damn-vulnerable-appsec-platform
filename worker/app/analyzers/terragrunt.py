"""Terragrunt analyzer (vector ``terragrunt_before_hook``).

Trigger: a ``terragrunt.hcl`` in the repo. The analyzer runs real
``terragrunt plan``, which executes repository-defined hooks such as
``before_hook`` before the wrapped Terraform/OpenTofu command.
"""

from __future__ import annotations

import shutil
import subprocess

from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_file

VECTOR = "terragrunt_before_hook"
NAME = "terragrunt"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    config_path = find_file(ctx.workdir, "terragrunt.hcl")
    if config_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no terragrunt.hcl present",
            duration_ms=0,
        )

    repo_dir = config_path.parent
    add_step(
        ctx.steps,
        "warn",
        "terragrunt: running `terragrunt plan` with repository-defined hooks",
    )

    terragrunt_bin = shutil.which("terragrunt")
    if terragrunt_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="terragrunt binary not installed",
            duration_ms=0,
        )

    cmd = [terragrunt_bin, "plan", "--non-interactive"]
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
            return AnalyzerResult(
                name=NAME,
                vector=VECTOR,
                triggered=True,
                status="error",
                summary="terragrunt plan timed out",
                duration_ms=timer.ms,
            )

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="ran terragrunt plan with repository hooks",
        duration_ms=timer.ms,
    )
