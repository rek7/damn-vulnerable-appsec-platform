"""DVAP end-to-end test harness (SPEC §12, CONTRACTS §3).

API-level tests — no browser required.  Run inside docker-compose.test.yml
where all service hostnames resolve on dvap-net.

Test matrix (parametrized per vector):
  - observation preset + validation scenario -> beacon {scan_token}/{vector} arrives
    within BEACON_TIMEOUT_S and appears in scan detail.
  - Matching control ON -> no beacon within BEACON_TIMEOUT_S.

Additional containment assertions:
  - No evil-repos/ file references an external hostname (non-listener).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("DVAP_API_URL", "http://localhost:8000")
DB_URL = os.environ.get(
    "DVAP_DATABASE_URL",
    "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
)
BEACON_TIMEOUT_S = 20  # seconds to wait for a beacon to arrive
POLL_INTERVAL_S = 1

EXPECTED_EXFIL_KEYS = (
    "AWS_ACCESS_KEY_ID=",
    "AWS_SECRET_ACCESS_KEY=",
    "AWS_CANARY_ACCESS_KEY_ID=",
    "AWS_CANARY_SECRET_ACCESS_KEY=",
    "AWS_SESSION_TOKEN=",
    "GITHUB_TOKEN=",
    "GITHUB_CANARY_TOKEN=",
    "NPM_TOKEN=",
    "DATABASE_URL=",
    "POSTGRES_CANARY_DSN=",
    "DVAP_DATABASE_URL=",
    "LATERAL_MOVEMENT_DB_URL=",
    "STRIPE_API_KEY=",
    "SLACK_WEBHOOK_URL=",
    "K8S_SA_TOKEN=",
)

# Map each (module, vector) → the primary blocking mitigation (CONTRACTS §3)
VECTOR_MITIGATION: list[tuple[str, str, str]] = [
    ("iac", "checkov_external_checks", "disable_extensibility"),
    ("sca", "setup_py_exec", "disable_extensibility"),
    ("sca", "gemspec_eval", "disable_extensibility"),
    ("sca", "npm_lifecycle", "disable_extensibility"),
    ("sast", "eslintrc_js_exec", "disable_extensibility"),
    ("sast", "rubocop_require", "disable_extensibility"),
    ("secrets", "symlink_traversal", "resolve_symlinks"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api(path: str, **kwargs: Any) -> httpx.Response:
    """GET helper with a 30 s timeout."""
    return httpx.get(f"{API_BASE}{path}", timeout=30, **kwargs)


def api_post(path: str, **kwargs: Any) -> httpx.Response:
    return httpx.post(f"{API_BASE}{path}", timeout=60, **kwargs)


def api_put(path: str, **kwargs: Any) -> httpx.Response:
    return httpx.put(f"{API_BASE}{path}", timeout=30, **kwargs)


def set_preset(preset: str) -> None:
    """Apply observation or protected preset."""
    r = api_post(f"/api/config/preset/{preset}")
    assert r.status_code == 200, f"preset {preset} failed: {r.text}"


def set_mitigation(mitigation: str, value: bool) -> None:
    """Flip one mitigation toggle."""
    r = api_put("/api/config", json={mitigation: value})
    assert r.status_code == 200, f"set_mitigation failed: {r.text}"


def submit_sample(module: str, vector: str) -> str:
    """Submit a sample scan and return the scan_token."""
    r = api_post(
        "/api/scans",
        json={"module": module, "vector": vector, "source_type": "sample"},
    )
    assert r.status_code == 200, f"scan submission failed: {r.text}"
    data = r.json()
    assert "scan_token" in data, f"no scan_token in response: {data}"
    return str(data["scan_token"])


def wait_for_beacon(
    scan_token: str, vector: str, timeout: float
) -> dict[str, Any] | None:
    """Poll GET /api/beacons until {scan_token}/{vector} appears or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = api(f"/api/beacons?scan_token={scan_token}")
        if r.status_code == 200:
            beacons: list[dict[str, Any]] = r.json()
            for b in beacons:
                if b.get("scan_token") == scan_token and b.get("vector") == vector:
                    return b
        time.sleep(POLL_INTERVAL_S)
    return None


def assert_expected_exfil(beacon: dict[str, Any]) -> None:
    decoded = str(beacon.get("decoded") or "")
    for key in EXPECTED_EXFIL_KEYS:
        assert key in decoded, f"expected {key!r} in decoded beacon: {decoded!r}"


# ---------------------------------------------------------------------------
# Smoke test — healthz
# ---------------------------------------------------------------------------


