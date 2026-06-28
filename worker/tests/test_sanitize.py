"""Per-analyzer disable_extensibility sanitization LOGIC (§4), no tools invoked."""

from __future__ import annotations

from pathlib import Path

from app import sanitize

# --- checkov ---------------------------------------------------------------


def test_strip_checkov_external_checks_removes_list_block() -> None:
    yaml = (
        "directory:\n"
        "  - .\n"
        "external-checks-dir:\n"
        "  - checkov_checks\n"
        "compact: true\n"
    )
    out = sanitize.strip_checkov_external_checks(yaml)
    assert "external-checks-dir" not in out
    assert "checkov_checks" not in out
    # Unrelated keys are preserved.
    assert "directory:" in out
    assert "compact: true" in out


def test_strip_checkov_external_checks_removes_inline_form() -> None:
    yaml = "external-checks-dir: [checkov_checks]\ncompact: true\n"
    out = sanitize.strip_checkov_external_checks(yaml)
    assert "external-checks-dir" not in out
    assert "compact: true" in out


def test_checkov_args_present_only_when_dir_given(tmp_path: Path) -> None:
    assert sanitize.checkov_external_checks_args(None) == []
    args = sanitize.checkov_external_checks_args(tmp_path)
    assert args == ["--external-checks-dir", str(tmp_path)]


# --- setup.py / gemspec static parse ---------------------------------------


def test_parse_setup_metadata() -> None:
    src = "setup(\n  name='dvap-canary',\n  version='0.0.1',\n)\n"
    assert sanitize.parse_setup_metadata(src) == ("dvap-canary", "0.0.1")


def test_parse_gemspec_metadata() -> None:
    src = "spec.name = 'dvap-canary'\nspec.version = '0.0.1'\n"
    assert sanitize.parse_gemspec_metadata(src) == ("dvap-canary", "0.0.1")


# --- npm --------------------------------------------------------------------


def test_npm_install_args_adds_ignore_scripts_when_mitigated() -> None:
    assert sanitize.npm_install_args(disable_extensibility=False) == ["install"]
    assert sanitize.npm_install_args(disable_extensibility=True) == [
        "install",
        "--ignore-scripts",
    ]


# --- eslint -----------------------------------------------------------------


def test_eslint_args_adds_no_eslintrc_when_mitigated() -> None:
    assert sanitize.eslint_args(".", disable_extensibility=False) == ["."]
    assert sanitize.eslint_args(".", disable_extensibility=True) == [
        "--no-eslintrc",
        ".",
    ]


# --- rubocop ----------------------------------------------------------------


def test_strip_rubocop_requires_removes_require_block() -> None:
    yaml = "require:\n" "  - ./dvap_cop.rb\n" "AllCops:\n" "  NewCops: disable\n"
    out = sanitize.strip_rubocop_requires(yaml)
    assert "require:" not in out
    assert "dvap_cop.rb" not in out
    # Unrelated config preserved.
    assert "AllCops:" in out
    assert "NewCops: disable" in out
