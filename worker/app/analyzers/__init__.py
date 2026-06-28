"""Analyzer registry and the shared analyzer context.

Every analyzer implements the same callable interface: given an
:class:`AnalyzerContext` it detects its trigger file, runs the real tool path,
and returns an :class:`~worker.app.models.AnalyzerResult`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..models import AnalyzerResult, Step


@dataclass
class AnalyzerContext:
    """Everything an analyzer needs to run against one scan's workdir."""

    workdir: Path
    scan_token: str
    listener_host: str
    listener_port: int
    # Subprocess env built by the job.
    env: dict[str, str]
    # Synthetic secrets visible this scan + k8s token, used by the worker-side
    # symlink beacon to build exfil.
    seeds: dict[str, str] = field(default_factory=dict)
    k8s_token: str = ""
    # Steps appended by analyzers for the step log.
    steps: list[Step] = field(default_factory=list)


# An analyzer is any callable that maps a context to a result.
Analyzer = Callable[[AnalyzerContext], AnalyzerResult]


def _registry() -> dict[str, list[Analyzer]]:
    """Build the module -> analyzers map.

    Imported lazily inside the function to avoid import cycles between the
    analyzers and this package module.
    """
    from . import (
        checkov,
        eslintrc,
        gemspec,
        npm_lifecycle,
        rubocop,
        secret_scanner,
        setup_py,
    )

    return {
        "iac": [checkov.run],
        "sca": [setup_py.run, gemspec.run, npm_lifecycle.run],
        "sast": [eslintrc.run, rubocop.run],
        "secrets": [secret_scanner.run],
    }


def analyzers_for_module(module: str) -> list[Analyzer]:
    """Return the analyzers registered for a module (empty if unknown)."""
    return _registry().get(module, [])