def test_api_healthz() -> None:
    r = api("/api/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------------------------------------------------------------------------
# Fresh-boot is VULNERABLE: default config is all-off
# ---------------------------------------------------------------------------


def test_default_config_is_vulnerable() -> None:
    r = api("/api/config")
    assert r.status_code == 200
    cfg = r.json()
    for key in (
        "strip_credentials",
        "block_egress",
        "resolve_symlinks",
        "disable_extensibility",
    ):
        assert key in cfg, f"missing config key: {key}"
        assert cfg[key] is False, f"{key} should be False on fresh boot"


def test_postgres_seeded_integration_credentials() -> None:
    import psycopg

    expected = {
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "github_token",
        "npm_token",
        "postgres_url",
    }
    with psycopg.connect(DB_URL) as conn:
        rows = conn.execute(
            """
            SELECT credential_type
            FROM integration_credentials
            ORDER BY credential_type
            """
        ).fetchall()

    assert {str(row[0]) for row in rows} == expected


# ---------------------------------------------------------------------------
# Per-vector parametrized test: fires in observation mode, blocked when mitigated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module,vector,mitigation", VECTOR_MITIGATION)
def test_vector_fires_when_vulnerable(
    module: str, vector: str, mitigation: str
) -> None:
    """Beacon arrives within BEACON_TIMEOUT_S when controls are disabled."""
    set_preset("vulnerable")
    scan_token = submit_sample(module, vector)
    beacon = wait_for_beacon(scan_token, vector, BEACON_TIMEOUT_S)
    assert beacon is not None, (
        f"[FAIL] beacon {scan_token}/{vector} did NOT arrive within "
        f"{BEACON_TIMEOUT_S}s (expected: fires in observation mode)"
    )
    assert_expected_exfil(beacon)


@pytest.mark.parametrize("module,vector,mitigation", VECTOR_MITIGATION)
def test_vector_blocked_when_mitigated(
    module: str, vector: str, mitigation: str
) -> None:
    """No beacon when the matching mitigation is ON."""
    set_preset("vulnerable")  # start clean
    set_mitigation(mitigation, True)  # flip the one mitigation
    scan_token = submit_sample(module, vector)
    beacon = wait_for_beacon(scan_token, vector, BEACON_TIMEOUT_S)
    # Reset before asserting so we don't leave state dirty if assertion fails
    set_preset("vulnerable")
    assert beacon is None, (
        f"[FAIL] beacon {scan_token}/{vector} arrived even though "
        f"mitigation '{mitigation}' was ON (expected: blocked)"
    )


# ---------------------------------------------------------------------------
# Hardened preset blocks everything
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module,vector,mitigation", VECTOR_MITIGATION)
def test_hardened_preset_blocks_all(module: str, vector: str, mitigation: str) -> None:
    set_preset("hardened")
    scan_token = submit_sample(module, vector)
    beacon = wait_for_beacon(scan_token, vector, BEACON_TIMEOUT_S)
    set_preset("vulnerable")  # restore
    assert (
        beacon is None
    ), f"[FAIL] beacon arrived for {vector} even with protected mode"


# ---------------------------------------------------------------------------
# Containment: no evil-repos/ file references an external hostname
# ---------------------------------------------------------------------------

# Detect external URLs: http(s):// NOT followed by the listener placeholder
_EXTERNAL_URL_RE = re.compile(
    r"https?://(?!__DVAP_LISTENER_HOST__)[a-zA-Z0-9]",
    re.IGNORECASE,
)

# Resolve evil-repos relative to the e2e dir at /e2e; in the container the
# repo root is mounted at / so we look one level up.
_EVIL_REPOS_CANDIDATES = [
    Path("/app/evil-repos"),  # if repo is mounted at /app
    Path("/evil-repos"),  # if repo root is at /
    Path(__file__).parent.parent / "evil-repos",  # local run
]


def _find_evil_repos() -> Path | None:
    for p in _EVIL_REPOS_CANDIDATES:
        if p.is_dir():
            return p
    return None


def test_no_external_urls_in_evil_repos() -> None:
    """No evil-repo file may contain a literal external HTTP(S) URL."""
    evil_repos = _find_evil_repos()
    if evil_repos is None:
        pytest.skip("evil-repos/ directory not found in container")

    violations: list[str] = []
    for fpath in sorted(evil_repos.rglob("*")):
        if fpath.is_symlink():
            continue
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _EXTERNAL_URL_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")

    assert not violations, (
        "evil-repos/ contains external URL references — CONTAINMENT VIOLATION:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Scan detail includes correlated beacons
# ---------------------------------------------------------------------------


def test_scan_detail_includes_beacon() -> None:
    """GET /api/scans/{id} returns beacon_count > 0 after a fired vector."""
    set_preset("vulnerable")
    r = api_post(
        "/api/scans",
        json={
            "module": "iac",
            "vector": "checkov_external_checks",
            "source_type": "sample",
        },
    )
    assert r.status_code == 200
    scan = r.json()
    scan_id = scan["id"]
    scan_token = scan["scan_token"]

    # Wait for beacon
    beacon = wait_for_beacon(scan_token, "checkov_external_checks", BEACON_TIMEOUT_S)
    assert (
        beacon is not None
    ), "prerequisite: beacon should arrive for iac/checkov_external_checks"

    # Check scan detail
    detail = api(f"/api/scans/{scan_id}")
    assert detail.status_code == 200
    d = detail.json()
    assert (
        d.get("beacon_count", 0) > 0
    ), f"scan detail shows beacon_count=0 after beacon arrived: {d}"
