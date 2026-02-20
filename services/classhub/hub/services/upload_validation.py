"""Lightweight file-content checks for student uploads."""

from __future__ import annotations

import zipfile


_MAGIC_BY_EXTENSION: dict[str, tuple[bytes, ...]] = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".pdf": (b"%PDF-",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".sb3": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}


def _file_obj(upload):
    return getattr(upload, "file", upload)


def _read_head(upload, size: int = 16) -> bytes:
    fh = _file_obj(upload)
    start = fh.tell()
    try:
        fh.seek(0)
        return fh.read(size) or b""
    finally:
        fh.seek(start)


def _is_zip(upload) -> bool:
    fh = _file_obj(upload)
    start = fh.tell()
    try:
        fh.seek(0)
        return zipfile.is_zipfile(fh)
    finally:
        fh.seek(start)


def _sb3_has_project_json(upload) -> bool:
    fh = _file_obj(upload)
    start = fh.tell()
    try:
        fh.seek(0)
        with zipfile.ZipFile(fh, "r") as archive:
            names = set(archive.namelist())
            return "project.json" in names
    except (zipfile.BadZipFile, OSError):
        return False
    finally:
        fh.seek(start)


def validate_upload_content(upload, ext: str) -> str:
    """Return a user-facing error when file bytes obviously mismatch extension."""

    normalized_ext = (ext or "").strip().lower()
    signatures = _MAGIC_BY_EXTENSION.get(normalized_ext)
    if signatures:
        head = _read_head(upload)
        if not any(head.startswith(sig) for sig in signatures):
            return f"File content does not match {normalized_ext}."

    if normalized_ext == ".sb3":
        if not _is_zip(upload):
            return "Scratch project uploads must be valid .sb3 archives."
        if not _sb3_has_project_json(upload):
            return "Scratch project upload is missing project.json."

    return ""
