"""Tests for the SSRF guard (CONTRACTS.md §13)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.ssrf import SSRFError, validate_git_url


def _mock_resolve_public(host: str, port: object = None) -> list[tuple[object, ...]]:
    """Simulate a public IP for allowlisted hosts (e.g. github.com -> 140.82.114.4)."""
    return [(None, None, None, None, ("140.82.114.4", 0))]


def _mock_resolve_private(host: str, port: object = None) -> list[tuple[object, ...]]:
    """Simulate a private IP for an allowlisted host."""
    return [(None, None, None, None, ("192.168.1.1", 0))]


def _mock_resolve_loopback(host: str, port: object = None) -> list[tuple[object, ...]]:
    return [(None, None, None, None, ("127.0.0.1", 0))]


def _mock_resolve_metadata(host: str, port: object = None) -> list[tuple[object, ...]]:
    return [(None, None, None, None, ("169.254.169.254", 0))]


def _mock_resolve_link_local(
    host: str, port: object = None
) -> list[tuple[object, ...]]:
    return [(None, None, None, None, ("169.254.0.1", 0))]


# ---------------------------------------------------------------------------
# Accept cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/foo/bar",
        "https://github.com/foo/bar.git",
        "https://gitlab.com/org/repo",
        "https://bitbucket.org/team/project",
        "https://codeberg.org/user/repo",
    ],
)
def test_accept_valid_urls(url: str) -> None:
    with patch("app.ssrf.socket.getaddrinfo", side_effect=_mock_resolve_public):
        validate_git_url(url)  # should not raise


# ---------------------------------------------------------------------------
# Reject: scheme
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/foo/bar",
        "git://github.com/foo/bar",
        "ssh://github.com/foo/bar",
        "file:///etc/passwd",
        "ftp://github.com/foo/bar",
    ],
)
def test_reject_bad_scheme(url: str) -> None:
    with pytest.raises(SSRFError, match="https"):
        validate_git_url(url)


# ---------------------------------------------------------------------------
# Reject: host not in allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/repo",
        "https://sub.github.com/repo",  # subdomain not allowed in v1
        "https://github.com.evil.com/repo",
        "https://notgithub.com/repo",
    ],
)
def test_reject_disallowed_host(url: str) -> None:
    with pytest.raises(SSRFError):
        validate_git_url(url)


# ---------------------------------------------------------------------------
# Reject: userinfo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://user@github.com/repo",
        "https://user:pass@github.com/repo",
    ],
)
def test_reject_userinfo(url: str) -> None:
    with pytest.raises(SSRFError, match="userinfo"):
        validate_git_url(url)


# ---------------------------------------------------------------------------
# Reject: private / loopback / link-local / metadata resolved IPs
# ---------------------------------------------------------------------------


def test_reject_private_ip() -> None:
    with (
        patch("app.ssrf.socket.getaddrinfo", side_effect=_mock_resolve_private),
        pytest.raises(SSRFError, match="private"),
    ):
        validate_git_url("https://github.com/foo/bar")


def test_reject_loopback_ip() -> None:
    with (
        patch("app.ssrf.socket.getaddrinfo", side_effect=_mock_resolve_loopback),
        pytest.raises(SSRFError),
    ):
        validate_git_url("https://github.com/foo/bar")


def test_reject_metadata_ip() -> None:
    with (
        patch("app.ssrf.socket.getaddrinfo", side_effect=_mock_resolve_metadata),
        pytest.raises(SSRFError, match="metadata"),
    ):
        validate_git_url("https://github.com/foo/bar")


def test_reject_link_local_ip() -> None:
    with (
        patch("app.ssrf.socket.getaddrinfo", side_effect=_mock_resolve_link_local),
        pytest.raises(SSRFError),
    ):
        validate_git_url("https://github.com/foo/bar")
