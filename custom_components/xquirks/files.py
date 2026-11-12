"""File access in the custom quirks folder (blocking I/O: run in the executor)."""

from __future__ import annotations

import contextlib
import errno
import os
import stat
import tempfile
from pathlib import Path

from .const import MAX_DOWNLOAD
from .content import effective_revision, generated, sha256

# sha_on_disk for a file that exists but cannot be read (permissions, a directory, a symlink loop).
UNREADABLE = "unreadable"
# Temporary files: a leading dot and no .py suffix, so ZHA's loader skips them.
TMP_PREFIX = ".xquirks-"
TMP_SUFFIX = ".tmp"
# os.link is not available on every file system (some network shares): write in place instead.
NO_LINK = {errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV, errno.ENOSYS, errno.EMLINK}


def sha_on_disk(path: str) -> str | None:
    """sha256 of a file, None when it does not exist, UNREADABLE when it cannot be read or is a
    symlink (a link is never this integration's: neither it nor what it points to is written)."""
    if os.path.islink(path):
        return UNREADABLE
    try:
        return sha256(Path(path).read_bytes())
    except FileNotFoundError:
        return None
    except OSError:
        return UNREADABLE


def present_state(path: str) -> tuple[str | None, str | None]:
    """A file in the folder: (sha256 as sha_on_disk gives it, its revision when it is a file of this collection,
    else None). A symlink is UNREADABLE, with the revision of what it points to (ZHA imports that)."""
    if os.path.islink(path):
        content = _link_target(path)
        return UNREADABLE, effective_revision(content) if content is not None and generated(content) else None
    try:
        content = Path(path).read_bytes()
    except FileNotFoundError:
        return None, None
    except OSError:
        return UNREADABLE, None
    return sha256(content), effective_revision(content) if generated(content) else None


def _link_target(path: str) -> bytes | None:
    """The content a symlink points to when that is a regular file of at most MAX_DOWNLOAD bytes, else
    None. Opened without blocking and checked before reading: a FIFO or a device is never read."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        chunks, size = [], 0
        while size <= MAX_DOWNLOAD and (chunk := os.read(fd, MAX_DOWNLOAD + 1 - size)):
            chunks.append(chunk)
            size += len(chunk)
    except OSError:
        return None
    finally:
        os.close(fd)
    return b"".join(chunks) if size <= MAX_DOWNLOAD else None


def read_bounded(path: str, limit: int) -> bytes | None:
    """The content of a file when it can be read and is at most limit bytes, else None."""
    try:
        with open(path, "rb") as handle:
            content = handle.read(limit + 1)
    except OSError:
        return None
    return content if len(content) <= limit else None


def read_if(path: str, expected: str) -> bytes | None:
    """The content of a file while it has the sha256 `expected`, else None."""
    try:
        content = Path(path).read_bytes()
    except OSError:
        return None
    return content if sha256(content) == expected else None


def names_in(folder: str) -> set[str]:
    """Names of the files (and symlinks, dangling ones too) in folder; OSError when it cannot be read."""
    try:
        entries = list(os.scandir(folder))
    except FileNotFoundError:
        return set()
    names = set()
    for entry in entries:
        try:
            if entry.is_symlink() or entry.is_file():
                names.add(entry.name)
        except OSError:
            names.add(entry.name)
    return names


def _fsync_folder(folder: str) -> None:
    with contextlib.suppress(OSError):
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _write_temp(folder: str, content: bytes, mode: int) -> str:
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=TMP_PREFIX, suffix=TMP_SUFFIX)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return tmp


def _write_exclusive(path: str, content: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        # Created exclusively above, so the half-written file is ours to remove.
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise


def write_new(path: str, content: bytes) -> None:
    """Write a file that must not exist yet (FileExistsError otherwise); a failure leaves nothing behind."""
    folder = os.path.dirname(path)
    tmp = _write_temp(folder, content, 0o644)
    try:
        try:
            # Atomic and exclusive: the full content appears under the name at once or not at all.
            os.link(tmp, path)
        except FileExistsError:
            raise
        except OSError as err:
            if err.errno not in NO_LINK:
                raise
            _write_exclusive(path, content)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
    _fsync_folder(folder)


def replace(path: str, content: bytes, expected: str) -> bool:
    """Replace a file only while its content still has the sha256 `expected` and it is no symlink; atomic."""
    if sha_on_disk(path) != expected:
        return False
    folder = os.path.dirname(path)
    tmp = _write_temp(folder, content, os.stat(path).st_mode & 0o777)
    try:
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
    _fsync_folder(folder)
    return True


def delete(path: str, expected: str) -> bool:
    """Delete a file only while its content still has the sha256 `expected` and it is no symlink."""
    if sha_on_disk(path) != expected:
        return False
    os.unlink(path)
    _fsync_folder(os.path.dirname(path))
    # The bytecode Python cached for it is of no use any more.
    stem = os.path.splitext(os.path.basename(path))[0]
    with contextlib.suppress(OSError):
        for entry in os.scandir(os.path.join(os.path.dirname(path), "__pycache__")):
            if entry.name.startswith(f"{stem}.") and entry.name.endswith(".pyc") and entry.is_file(follow_symlinks=False):
                with contextlib.suppress(OSError):
                    os.unlink(entry.path)
    return True


def remove_stale_temp(folder: str) -> None:
    """Temporary files this integration left behind (a crash between writing and renaming)."""
    with contextlib.suppress(OSError):
        for entry in os.scandir(folder):
            if entry.name.startswith(TMP_PREFIX) and entry.name.endswith(TMP_SUFFIX) and entry.is_file(follow_symlinks=False):
                with contextlib.suppress(OSError):
                    os.unlink(entry.path)
