"""Git-URL SSRF guard accept/reject + beacon host block (§13).

DNS resolution is skipped (``resolve=False``) for accept cases so the suite does
not depend on network access; every non-network rule is still enforced.
"""

from __future__ import annotations

import pytest

from app import ssrf


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo.git",
        "https://gitlab.com/owner/repo",
        "https://bitbucket.org/owner/repo.git",
        "https://codeberg.org/owner/repo",
    ],
)
def test_allowlisted_hosts_accepted(url: str) -> None:
    assert ssrf.validate_git_url(url, resolve=False) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",  # wrong scheme
        "git://github.com/owner/repo",  # wrong scheme
        "ssh://git@github.com/owner/repo",  # wrong scheme
        "file:///etc/passwd",  # wrong scheme
        "https://evil.com/owner/repo",  # host not allowlisted
        "https://gist.github.com/owner/repo",  # subdomain not allowed (exact only)
        "https://github.com.evil.com/repo",  # look-alike host
        "https://user:pass@github.com/repo",  # embedded credentials
        "https://github.com@evil.com/repo",  # userinfo trick
    ],
)
def test_disallowed_urls_rejected(url: str) -> None:
    with pytest.raises(ssrf.SSRFError):
        ssrf.validate_git_url(url, resolve=False)


def test_resolution_rejects_private_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend github.com resolves to a private address -> must reject.
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda host: ["10.0.0.5"])
    with pytest.raises(ssrf.SSRFError):
        ssrf.validate_git_url("https://github.com/owner/repo", resolve=True)


def test_resolution_rejects_metadata_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda host: ["169.254.169.254"])
    with pytest.raises(ssrf.SSRFError):
        ssrf.validate_git_url("https://gitlab.com/owner/repo", resolve=True)


def test_resolution_accepts_public_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssrf, "_resolve_addresses", lambda host: ["140.82.112.3"])
    url = "https://github.com/owner/repo"
    assert ssrf.validate_git_url(url, resolve=True) == url


def test_beacon_host_block_loopback_and_metadata() -> None:
    assert ssrf.is_blocked_beacon_host("127.0.0.1") is True
    assert ssrf.is_blocked_beacon_host("169.254.169.254") is True
    assert ssrf.is_blocked_beacon_host("169.254.170.2") is True
    assert ssrf.is_blocked_beacon_host("10.1.2.3") is True
    assert ssrf.is_blocked_beacon_host("172.16.0.2") is True
    assert ssrf.is_blocked_beacon_host("93.184.216.34") is True
    assert ssrf.is_blocked_beacon_host("example.com") is True
    assert ssrf.is_blocked_beacon_host("egress.blocked.invalid") is True
    assert ssrf.is_blocked_beacon_host("") is True


def test_beacon_host_allows_internal_listener() -> None:
    assert ssrf.is_blocked_beacon_host("listener") is False
