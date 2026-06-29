"""Repo fetchers: sample copy, archive extract (zip-slip guarded), git clone.

The extract/clone guards are part of the containment boundary (§13): even though
the *contents* of a fetched repo are meant to execute, the fetch itself must not
let an attacker escape the workdir (zip-slip) or point the worker at the
operator's own network (git SSRF).
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

from . import config, ssrf

# Map module -> bundled sample repo subdirs (relative to sample_repos_root).
# Each tuple is (vector_id, relative_path).
MODULE_SAMPLE_REPOS: dict[str, list[tuple[str, str]]] = {
    "iac": [
        ("checkov_external_checks", "iac/checkov-external-checks"),
        ("terragrunt_before_hook", "iac/terragrunt-before-hook"),
    ],
    "sca": [
        ("setup_py_exec", "sca/setup-exec"),
        ("gemspec_eval", "sca/gemspec-eval"),
        ("npm_lifecycle", "sca/npm-lifecycle"),
    ],
    "sast": [
        ("eslintrc_js_exec", "sast/eslintrc"),
        ("rubocop_require", "sast/rubocop-require"),
    ],
    "secrets": [("symlink_traversal", "secrets/symlink")],
}


class FetchError(RuntimeError):
    """Raised when a fetch fails (bad archive, oversized clone, etc.)."""


# ---------------------------------------------------------------------------
# Sample
# ---------------------------------------------------------------------------


def sample_repo_entries(module: str, vector: str | None) -> list[tuple[str, Path]]:
    """Resolve bundled sample repo entries for a module (+ optional vector).

    When ``vector`` is given, only that vector's repo is returned (sample
    isolation, §9). Otherwise every repo registered for the module is returned.
    """
    root = config.sample_repos_root()
    entries = MODULE_SAMPLE_REPOS.get(module, [])
    chosen = [
        (vec, root / rel) for (vec, rel) in entries if vector is None or vec == vector
    ]
    if not chosen:
        raise FetchError(f"no sample repo for module={module!r} vector={vector!r}")
    return chosen


def sample_repo_paths(module: str, vector: str | None) -> list[Path]:
    """Resolve bundled sample repo source dirs for a module (+ optional vector)."""
    return [path for _vector, path in sample_repo_entries(module, vector)]


def copy_sample_repo(src: Path, dest: Path) -> None:
    """Copy one bundled sample repo into ``dest`` (merging, symlinks kept)."""
    if not src.is_dir():
        raise FetchError(f"bundled sample repo missing: {src}")
    # Copy contents of src into dest (merging when multiple repos).
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir() and not item.is_symlink():
            shutil.copytree(item, target, dirs_exist_ok=True, symlinks=True)
        elif _is_secret_environ_link(src, item):
            target.unlink(missing_ok=True)
            target.symlink_to("/proc/self/environ")
        else:
            # copy2 with follow_symlinks=False preserves the symlink itself.
            shutil.copy2(item, target, follow_symlinks=False)


def _is_secret_environ_link(repo: Path, item: Path) -> bool:
    """True for the source fixture symlink that becomes /proc/self/environ.

    The checked-in source symlink is intentionally inert so containment tests can
    inspect ``sample-repos/`` without dereferencing a live test process's env. The
    worker materializes the real traversal target only inside scan workdirs.
    """
    return (
        item.name == "leak"
        and item.is_symlink()
        and len(repo.parts) >= 2
        and repo.parts[-2:] == ("secrets", "symlink")
    )


def copy_sample(module: str, vector: str | None, dest: Path) -> None:
    """Copy bundled sample repo contents for a module into ``dest``.

    ``symlinks=True`` is essential: the secrets/symlink repo's ``leak`` must be
    copied as a symlink, not dereferenced.
    """
    for src in sample_repo_paths(module, vector):
        copy_sample_repo(src, dest)


# ---------------------------------------------------------------------------
# Upload archive (zip-slip guard, §13)
# ---------------------------------------------------------------------------


def _is_within(root: Path, target: Path) -> bool:
    """True if ``target`` (resolved lexically) stays within ``root``."""
    root_res = os.path.normpath(str(root))
    target_res = os.path.normpath(str(target))
    return target_res == root_res or target_res.startswith(root_res + os.sep)


def _safe_member_path(root: Path, name: str) -> Path:
    """Resolve an archive entry name under ``root``, rejecting escapes.

    Rejects absolute paths and any ``..`` traversal that escapes the root.
    """
    if name.startswith("/") or name.startswith("\\"):
        raise FetchError(f"archive entry has absolute path: {name!r}")
    # Normalize and ensure it does not escape.
    candidate = Path(os.path.normpath(os.path.join(str(root), name)))
    if not _is_within(root, candidate):
        raise FetchError(f"archive entry escapes root (zip-slip): {name!r}")
    return candidate


def extract_zip(archive_path: Path, dest: Path) -> None:
    """Extract a .zip into ``dest`` with a zip-slip guard (§13)."""
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            name = info.filename
            target = _safe_member_path(dest, name)
            if name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def _tar_member_is_unsafe_symlink(root: Path, member: tarfile.TarInfo) -> bool:
    """True if a tar symlink/hardlink points outside the extraction root."""
    if not (member.issym() or member.islnk()):
        return False
    link_target = member.linkname
    if link_target.startswith("/"):
        return True
    member_dir = Path(os.path.dirname(os.path.join(str(root), member.name)))
    resolved = Path(os.path.normpath(str(member_dir / link_target)))
    return not _is_within(root, resolved)


def extract_tar(archive_path: Path, dest: Path) -> None:
    """Extract a .tar.gz into ``dest`` with zip-slip + symlink guards (§13)."""
    with tarfile.open(archive_path, "r:*") as tf:
        for member in tf.getmembers():
            # Validate destination path stays within root.
            _safe_member_path(dest, member.name)
            if _tar_member_is_unsafe_symlink(dest, member):
                raise FetchError(f"archive entry has unsafe symlink: {member.name!r}")
        # Every member validated above; ``filter="data"`` adds the stdlib's own
        # path/symlink sanitization as a second layer (and silences the 3.14
        # deprecation warning).
        tf.extractall(dest, filter="data")  # noqa: S202


def extract_archive(archive_path: Path, dest: Path) -> None:
    """Dispatch extraction by file extension (.zip / .tar.gz / .tgz)."""
    name = archive_path.name.lower()
    if name.endswith(".zip"):
        extract_zip(archive_path, dest)
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        extract_tar(archive_path, dest)
    else:
        raise FetchError(f"unsupported archive type: {archive_path.name!r}")


# ---------------------------------------------------------------------------
# Git clone (SSRF guard + caps, §13)
# ---------------------------------------------------------------------------


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            fp = Path(dirpath) / f
            with contextlib.suppress(OSError):
                total += fp.stat(follow_symlinks=False).st_size
    return total


def clone_git(git_url: str, dest: Path, *, resolve: bool = True) -> None:
    """SSRF-validate then shallow-clone ``git_url`` into ``dest`` with caps (§13).

    Raises SSRFError if the URL fails validation, FetchError on clone failure,
    timeout, or size-cap violation.
    """
    ssrf.validate_git_url(git_url, resolve=resolve)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", git_url, str(dest)],
            check=True,
            capture_output=True,
            timeout=config.GIT_CLONE_TIMEOUT_S,
            # Never prompt for credentials -- fail closed instead of hanging.
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise FetchError(
            f"git clone timed out after {config.GIT_CLONE_TIMEOUT_S}s"
        ) from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        stderr = exc.stderr.decode("utf-8", "replace") if exc.stderr else ""
        raise FetchError(f"git clone failed: {stderr.strip()[:200]}") from exc

    size = _dir_size_bytes(dest)
    if size > config.GIT_CLONE_MAX_BYTES:
        shutil.rmtree(dest, ignore_errors=True)
        cap = config.GIT_CLONE_MAX_BYTES
        raise FetchError(f"cloned repo exceeds size cap ({size} > {cap} bytes)")
