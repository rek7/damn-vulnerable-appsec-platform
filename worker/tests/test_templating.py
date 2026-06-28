"""Placeholder templating + block_egress blackhole substitution (§4, §8)."""

from __future__ import annotations

from pathlib import Path

from app import config, templating


def test_substitutions_use_real_host_when_egress_allowed() -> None:
    subs = templating.build_substitutions(
        scan_token="tok123",
        vector="checkov_external_checks",
        listener_host="listener",
        listener_port=9000,
        block_egress=False,
    )
    assert subs[config.PLACEHOLDER_SCAN_TOKEN] == "tok123"
    assert subs[config.PLACEHOLDER_VECTOR] == "checkov_external_checks"
    assert subs[config.PLACEHOLDER_LISTENER_HOST] == "listener"
    assert subs[config.PLACEHOLDER_LISTENER_PORT] == "9000"


def test_substitutions_blackhole_when_egress_blocked() -> None:
    subs = templating.build_substitutions(
        scan_token="tok123",
        vector="v",
        listener_host="listener",
        listener_port=9000,
        block_egress=True,
    )
    assert subs[config.PLACEHOLDER_LISTENER_HOST] == config.BLACKHOLE_HOST
    assert config.BLACKHOLE_HOST == "egress.blocked.invalid"


def test_substitute_text_replaces_all_placeholders() -> None:
    raw = (
        "host=__DVAP_LISTENER_HOST__ port=__DVAP_LISTENER_PORT__ "
        "tok=__DVAP_SCAN_TOKEN__ vec=__DVAP_VECTOR__"
    )
    subs = templating.build_substitutions(
        scan_token="abc",
        vector="setup_py_exec",
        listener_host="listener",
        listener_port=9000,
        block_egress=False,
    )
    out = templating.substitute_text(raw, subs)
    assert "__DVAP_" not in out
    assert out == "host=listener port=9000 tok=abc vec=setup_py_exec"


def test_apply_to_tree_rewrites_files_and_keeps_symlinks(tmp_path: Path) -> None:
    (tmp_path / "payload.py").write_text(
        "HOST='__DVAP_LISTENER_HOST__'\nTOK='__DVAP_SCAN_TOKEN__'\n",
        encoding="utf-8",
    )
    # A symlink must not be rewritten or followed.
    target = tmp_path / "real.txt"
    target.write_text("__DVAP_SCAN_TOKEN__", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    subs = templating.build_substitutions(
        scan_token="zzz",
        vector="v",
        listener_host="egress.blocked.invalid",
        listener_port=9000,
        block_egress=True,
    )
    templating.apply_to_tree(tmp_path, subs)

    body = (tmp_path / "payload.py").read_text()
    assert "egress.blocked.invalid" in body
    assert "zzz" in body and "__DVAP_" not in body
    # The symlink is still a symlink (not rewritten into a real file).
    assert link.is_symlink()
