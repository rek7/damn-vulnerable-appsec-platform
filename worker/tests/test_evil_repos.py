"""Containment test: no evil-repo file references a non-placeholder host/IP (§8).

Also verifies that every bundled sample repo exists, carries the placeholders,
and templates cleanly into a workdir.
"""

from __future__ import annotations

import re
from pathlib import Path

from app import config, fetch, templating

# Allowed network reference: a URL whose host is the placeholder OR a bare scheme
# prefix (e.g. ``"http://"`` concatenated with a variable). We capture only the
# host token (everything up to the first ``:``, ``/`` or whitespace) and reject
# any URL that hard-codes a real host directly after the scheme.
_URL_RE = re.compile(r"https?://([^/\s:'\"]*)")
# IPv4 literals are never allowed anywhere in evil-repos.
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Substrings that legitimately appear as the host right after ``://`` in payload
# code:
#   - empty (scheme is concatenated with a host *variable* in the next token)
#   - the listener-host placeholder
#   - the Ruby interpolation of the host variable (``#{LISTENER_HOST}``)
_ALLOWED_URL_HOST_TOKENS = {
    "",
    config.PLACEHOLDER_LISTENER_HOST,
    "#{LISTENER_HOST}",  # ruby string interpolation
}


def _iter_repo_files() -> list[Path]:
    root = Path(__file__).resolve().parent.parent.parent / "evil-repos"
    files = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            files.append(path)
    return files


def test_evil_repos_have_no_external_host_urls() -> None:
    offenders: list[str] = []
    for path in _iter_repo_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in _URL_RE.finditer(text):
            host_token = match.group(1)
            if host_token not in _ALLOWED_URL_HOST_TOKENS:
                offenders.append(f"{path}: {match.group(0)!r}")
    assert not offenders, f"external host URL literals found: {offenders}"


def test_evil_repos_have_no_ipv4_literals() -> None:
    offenders: list[str] = []
    for path in _iter_repo_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in _IPV4_RE.finditer(text):
            offenders.append(f"{path}: {match.group(0)!r}")
    assert not offenders, f"IPv4 literals found: {offenders}"


def test_each_module_sample_repo_exists() -> None:
    for module, entries in fetch.MODULE_SAMPLE_REPOS.items():
        for _vector, rel in entries:
            repo = config.evil_repos_root() / rel
            assert repo.is_dir(), f"missing sample repo for {module}: {repo}"


def test_symlink_repo_has_leak_symlink() -> None:
    repo = config.evil_repos_root() / "secrets" / "symlink"
    leak = repo / "leak"
    assert leak.is_symlink(), "secrets/symlink/leak must be a symlink"


def test_symlink_sample_copy_materializes_proc_environ_link(tmp_path: Path) -> None:
    fetch.copy_sample("secrets", "symlink_traversal", tmp_path)
    leak = tmp_path / "leak"
    assert leak.is_symlink()
    assert leak.readlink() == Path("/proc/self/environ")


def test_sample_copy_and_template_substitutes_placeholders(tmp_path: Path) -> None:
    # Copy the checkov sample and template it; placeholders must all resolve.
    fetch.copy_sample("iac", "checkov_external_checks", tmp_path)
    subs = templating.build_substitutions(
        scan_token="deadbeef0000",
        vector="checkov_external_checks",
        listener_host="listener",
        listener_port=9000,
        block_egress=False,
    )
    templating.apply_to_tree(tmp_path, subs)
    payload = (tmp_path / "checkov_checks" / "extra_check.py").read_text()
    assert "__DVAP_" not in payload
    assert "deadbeef0000" in payload
    assert "listener" in payload


def test_block_egress_templating_uses_blackhole(tmp_path: Path) -> None:
    fetch.copy_sample("sca", "setup_py_exec", tmp_path)
    subs = templating.build_substitutions(
        scan_token="tok",
        vector="setup_py_exec",
        listener_host="listener",
        listener_port=9000,
        block_egress=True,
    )
    templating.apply_to_tree(tmp_path, subs)
    payload = (tmp_path / "setup.py").read_text()
    assert "egress.blocked.invalid" in payload
    assert "listener" not in payload
