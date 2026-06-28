"""Pure ``disable_extensibility`` sanitization logic, per analyzer (§4).

These functions implement the "safe path" transformations and are intentionally
pure (string-in/string-out or simple filesystem mutations) so they can be unit
tested directly without invoking checkov/rubocop/eslint/npm.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# checkov: strip external-checks-dir from .checkov.yml
# ---------------------------------------------------------------------------


def strip_checkov_external_checks(yaml_text: str) -> str:
    """Remove the ``external-checks-dir`` block from a .checkov.yml body.

    Handles both the YAML list form::

        external-checks-dir:
          - checkov_checks

    and an inline form ``external-checks-dir: [checkov_checks]`` / scalar. We do
    a line-oriented strip (no YAML lib needed): drop the key line and any
    immediately-following indented list items.
    """
    lines = yaml_text.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if not skipping and re.match(r"^external-checks-dir\s*:", stripped):
            # Start skipping this key; if it's inline (value on same line) we
            # only drop this one line, otherwise also drop indented children.
            inline_value = stripped.split(":", 1)[1].strip()
            skipping = inline_value == ""
            continue
        if skipping:
            # Continue skipping indented list items / block scalars.
            if line.startswith((" ", "\t")) and (
                stripped.startswith("-") or stripped == "" or ":" not in stripped
            ):
                continue
            skipping = False
        out.append(line)
    result = "\n".join(out)
    # Preserve a trailing newline if the original had one.
    if yaml_text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def checkov_external_checks_args(checks_dir: Path | None) -> list[str]:
    """Build the ``--external-checks-dir`` args for the vulnerable path.

    Returns an empty list when ``checks_dir`` is None (mitigated path passes no
    external checks dir at all).
    """
    if checks_dir is None:
        return []
    return ["--external-checks-dir", str(checks_dir)]


# ---------------------------------------------------------------------------
# setup.py / gemspec: static metadata parse (no exec)
# ---------------------------------------------------------------------------

_SETUP_NAME_RE = re.compile(r"""name\s*=\s*['"]([^'"]+)['"]""")
_SETUP_VERSION_RE = re.compile(r"""version\s*=\s*['"]([^'"]+)['"]""")


def parse_setup_metadata(setup_py_text: str) -> tuple[str | None, str | None]:
    """Statically extract (name, version) from setup.py without executing it."""
    name_m = _SETUP_NAME_RE.search(setup_py_text)
    ver_m = _SETUP_VERSION_RE.search(setup_py_text)
    return (
        name_m.group(1) if name_m else None,
        ver_m.group(1) if ver_m else None,
    )


_GEMSPEC_NAME_RE = re.compile(r"""\.name\s*=\s*['"]([^'"]+)['"]""")
_GEMSPEC_VERSION_RE = re.compile(r"""\.version\s*=\s*['"]([^'"]+)['"]""")


def parse_gemspec_metadata(gemspec_text: str) -> tuple[str | None, str | None]:
    """Statically extract (name, version) from a .gemspec without evaluating it."""
    name_m = _GEMSPEC_NAME_RE.search(gemspec_text)
    ver_m = _GEMSPEC_VERSION_RE.search(gemspec_text)
    return (
        name_m.group(1) if name_m else None,
        ver_m.group(1) if ver_m else None,
    )


# ---------------------------------------------------------------------------
# npm: lifecycle scripts disabled via the real --ignore-scripts flag
# ---------------------------------------------------------------------------


def npm_install_args(*, disable_extensibility: bool) -> list[str]:
    """Build ``npm install`` args; add ``--ignore-scripts`` when mitigated (§4)."""
    args = ["install"]
    if disable_extensibility:
        args.append("--ignore-scripts")
    return args


# ---------------------------------------------------------------------------
# eslint: ignore .eslintrc.js via --no-eslintrc
# ---------------------------------------------------------------------------


def eslint_args(target: str, *, disable_extensibility: bool) -> list[str]:
    """Build eslint args; add ``--no-eslintrc`` when mitigated (§4)."""
    args: list[str] = []
    if disable_extensibility:
        args.append("--no-eslintrc")
    args.append(target)
    return args


# ---------------------------------------------------------------------------
# rubocop: strip `require:` lines from .rubocop.yml
# ---------------------------------------------------------------------------


def strip_rubocop_requires(yaml_text: str) -> str:
    """Remove the ``require:`` block from a .rubocop.yml body.

    Drops the ``require:`` key line and any immediately-following indented list
    items, leaving the rest of the config intact.
    """
    lines = yaml_text.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if not skipping and re.match(r"^require\s*:", stripped):
            inline_value = stripped.split(":", 1)[1].strip()
            skipping = inline_value == ""
            continue
        if skipping:
            if line.startswith((" ", "\t")) and (
                stripped.startswith("-") or stripped == "" or ":" not in stripped
            ):
                continue
            skipping = False
        out.append(line)
    result = "\n".join(out)
    if yaml_text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result
