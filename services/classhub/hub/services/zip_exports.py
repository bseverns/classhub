"""Shared helpers for temporary ZIP export creation."""

from contextlib import contextmanager
import tempfile
import zipfile


@contextmanager
def temporary_zip_archive():
    """Yield a writable temp file and open ZipFile bound to it."""
    tmp = tempfile.TemporaryFile(mode="w+b")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        yield tmp, archive


def reserve_archive_path(primary: str, used_paths: set[str], *, fallback: str = "") -> str:
    """Reserve a path in the ZIP, using fallback when primary is already used."""
    chosen = primary
    if chosen in used_paths and fallback:
        chosen = fallback
    used_paths.add(chosen)
    return chosen


def write_submission_file_to_archive(
    archive,
    *,
    submission,
    arcname: str,
    allow_file_fallback: bool = False,
) -> bool:
    """Write a submission file into a ZIP archive with optional file-handle fallback."""
    try:
        source_path = submission.file.path
        archive.write(source_path, arcname=arcname)
        return True
    except Exception:
        if not allow_file_fallback:
            return False
    try:
        with submission.file.open("rb") as fh:
            archive.writestr(arcname, fh.read())
        return True
    except Exception:
        return False
