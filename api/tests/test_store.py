"""Tests for API store helpers."""

from __future__ import annotations

import pytest

from app.store import PostgresStore


def _credential_map() -> dict[str, str]:
    rows = PostgresStore._integration_credential_rows()
    return {credential_type: value for _, _, credential_type, _, value, _ in rows}


def test_integration_credentials_use_canary_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIANONCANARY0000000")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "noncanary-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_noncanary")
    monkeypatch.setenv("AWS_CANARY_ACCESS_KEY_ID", "AKIACANARY0000000000")
    monkeypatch.setenv("AWS_CANARY_SECRET_ACCESS_KEY", "canary-secret")
    monkeypatch.setenv("GITHUB_CANARY_TOKEN", "ghp_canary")

    credentials = _credential_map()

    assert credentials["aws_access_key_id"] == "AKIACANARY0000000000"
    assert credentials["aws_secret_access_key"] == "canary-secret"
    assert credentials["github_token"] == "ghp_canary"


def test_integration_credentials_do_not_fallback_to_non_canary_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIANONCANARY0000000")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "noncanary-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_noncanary")
    monkeypatch.delenv("AWS_CANARY_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_CANARY_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("GITHUB_CANARY_TOKEN", raising=False)

    credentials = _credential_map()

    assert credentials["aws_access_key_id"] == "AKIAFAKECANARY000001"
    assert (
        credentials["aws_secret_access_key"]
        == "FAKEAwsCanarySecretKeyForDVAPDoNotUse000000000FAKE"
    )
    assert credentials["github_token"] == "ghp_FAKEdvapCanaryGithubToken000000000000"
