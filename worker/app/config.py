"""Runtime configuration knobs and constants for the DVAP worker.

Everything that a deployment might want to override lives here behind an env var,
with container-friendly defaults. Pure module: importing it has no side effects.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Placeholders (must match the literals embedded in every evil-repo, §8)
# ---------------------------------------------------------------------------

PLACEHOLDER_SCAN_TOKEN = "__DVAP_SCAN_TOKEN__"
PLACEHOLDER_VECTOR = "__DVAP_VECTOR__"
PLACEHOLDER_LISTENER_HOST = "__DVAP_LISTENER_HOST__"
PLACEHOLDER_LISTENER_PORT = "__DVAP_LISTENER_PORT__"

# Substituted for the listener host when block_egress is on (does not resolve).
BLACKHOLE_HOST = "egress.blocked.invalid"

# ---------------------------------------------------------------------------
# Synthetic secrets / watermark (§7)
# ---------------------------------------------------------------------------

WATERMARK = "FAKE"  # case-insensitive substring every seed value must contain

# Env keys injected into analyzer subprocesses (the keys present in seeds file).
SECRET_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_CANARY_ACCESS_KEY_ID",
    "AWS_CANARY_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_CANARY_TOKEN",
    "NPM_TOKEN",
    "APP_DATABASE_URL",
    "STRIPE_API_KEY",
    "SLACK_WEBHOOK_URL",
)


def seeds_file_candidates() -> list[Path]:
    """Ordered candidate paths for the synthetic seeds env file (§7)."""
    override = os.environ.get("DVAP_SEEDS_FILE")
    if override:
        return [Path(override)]
    return [
        Path("/app/seeds/synthetic.env"),
        Path("seeds/synthetic.env"),
        Path("../seeds/synthetic.env"),
    ]


def extra_seeds_file_candidates() -> list[Path]:
    """Ordered candidate paths for optional local seed overlays."""
    override = os.environ.get("DVAP_EXTRA_SEEDS_FILE")
    if override:
        return [Path(override)]
    return [
        Path("/app/seeds/canarytokens.local.env"),
        Path("seeds/canarytokens.local.env"),
        Path("../seeds/canarytokens.local.env"),
    ]


def k8s_token_src_candidates() -> list[Path]:
    """Where to read the fake k8s SA token *contents* from (alongside seeds)."""
    override = os.environ.get("DVAP_K8S_TOKEN_SRC")
    if override:
        return [Path(override)]
    return [
        Path("/app/seeds/k8s-sa-token"),
        Path("seeds/k8s-sa-token"),
        Path("../seeds/k8s-sa-token"),
    ]


def k8s_token_dest() -> Path:
    """Where the worker writes the k8s SA token for a scan (overridable)."""
    return Path(
        os.environ.get(
            "DVAP_K8S_TOKEN_PATH",
            "/var/run/secrets/kubernetes.io/serviceaccount/token",
        )
    )


def evil_repos_root() -> Path:
    """Root of the bundled evil-repos (overridable for tests)."""
    override = os.environ.get("DVAP_EVIL_REPOS_DIR")
    if override:
        return Path(override)
    # Container layout (COPY evil-repos/ /app/evil-repos), then repo-relative.
    for candidate in (Path("/app/evil-repos"), Path("evil-repos")):
        if candidate.is_dir():
            return candidate
    # Fallback: sibling of the worker package source tree.
    return Path(__file__).resolve().parent.parent.parent / "evil-repos"


# ---------------------------------------------------------------------------
# Fetch caps (§13)
# ---------------------------------------------------------------------------

GIT_CLONE_TIMEOUT_S = int(os.environ.get("DVAP_GIT_TIMEOUT", "30"))
GIT_CLONE_MAX_BYTES = int(os.environ.get("DVAP_GIT_MAX_BYTES", str(50 * 1024 * 1024)))

# Git URL host allowlist (exact host match only, §13).
GIT_HOST_ALLOWLIST = frozenset(
    {"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"}
)

# ---------------------------------------------------------------------------
# Beacon
# ---------------------------------------------------------------------------

BEACON_TIMEOUT_S = float(os.environ.get("DVAP_BEACON_TIMEOUT", "5"))

# Metadata IPs that must never be reachable (§13).
METADATA_IPS = frozenset({"169.254.169.254", "169.254.170.2"})
