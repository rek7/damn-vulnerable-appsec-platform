from __future__ import annotations

from pathlib import Path

from app.analyzers import AnalyzerContext
from app.analyzers import terragrunt
from tests.conftest import GOOD_SEEDS, GOOD_TOKEN


def _ctx(workdir: Path) -> AnalyzerContext:
    return AnalyzerContext(
        workdir=workdir,
        scan_token="abcdef012345",
        listener_host="listener",
        listener_port=9000,
        env={**GOOD_SEEDS},
        seeds=dict(GOOD_SEEDS),
        k8s_token=GOOD_TOKEN,
        steps=[],
    )


def test_terragrunt_analyzer_ignores_repos_without_config(tmp_path: Path) -> None:
    result = terragrunt.run(_ctx(tmp_path))

    assert result.name == "terragrunt"
    assert result.vector == "terragrunt_before_hook"
    assert result.triggered is False
    assert result.status == "ok"


def test_terragrunt_analyzer_runs_plan_for_config(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "terragrunt.hcl").write_text("terraform {}\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr(
        terragrunt.shutil,
        "which",
        lambda name: "/usr/local/bin/terragrunt",
    )

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

    monkeypatch.setattr(terragrunt.subprocess, "run", fake_run)

    result = terragrunt.run(_ctx(tmp_path))

    assert result.triggered is True
    assert result.status == "ok"
    assert result.summary == "ran terragrunt plan with repository hooks"
    assert calls[0][0] == ["/usr/local/bin/terragrunt", "plan", "--non-interactive"]
    assert calls[0][1]["cwd"] == str(tmp_path)
