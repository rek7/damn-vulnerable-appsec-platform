"""Shared pytest fixtures for the worker test suite.

These tests must pass WITHOUT the heavy analyzer toolchains installed; any test
that needs a real tool is gated behind ``@pytest.mark.skipif(shutil.which(...))``.
The watermark startup check is disabled for the test process so importing the app
package never calls ``sys.exit``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Disable the hard-exit boot check before any app import happens.
os.environ.setdefault("DVAP_SKIP_WATERMARK_CHECK", "1")
os.environ["DVAP_EXTRA_SEEDS_FILE"] = "__dvap_no_extra_seeds_for_tests__"

# The synthetic seed contents the worker expects (mirror seeds/synthetic.env).
GOOD_SEEDS = {
    "AWS_ACCESS_KEY_ID": "AKIA_FAKE_DVSEXAMPLE000",
    "AWS_SECRET_ACCESS_KEY": "FAKEdvsSecretKeyDoNotUse00000000000000FAKE",
    "AWS_CANARY_ACCESS_KEY_ID": "AKIAFAKECANARY000001",
    "AWS_CANARY_SECRET_ACCESS_KEY": (
        "FAKEAwsCanarySecretKeyForDVAPDoNotUse000000000FAKE"
    ),
    "AWS_SESSION_TOKEN": "FQoGZXIvYXdzEFAKEdvapCanarySessionTokenDoNotUseFAKE",
    "GITHUB_TOKEN": "ghp_FAKE0000dvsExampleToken0000000000",
    "GITHUB_CANARY_TOKEN": "ghp_FAKEdvapCanaryGithubToken000000000000",
    "NPM_TOKEN": "npm_FAKEdvapCanaryPublishToken000000000000",
    "DATABASE_URL": "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    "POSTGRES_CANARY_DSN": "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    "DVAP_DATABASE_URL": "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    "LATERAL_MOVEMENT_DB_URL": (
        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap"
    ),
    "STRIPE_API_KEY": "sk_live_FAKE_dvs_0000example0000",
    "SLACK_WEBHOOK_URL": "https://hooks.slack.invalid/services/TFAKE/BFAKE/FAKEdvapWebhookDoNotUse",
}
GOOD_TOKEN = "eyJhbGciFAKE.dvsFAKEserviceaccounttoken.doNotUseFAKE"


def write_env_file(path: Path, seeds: dict[str, str]) -> Path:
    """Write a KEY=VALUE .env file at ``path``."""
    path.write_text(
        "\n".join(f"{k}={v}" for k, v in seeds.items()) + "\n", encoding="utf-8"
    )
    return path


@pytest.fixture
def synthetic_seeds(tmp_path: Path) -> dict[str, Path]:
    """Create a valid synthetic seeds file + k8s token in a temp dir.

    Returns a dict with the seed-file path, token-src path, and a k8s token
    destination path -- all under tmp so tests never touch the real seeds dir.
    """
    seeds_file = write_env_file(tmp_path / "synthetic.env", GOOD_SEEDS)
    token_src = tmp_path / "k8s-sa-token"
    token_src.write_text(GOOD_TOKEN, encoding="utf-8")
    return {
        "seeds_file": seeds_file,
        "token_src": token_src,
        "token_dest": tmp_path / "k8s_token_out",
    }


@pytest.fixture
def evil_repos_dir() -> Path:
    """Absolute path to the bundled evil-repos (sibling of the worker package)."""
    return Path(__file__).resolve().parent.parent.parent / "evil-repos"


@pytest.fixture
def seed_env(synthetic_seeds: dict[str, Path]) -> Iterator[dict[str, Path]]:
    """Point the worker config env vars at the temp synthetic seeds."""
    prev = {
        k: os.environ.get(k)
        for k in ("DVAP_SEEDS_FILE", "DVAP_K8S_TOKEN_SRC", "DVAP_K8S_TOKEN_PATH")
    }
    os.environ["DVAP_SEEDS_FILE"] = str(synthetic_seeds["seeds_file"])
    os.environ["DVAP_K8S_TOKEN_SRC"] = str(synthetic_seeds["token_src"])
    os.environ["DVAP_K8S_TOKEN_PATH"] = str(synthetic_seeds["token_dest"])
    try:
        yield synthetic_seeds
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
