"""Watermark startup-check + env/seed setup (§7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import config, seeds
from tests.conftest import GOOD_SEEDS, GOOD_TOKEN, write_env_file


def test_watermark_passes_for_good_seeds(synthetic_seeds: dict[str, Path]) -> None:
    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])
    token = seeds.load_k8s_token(synthetic_seeds["token_src"])
    # Should not raise.
    seeds.verify_watermark(loaded, token)
    assert loaded == GOOD_SEEDS
    assert token == GOOD_TOKEN


def test_watermark_fails_when_a_seed_value_lacks_fake(tmp_path: Path) -> None:
    bad = dict(GOOD_SEEDS)
    bad["GITHUB_TOKEN"] = "ghp_REALdangerousLookingToken000000"  # no FAKE
    bad_file = write_env_file(tmp_path / "bad.env", bad)
    loaded = seeds.load_seeds(bad_file)
    with pytest.raises(seeds.WatermarkError):
        seeds.verify_watermark(loaded, GOOD_TOKEN)


def test_watermark_fails_when_token_lacks_fake(
    synthetic_seeds: dict[str, Path],
) -> None:
    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])
    with pytest.raises(seeds.WatermarkError):
        seeds.verify_watermark(loaded, "real.looking.jwt.token")


def test_watermark_case_insensitive() -> None:
    assert seeds.has_watermark("prefix-fAkE-suffix")
    assert seeds.has_watermark("FAKE")
    assert not seeds.has_watermark("nothing here")


def test_load_seeds_overlays_canarytokens_file(
    synthetic_seeds: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extra_file = write_env_file(
        tmp_path / "canarytokens.local.env",
        {
            "DVAP_ALLOW_EXTERNAL_CANARYTOKENS": "1",
            "AWS_CANARY_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_CANARY_SECRET_ACCESS_KEY": (
                "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            ),
        },
    )
    monkeypatch.setenv("DVAP_EXTRA_SEEDS_FILE", str(extra_file))
    monkeypatch.setenv("DVAP_ALLOW_EXTERNAL_CANARYTOKENS", "1")

    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])

    assert loaded["AWS_CANARY_ACCESS_KEY_ID"] == "AKIAIOSFODNN7EXAMPLE"
    assert (
        loaded["AWS_CANARY_SECRET_ACCESS_KEY"]
        == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    )
    seeds.verify_watermark(loaded, GOOD_TOKEN)


def test_watermark_rejects_canarytokens_org_keys_without_opt_in() -> None:
    loaded = dict(GOOD_SEEDS)
    loaded["AWS_CANARY_ACCESS_KEY_ID"] = "AKIAIOSFODNN7EXAMPLE"
    loaded["AWS_CANARY_SECRET_ACCESS_KEY"] = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    with pytest.raises(seeds.WatermarkError):
        seeds.verify_watermark(loaded, GOOD_TOKEN)


def test_build_subprocess_env_includes_seeds_by_default(
    synthetic_seeds: dict[str, Path],
) -> None:
    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])
    env = seeds.build_subprocess_env(loaded, strip_credentials=False)
    for key, value in GOOD_SEEDS.items():
        assert env[key] == value


def test_build_subprocess_env_strips_seeds_when_mitigated(
    synthetic_seeds: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])
    monkeypatch.setenv(
        "DVAP_DATABASE_URL",
        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    )
    monkeypatch.setenv(
        "LATERAL_MOVEMENT_DB_URL",
        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    )
    env = seeds.build_subprocess_env(loaded, strip_credentials=True)
    for key in GOOD_SEEDS:
        assert key not in env
    # Also every config secret key is scrubbed even if it leaked from os.environ.
    for key in config.SECRET_ENV_KEYS:
        assert key not in env


def test_stripped_subprocess_env_has_no_secret_scanner_findings(
    synthetic_seeds: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import secret_patterns

    loaded = seeds.load_seeds(synthetic_seeds["seeds_file"])
    monkeypatch.setenv(
        "DVAP_DATABASE_URL",
        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    )
    monkeypatch.setenv(
        "LATERAL_MOVEMENT_DB_URL",
        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap",
    )

    stripped = seeds.build_subprocess_env(loaded, strip_credentials=True)
    env_text = "\x00".join(f"{key}={value}" for key, value in stripped.items())

    assert "DVAP_DATABASE_URL" not in stripped
    assert "LATERAL_MOVEMENT_DB_URL" not in stripped
    assert secret_patterns.find_secrets_in_text(env_text) == []


def test_write_and_remove_k8s_token(synthetic_seeds: dict[str, Path]) -> None:
    dest = synthetic_seeds["token_dest"]
    written = seeds.write_k8s_token(GOOD_TOKEN, dest)
    assert written == dest
    assert dest.read_text(encoding="utf-8") == GOOD_TOKEN
    seeds.remove_k8s_token(dest)
    assert not dest.exists()


def test_write_k8s_token_noop_when_empty(synthetic_seeds: dict[str, Path]) -> None:
    assert seeds.write_k8s_token("", synthetic_seeds["token_dest"]) is None


def test_startup_check_returns_seeds_and_token(seed_env: dict[str, Path]) -> None:
    loaded, token = seeds.startup_watermark_check()
    assert loaded == GOOD_SEEDS
    assert token == GOOD_TOKEN
