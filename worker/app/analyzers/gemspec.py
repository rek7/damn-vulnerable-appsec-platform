"""gemspec analyzer (vector ``gemspec_eval``).

Trigger: a ``*.gemspec`` in the repo. Vulnerable path evaluates the gemspec via
Ruby (``Gem::Specification.load``), executing the file. Mitigated path
(``disable_extensibility``) parses name/version statically with a regex.
"""

from __future__ import annotations

import shutil
import subprocess

from .. import sanitize
from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step, find_by_suffix

VECTOR = "gemspec_eval"
NAME = "gemspec"


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    gemspec_path = find_by_suffix(ctx.workdir, ".gemspec")
    if gemspec_path is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=False,
            status="ok",
            summary="no .gemspec present",
            duration_ms=0,
        )

    if ctx.mitigations.disable_extensibility:
        with Timer() as timer:
            name, version = sanitize.parse_gemspec_metadata(
                gemspec_path.read_text(encoding="utf-8")
            )
        add_step(
            ctx.steps,
            "info",
            "gemspec: disable_extensibility ON -- parsed metadata statically, "
            "no eval",
        )
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="blocked",
            summary=f"static parse: name={name} version={version}",
            duration_ms=timer.ms,
        )

    add_step(
        ctx.steps,
        "warn",
        "gemspec: evaluating gemspec via Ruby Gem::Specification.load "
        "(vulnerable path)",
    )
    ruby_bin = shutil.which("ruby")
    if ruby_bin is None:
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="error",
            summary="ruby interpreter not found",
            duration_ms=0,
        )

    # Evaluate the gemspec the way real tooling does -- load + print metadata.
    script = (
        "spec = Gem::Specification.load(ARGV[0]); "
        "puts spec ? \"#{spec.name} #{spec.version}\" : 'nil'"
    )
    with Timer() as timer:
        try:
            subprocess.run(
                [ruby_bin, "-e", script, gemspec_path.name],
                cwd=str(gemspec_path.parent),
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
                summary="gemspec evaluation timed out",
                duration_ms=timer.ms,
            )

    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary="evaluated gemspec via Ruby",
        duration_ms=timer.ms,
    )
