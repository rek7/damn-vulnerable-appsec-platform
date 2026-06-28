"""Secret scanner: symlink-following (vulnerable) vs resolve_symlinks (§4, §13)."""

from __future__ import annotations

import os
from pathlib import Path

from app import config, secret_patterns
from app.analyzers import AnalyzerContext, secret_scanner
from app.analyzers.secret_scanner import _scan_with_env
from app.models import Mitigations
from tests.conftest import GOOD_SEEDS


def test_finds_secret_in_regular_file(tmp_path: Path) -> None:
    (tmp_path / "creds.txt").write_text(
        "AWS_ACCESS_KEY_ID=AKIA_FAKE_DVSEXAMPLE000\n", encoding="utf-8"
    )
    findings = secret_patterns.scan_workdir(tmp_path, resolve_symlinks=False)
    assert "creds.txt" in findings
    assert "aws_access_key_id" in findings["creds.txt"]


def test_vulnerable_path_follows_symlink_outside_root(tmp_path: Path) -> None:
    # Secret lives OUTSIDE the workdir; a symlink inside points to it.
    outside = tmp_path / "outside"
    outside.mkdir()
    secret_file = outside / "secret.env"
    secret_file.write_text(
        "GITHUB_TOKEN=ghp_FAKE0000dvsExampleToken0000000000\n", encoding="utf-8"
    )
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "leak").symlink_to(secret_file)

    # Vulnerable: symlink is followed and the out-of-root secret is read.
    findings = secret_patterns.scan_workdir(workdir, resolve_symlinks=False)
    assert "leak" in findings
    assert "github_token" in findings["leak"]


def test_proc_environ_symlink_uses_effective_scan_env(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "leak").symlink_to("/proc/self/environ")

    scan_env = {**os.environ, **GOOD_SEEDS}
    findings = _scan_with_env(workdir, resolve_symlinks=False, env=scan_env)
    assert "leak" in findings
    assert set(findings["leak"]) == {
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "github_token",
        "npm_token",
        "postgres_url",
        "slack_webhook",
        "stripe_key",
    }

    stripped_env = dict(scan_env)
    for key in config.SECRET_ENV_KEYS:
        stripped_env.pop(key, None)
    assert _scan_with_env(workdir, resolve_symlinks=False, env=stripped_env) == {}


def test_strip_credentials_still_beacons_empty_exfil(
    tmp_path: Path, monkeypatch
) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "leak").symlink_to("/proc/self/environ")

    stripped_env = dict(os.environ)
    for key in config.SECRET_ENV_KEYS:
        stripped_env.pop(key, None)

    captured: dict[str, str] = {}

    def fake_send_beacon(
        listener_host: str,
        listener_port: int,
        scan_token: str,
        vector: str,
        dotted: str,
    ) -> bool:
        captured["host"] = listener_host
        captured["token"] = scan_token
        captured["vector"] = vector
        captured["dotted"] = dotted
        return True

    monkeypatch.setattr(secret_scanner.beacon, "send_beacon", fake_send_beacon)
    result = secret_scanner.run(
        AnalyzerContext(
            workdir=workdir,
            mitigations=Mitigations(strip_credentials=True),
            scan_token="abcdef012345",
            listener_host="listener",
            listener_port=9000,
            env=stripped_env,
            seeds={},
            k8s_token="",
        )
    )

    assert result.status == "ok"
    assert "0 secret(s)" in result.summary
    assert captured == {
        "host": "listener",
        "token": "abcdef012345",
        "vector": "symlink_traversal",
        "dotted": "",
    }


def test_resolve_symlinks_skips_escaping_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret_file = outside / "secret.env"
    secret_file.write_text(
        "GITHUB_TOKEN=ghp_FAKE0000dvsExampleToken0000000000\n", encoding="utf-8"
    )
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "leak").symlink_to(secret_file)

    # Mitigated: the escaping symlink is skipped, so nothing is found.
    findings = secret_patterns.scan_workdir(workdir, resolve_symlinks=True)
    assert findings == {}


def test_resolve_symlinks_keeps_in_root_symlink(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    real = workdir / "real.env"
    real.write_text(
        "STRIPE_API_KEY=sk_live_FAKE_dvs_0000example0000\n", encoding="utf-8"
    )
    # A symlink whose target stays inside the workdir is still read when resolved.
    (workdir / "alias.env").symlink_to(real)
    findings = secret_patterns.scan_workdir(workdir, resolve_symlinks=True)
    # Both the real file and the in-root symlink are read.
    assert "real.env" in findings
    assert "alias.env" in findings


def test_all_synthetic_patterns_match() -> None:
    text = (
        "AWS_ACCESS_KEY_ID=AKIA_FAKE_DVSEXAMPLE000\n"
        "AWS_SECRET_ACCESS_KEY=FAKEdvsSecretKeyDoNotUse00000000000000FAKE\n"
        "AWS_CANARY_ACCESS_KEY_ID=AKIAFAKECANARY000001\n"
        "AWS_CANARY_SECRET_ACCESS_KEY=FAKEAwsCanarySecretKeyForDVAPDoNotUse000000000FAKE\n"
        "AWS_SESSION_TOKEN=FQoGZXIvYXdzEFAKEdvapCanarySessionTokenDoNotUseFAKE\n"
        "GITHUB_TOKEN=ghp_FAKE0000dvsExampleToken0000000000\n"
        "GITHUB_CANARY_TOKEN=ghp_FAKEdvapCanaryGithubToken000000000000\n"
        "NPM_TOKEN=npm_FAKEdvapCanaryPublishToken000000000000\n"
        "APP_DATABASE_URL=postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap\n"
        "STRIPE_API_KEY=sk_live_FAKE_dvs_0000example0000\n"
        "SLACK_WEBHOOK_URL=https://hooks.slack.invalid/services/TFAKE/BFAKE/FAKEdvapWebhookDoNotUse\n"
    )
    matched = set(secret_patterns.find_secrets_in_text(text))
    assert matched == {
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "github_token",
        "npm_token",
        "postgres_url",
        "slack_webhook",
        "stripe_key",
    }


def test_patterns_ignore_non_watermarked_secret_shapes() -> None:
    text = (
        "AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n"
        "GITHUB_ACCESS_TOKEN=ghp_realisticTokenButNoWatermark000000\n"
        "APP_DATABASE_URL=postgres://demo:password@db.example.invalid:5432/demo\n"
        "NPM_TOKEN=npm_realisticTokenButNoWatermark\n"
        "STRIPE_API_KEY=sk_" "live_realisticTokenButNoWatermark\n"
    )
    assert secret_patterns.find_secrets_in_text(text) == []
