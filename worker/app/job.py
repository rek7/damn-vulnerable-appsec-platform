"""Per-scan job orchestration: fetch -> env -> analyze -> wipe (§9).

The ephemeral workdir is ALWAYS wiped in a ``finally``, even on error -- that is
the "ephemeral worker" containment control (§2.7).
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import UTC
from pathlib import Path

from . import analyzers, fetch, seeds, templating
from .analyzers import AnalyzerContext
from .models import AnalyzerResult, RunMeta, RunResponse, Step


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _step(steps: list[Step], level: str, message: str) -> None:
    steps.append(Step(ts=_now_iso(), level=level, message=message))  # type: ignore[arg-type]


def _fetch_repo(
    meta: RunMeta,
    workdir: Path,
    steps: list[Step],
    archive_path: Path | None,
) -> None:
    """Fetch the repo into ``workdir`` according to source_type (§9)."""
    if meta.source_type == "sample":
        for vector_id, src in fetch.sample_repo_entries(meta.module, meta.vector):
            fetch.copy_sample_repo(src, workdir)
            subs = templating.build_substitutions(
                scan_token=meta.scan_token,
                vector=vector_id,
                listener_host=meta.listener_host,
                listener_port=meta.listener_port,
            )
            templating.apply_to_tree(workdir, subs)
        _step(steps, "info", f"fetched sample repo for module={meta.module}")
    elif meta.source_type == "upload":
        if archive_path is None:
            raise fetch.FetchError("source_type=upload requires an archive")
        fetch.extract_archive(archive_path, workdir)
        _step(steps, "info", f"extracted upload archive {archive_path.name}")
    elif meta.source_type == "git":
        if not meta.git_url:
            raise fetch.FetchError("source_type=git requires git_url")
        fetch.clone_git(meta.git_url, workdir)
        _step(steps, "info", f"cloned {meta.git_url}")
    else:  # pragma: no cover - exhaustive by Literal
        raise fetch.FetchError(f"unknown source_type {meta.source_type!r}")


def run_job(meta: RunMeta, archive_path: Path | None = None) -> RunResponse:
    """Execute a full scan job and return the §9 response."""
    steps: list[Step] = []
    workdir = Path(tempfile.mkdtemp(prefix="dvap-scan-"))
    k8s_dest = None
    try:
        _step(steps, "info", f"workdir created at {workdir}")

        # --- fetch ------------------------------------------------------
        _fetch_repo(meta, workdir, steps, archive_path)

        # --- env / seeds (§7) -------------------------------------------
        loaded_seeds = seeds.load_seeds()
        k8s_token = seeds.load_k8s_token()

        env = seeds.build_subprocess_env(loaded_seeds)
        k8s_dest = seeds.write_k8s_token(k8s_token)
        _step(
            steps,
            "info",
            "synthetic seeds injected into analyzer env"
            + (f"; k8s token written to {k8s_dest}" if k8s_dest else ""),
        )

        # --- run analyzers ----------------------------------------------
        ctx = AnalyzerContext(
            workdir=workdir,
            scan_token=meta.scan_token,
            listener_host=meta.listener_host,
            listener_port=meta.listener_port,
            env=env,
            seeds=dict(loaded_seeds),
            k8s_token=k8s_token,
            steps=steps,
        )
        results: list[AnalyzerResult] = []
        for analyzer in analyzers.analyzers_for_module(meta.module):
            result = analyzer(ctx)
            results.append(result)

        triggered = [r for r in results if r.triggered]
        summary = _summarize(triggered)
        return RunResponse(
            status="completed",
            result=summary,
            analyzers=results,
            steps=steps,
        )
    except Exception as exc:  # noqa: BLE001 - report any failure as §9 "failed"
        _step(steps, "error", f"job failed: {exc}")
        return RunResponse(
            status="failed",
            result=f"job failed: {exc}",
            analyzers=[],
            steps=steps,
        )
    finally:
        # Ephemeral worker: always wipe the workdir + any k8s token written.
        shutil.rmtree(workdir, ignore_errors=True)
        if k8s_dest is not None:
            seeds.remove_k8s_token(k8s_dest)


def _summarize(triggered: list[AnalyzerResult]) -> str:
    """Build the short human result string from triggered analyzers."""
    if not triggered:
        return "no analyzers triggered"
    parts = [f"{r.name}={r.status}" for r in triggered]
    return "; ".join(parts)
