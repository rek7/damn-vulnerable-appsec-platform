"""Archive extraction zip-slip / symlink guards (§13)."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from app import fetch


def _make_zip(path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def test_zip_extracts_benign_entries(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    _make_zip(archive, {"a.txt": "hello", "sub/b.txt": "world"})
    dest = tmp_path / "out"
    dest.mkdir()
    fetch.extract_zip(archive, dest)
    assert (dest / "a.txt").read_text() == "hello"
    assert (dest / "sub" / "b.txt").read_text() == "world"


def test_zip_rejects_parent_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    _make_zip(archive, {"../escape.txt": "pwned"})
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fetch.FetchError):
        fetch.extract_zip(archive, dest)


def test_zip_rejects_absolute_path(tmp_path: Path) -> None:
    archive = tmp_path / "abs.zip"
    # Absolute paths are normally stripped by zipinfo; force one in directly.
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("/etc/cron.d/evil")
        zf.writestr(info, "data")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fetch.FetchError):
        fetch.extract_zip(archive, dest)


def test_tar_extracts_benign_entries(tmp_path: Path) -> None:
    archive = tmp_path / "ok.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        data = b"hello"
        info = tarfile.TarInfo("a.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    dest = tmp_path / "out"
    dest.mkdir()
    fetch.extract_tar(archive, dest)
    assert (dest / "a.txt").read_bytes() == b"hello"


def test_tar_rejects_parent_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        data = b"pwned"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fetch.FetchError):
        fetch.extract_tar(archive, dest)


def test_tar_skips_symlink_escaping_root(tmp_path: Path) -> None:
    archive = tmp_path / "link.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        data = b"safe"
        file_info = tarfile.TarInfo("main.tf")
        file_info.size = len(data)
        tf.addfile(file_info, io.BytesIO(data))

        info = tarfile.TarInfo("leak")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"  # absolute -> escapes root
        tf.addfile(info)
    dest = tmp_path / "out"
    dest.mkdir()
    fetch.extract_tar(archive, dest)
    assert (dest / "main.tf").read_bytes() == b"safe"
    assert not (dest / "leak").exists()


def test_extract_archive_rejects_unknown_type(tmp_path: Path) -> None:
    bogus = tmp_path / "thing.rar"
    bogus.write_bytes(b"nope")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fetch.FetchError):
        fetch.extract_archive(bogus, dest)
