from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import url2pathname, urlopen

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.utils._os import safe_join
import yaml


COURSES_ROOT = Path(__file__).resolve().parents[2] / "content" / "courses"
REGISTRY_SCHEMA_VERSION = "2026-06-08"
DEFAULT_RELEASE_CHANNEL = "stable"
VALID_UI_LEVELS = {"elementary", "secondary", "advanced"}
VALID_PROGRAM_PROFILES = {"elementary", "secondary", "advanced"}
COURSE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
REMOTE_FETCH_CHUNK_BYTES = 1024 * 1024
DEFAULT_REMOTE_FETCH_TIMEOUT_SECONDS = 10
DEFAULT_REMOTE_INDEX_MAX_BYTES = 1024 * 1024
DEFAULT_REMOTE_CHECKSUM_MAX_BYTES = 64 * 1024
DEFAULT_REMOTE_ARTIFACT_MAX_BYTES = 100 * 1024 * 1024


class CoursepackRegistryError(Exception):
    """Raised when registry data or artifact retrieval is invalid."""


@dataclass(frozen=True)
class RegistrySource:
    location: str
    base_path: Path | None = None
    base_url: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_registry_version() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_source_url_for_slug(slug: str) -> str:
    return f"repo://services/classhub/content/courses/{slug}"


def _normalized_registry_host(raw: str) -> str:
    return str(raw or "").strip().lower().rstrip(".")


def _allowed_registry_remote_hosts() -> set[str]:
    raw_value = getattr(settings, "CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS", ())
    if isinstance(raw_value, str):
        values = raw_value.split(",")
    else:
        values = raw_value or ()
    return {_normalized_registry_host(value) for value in values if _normalized_registry_host(value)}


def _positive_int_setting(name: str, default: int) -> int:
    raw_value = getattr(settings, name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise CoursepackRegistryError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise CoursepackRegistryError(f"{name} must be a positive integer.")
    return value


def _remote_fetch_timeout_seconds() -> int:
    return _positive_int_setting(
        "CLASSHUB_COURSEPACK_REGISTRY_FETCH_TIMEOUT_SECONDS",
        DEFAULT_REMOTE_FETCH_TIMEOUT_SECONDS,
    )


def _remote_index_max_bytes() -> int:
    return _positive_int_setting(
        "CLASSHUB_COURSEPACK_REGISTRY_INDEX_MAX_BYTES",
        DEFAULT_REMOTE_INDEX_MAX_BYTES,
    )


def _remote_checksum_max_bytes() -> int:
    return _positive_int_setting(
        "CLASSHUB_COURSEPACK_REGISTRY_CHECKSUM_MAX_BYTES",
        DEFAULT_REMOTE_CHECKSUM_MAX_BYTES,
    )


def _remote_artifact_max_bytes() -> int:
    return _positive_int_setting(
        "CLASSHUB_COURSEPACK_REGISTRY_ARTIFACT_MAX_BYTES",
        DEFAULT_REMOTE_ARTIFACT_MAX_BYTES,
    )


def _registry_remote_url(
    raw_url: str,
    *,
    label: str,
    allowed_hosts: set[str] | None = None,
    expected_origin: str = "",
) -> str:
    parsed = urlparse(str(raw_url or "").strip())
    if parsed.scheme != "https":
        raise CoursepackRegistryError(f"{label} must use https.")
    if parsed.username or parsed.password:
        raise CoursepackRegistryError(f"{label} cannot include credentials.")
    if parsed.query or parsed.fragment:
        raise CoursepackRegistryError(f"{label} cannot include query strings or fragments.")

    host = _normalized_registry_host(parsed.hostname or "")
    if not host:
        raise CoursepackRegistryError(f"{label} host is required.")

    allowed = allowed_hosts if allowed_hosts is not None else _allowed_registry_remote_hosts()
    if not allowed:
        raise CoursepackRegistryError(
            "Remote registry fetch is disabled until CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS is configured."
        )
    if host not in allowed:
        raise CoursepackRegistryError(
            f"{label} host '{host}' is not in CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS."
        )
    if parsed.port not in {None, 443}:
        raise CoursepackRegistryError(f"{label} must use the default https port.")

    if expected_origin:
        expected = urlparse(expected_origin)
        expected_host = _normalized_registry_host(expected.hostname or "")
        if expected.scheme != "https" or expected_host != host:
            raise CoursepackRegistryError(f"{label} must stay on the same https origin as the registry index.")
        if expected.port not in {None, 443}:
            raise CoursepackRegistryError("Registry index origin must use the default https port.")

    return urlunparse(("https", host, parsed.path or "/", "", "", ""))


def _response_content_length(handle: Any, *, label: str) -> int | None:
    value: Any = None
    headers = getattr(handle, "headers", None)
    if headers is not None:
        try:
            value = headers.get("Content-Length")
        except AttributeError:
            value = None
    if value is None:
        getheader = getattr(handle, "getheader", None)
        if callable(getheader):
            value = getheader("Content-Length")
    if value in {None, ""}:
        return None
    try:
        length = int(value)
    except (TypeError, ValueError) as exc:
        raise CoursepackRegistryError(f"{label} response Content-Length is invalid.") from exc
    if length < 0:
        raise CoursepackRegistryError(f"{label} response Content-Length is invalid.")
    return length


def _enforce_response_size_header(handle: Any, *, label: str, max_bytes: int) -> None:
    content_length = _response_content_length(handle, label=label)
    if content_length is not None and content_length > max_bytes:
        raise CoursepackRegistryError(
            f"{label} response is too large: {content_length} bytes exceeds limit {max_bytes}."
        )


def _read_bounded_response(handle: Any, *, label: str, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        block = handle.read(REMOTE_FETCH_CHUNK_BYTES)
        if not block:
            break
        if not isinstance(block, bytes):
            raise CoursepackRegistryError(f"{label} response must be bytes.")
        total += len(block)
        if total > max_bytes:
            raise CoursepackRegistryError(
                f"{label} response exceeded limit {max_bytes} bytes while reading."
            )
        chunks.append(block)
    return b"".join(chunks)


def _read_remote_bytes(url: str, *, label: str, max_bytes: int) -> bytes:
    with urlopen(url, timeout=_remote_fetch_timeout_seconds()) as handle:
        _enforce_response_size_header(handle, label=label, max_bytes=max_bytes)
        return _read_bounded_response(handle, label=label, max_bytes=max_bytes)


def _registry_file_url_to_path(raw_url: str, *, label: str) -> Path:
    parsed = urlparse(str(raw_url or "").strip())
    if parsed.scheme != "file":
        raise CoursepackRegistryError(f"{label} must use the file scheme.")
    if parsed.netloc not in {"", "localhost"}:
        raise CoursepackRegistryError(f"{label} file URLs cannot include a remote host.")
    return Path(url2pathname(parsed.path)).expanduser().resolve()


def _registry_local_path(base_path: Path, raw_path: str, *, label: str) -> Path:
    candidate = str(raw_path or "").strip().replace("\\", "/")
    if not candidate:
        raise CoursepackRegistryError(f"{label} path is required.")
    if urlparse(candidate).scheme == "file":
        raise CoursepackRegistryError(f"{label} must use a relative path inside the registry directory.")
    if candidate.startswith("/"):
        raise CoursepackRegistryError(f"{label} must use a relative path inside the registry directory.")

    resolved_base = Path(base_path).resolve()
    try:
        joined = safe_join(str(resolved_base), candidate)
    except SuspiciousFileOperation as exc:
        raise CoursepackRegistryError(f"{label} escapes the registry directory.") from exc
    resolved_path = Path(joined).resolve()
    if not resolved_path.is_relative_to(resolved_base):
        raise CoursepackRegistryError(f"{label} escapes the registry directory.")
    return resolved_path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _stream_local_file_to_path(
    source_path: Path,
    output_path: Path,
    *,
    label: str,
    max_bytes: int,
) -> tuple[int, str]:
    source_path = Path(source_path).resolve()
    output_path = Path(output_path).resolve()
    source_size = source_path.stat().st_size
    if source_size > max_bytes:
        raise CoursepackRegistryError(
            f"{label} file is too large: {source_size} bytes exceeds limit {max_bytes}."
        )
    if source_path == output_path:
        return source_size, sha256_file(source_path)

    digest = hashlib.sha256()
    total = 0
    try:
        with source_path.open("rb") as source_handle, output_path.open("wb") as output_handle:
            while True:
                block = source_handle.read(REMOTE_FETCH_CHUNK_BYTES)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise CoursepackRegistryError(
                        f"{label} file exceeded limit {max_bytes} bytes while reading."
                    )
                digest.update(block)
                output_handle.write(block)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return total, digest.hexdigest()


def _stream_remote_url_to_path(
    url: str,
    output_path: Path,
    *,
    label: str,
    max_bytes: int,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    try:
        with (
            urlopen(url, timeout=_remote_fetch_timeout_seconds()) as handle,
            Path(output_path).open("wb") as output_handle,
        ):
            _enforce_response_size_header(handle, label=label, max_bytes=max_bytes)
            while True:
                block = handle.read(REMOTE_FETCH_CHUNK_BYTES)
                if not block:
                    break
                if not isinstance(block, bytes):
                    raise CoursepackRegistryError(f"{label} response must be bytes.")
                total += len(block)
                if total > max_bytes:
                    raise CoursepackRegistryError(
                        f"{label} response exceeded limit {max_bytes} bytes while reading."
                    )
                digest.update(block)
                output_handle.write(block)
    except Exception:
        Path(output_path).unlink(missing_ok=True)
        raise
    return total, digest.hexdigest()


def write_checksum_file(path: Path, sha256: str) -> Path:
    artifact_path = Path(path).resolve()
    checksum_name = f"{artifact_path.name}.sha256"
    checksum_path = artifact_path.parent / checksum_name
    checksum_path.write_text(f"{sha256}  {artifact_path.name}\n", encoding="utf-8")
    return checksum_path


def _safe_registry_filename(raw_name: str, *, default: str = "registry-artifact.zip") -> str:
    candidate = Path(str(raw_name or "").strip()).name.strip()
    if not candidate or candidate in {".", ".."}:
        return default
    if not SAFE_FILENAME_RE.fullmatch(candidate):
        return default
    return candidate


def _resolved_output_path(raw_path: str | Path, *, fallback_name: str) -> Path:
    candidate = Path(raw_path)
    parent = candidate.parent.resolve()
    filename = _safe_registry_filename(candidate.name, default=fallback_name)
    return parent / filename


def _checksum_digest_from_payload(payload: bytes, *, label: str) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CoursepackRegistryError(f"{label} file must be UTF-8 text.") from exc
    first_token = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            first_token = stripped.split()[0].lower()
            break
    if not SHA256_RE.fullmatch(first_token):
        raise CoursepackRegistryError(f"{label} file does not contain a valid SHA-256 digest.")
    return first_token


def _verify_registry_checksum_sidecar(
    source: RegistrySource,
    checksum_url: str,
    *,
    expected_sha256: str,
) -> str:
    resolved_location = resolve_registry_artifact_location(
        source,
        checksum_url,
        label="Registry checksum",
    )
    parsed = urlparse(resolved_location)
    if parsed.scheme == "https":
        payload = _read_remote_bytes(
            resolved_location,
            label="Registry checksum",
            max_bytes=_remote_checksum_max_bytes(),
        )
    else:
        checksum_path = _registry_local_path(
            source.base_path or Path("."),
            checksum_url,
            label="Registry checksum",
        )
        if not checksum_path.exists() or not checksum_path.is_file():
            raise CoursepackRegistryError(f"Registry checksum file not found: {checksum_path}")
        checksum_size = checksum_path.stat().st_size
        max_bytes = _remote_checksum_max_bytes()
        if checksum_size > max_bytes:
            raise CoursepackRegistryError(
                f"Registry checksum file is too large: {checksum_size} bytes exceeds limit {max_bytes}."
            )
        payload = checksum_path.read_bytes()

    sidecar_sha256 = _checksum_digest_from_payload(payload, label="Registry checksum")
    if sidecar_sha256 != expected_sha256:
        raise CoursepackRegistryError(
            "Registry checksum sidecar does not match the registry index digest: "
            f"expected {expected_sha256}, got {sidecar_sha256}"
        )
    return resolved_location


def load_course_manifest(slug: str, *, courses_root: Path = COURSES_ROOT) -> dict[str, Any]:
    manifest_path = Path(courses_root) / slug / "course.yaml"
    if not manifest_path.exists():
        raise CoursepackRegistryError(f"Course manifest not found: {manifest_path}")
    try:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CoursepackRegistryError(f"Invalid YAML in {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CoursepackRegistryError(f"{manifest_path}: expected a YAML mapping/object")
    return payload


def build_registry_entry(
    *,
    slug: str,
    artifact_path: Path,
    version: str = "",
    release_channel: str = DEFAULT_RELEASE_CHANNEL,
    artifact_url: str = "",
    source_url: str = "",
    sdk_version: str = "",
    courses_root: Path = COURSES_ROOT,
) -> dict[str, Any]:
    manifest = load_course_manifest(slug, courses_root=courses_root)
    title = str(manifest.get("title") or slug).strip()
    ui_level = str(manifest.get("ui_level") or "").strip().lower()
    program_profile = str(manifest.get("program_profile") or "").strip().lower()

    if not ui_level or ui_level not in VALID_UI_LEVELS:
        raise CoursepackRegistryError(
            f"Course '{slug}' is missing a valid ui_level for registry export."
        )
    if program_profile and program_profile not in VALID_PROGRAM_PROFILES:
        raise CoursepackRegistryError(
            f"Course '{slug}' has invalid program_profile '{program_profile}' for registry export."
        )

    normalized_version = (version or default_registry_version()).strip()
    if not VERSION_RE.fullmatch(normalized_version):
        raise CoursepackRegistryError(
            f"Invalid version '{normalized_version}' (letters, numbers, dot, underscore, dash only)."
        )

    normalized_channel = str(release_channel or DEFAULT_RELEASE_CHANNEL).strip().lower()
    if not VERSION_RE.fullmatch(normalized_channel):
        raise CoursepackRegistryError(
            f"Invalid release channel '{normalized_channel}' "
            "(letters, numbers, dot, underscore, dash only)."
        )

    artifact_path = Path(artifact_path)
    if not artifact_path.exists() or not artifact_path.is_file():
        raise CoursepackRegistryError(f"Artifact not found: {artifact_path}")

    sha256 = sha256_file(artifact_path)
    checksum_path = write_checksum_file(artifact_path, sha256)
    normalized_source_url = str(source_url or default_source_url_for_slug(slug)).strip()

    return {
        "slug": slug,
        "title": title,
        "version": normalized_version,
        "release_channel": normalized_channel,
        "source_url": normalized_source_url,
        "sdk_version": str(sdk_version or "").strip(),
        "generated_at": utc_now_iso(),
        "compatibility": {
            "ui_level": ui_level,
            "program_profile": program_profile or ui_level,
        },
        "artifact": {
            "url": str(artifact_url or artifact_path.name).strip(),
            "sha256": sha256,
            "bytes": artifact_path.stat().st_size,
            "checksum_url": f"{str(artifact_url or artifact_path.name).strip()}.sha256",
            "filename": artifact_path.name,
        },
        "checksum_file": str(checksum_path),
    }


def new_registry_document(*, entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "entries": list(entries or []),
    }


def validate_registry_document(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["registry document must be a JSON object"]

    schema_version = str(payload.get("schema_version") or "").strip()
    if not schema_version:
        errors.append("registry: missing required field 'schema_version'")

    generated_at = str(payload.get("generated_at") or "").strip()
    if not generated_at:
        errors.append("registry: missing required field 'generated_at'")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append("registry: 'entries' must be a list")
        return errors

    seen_keys: set[tuple[str, str]] = set()
    for idx, entry in enumerate(entries, start=1):
        ref = f"entries[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{ref}: entry must be an object")
            continue

        slug = str(entry.get("slug") or "").strip()
        version = str(entry.get("version") or "").strip()
        title = str(entry.get("title") or "").strip()
        source_url = str(entry.get("source_url") or "").strip()
        release_channel = str(entry.get("release_channel") or "").strip()

        if not slug:
            errors.append(f"{ref}: missing required field 'slug'")
        elif not COURSE_SLUG_RE.fullmatch(slug):
            errors.append(f"{ref}: invalid slug '{slug}'")

        if not title:
            errors.append(f"{ref}: missing required field 'title'")

        if not version:
            errors.append(f"{ref}: missing required field 'version'")
        elif not VERSION_RE.fullmatch(version):
            errors.append(f"{ref}: invalid version '{version}'")

        if not release_channel:
            errors.append(f"{ref}: missing required field 'release_channel'")
        elif not VERSION_RE.fullmatch(release_channel):
            errors.append(f"{ref}: invalid release_channel '{release_channel}'")

        if not source_url:
            errors.append(f"{ref}: missing required field 'source_url'")

        if slug and version:
            key = (slug, version)
            if key in seen_keys:
                errors.append(f"{ref}: duplicate slug/version pair '{slug}@{version}'")
            else:
                seen_keys.add(key)

        compatibility = entry.get("compatibility")
        if not isinstance(compatibility, dict):
            errors.append(f"{ref}: missing required object 'compatibility'")
        else:
            ui_level = str(compatibility.get("ui_level") or "").strip().lower()
            program_profile = str(compatibility.get("program_profile") or "").strip().lower()
            if not ui_level:
                errors.append(f"{ref}: compatibility.ui_level is required")
            elif ui_level not in VALID_UI_LEVELS:
                errors.append(f"{ref}: invalid compatibility.ui_level '{ui_level}'")
            if not program_profile:
                errors.append(f"{ref}: compatibility.program_profile is required")
            elif program_profile not in VALID_PROGRAM_PROFILES:
                errors.append(
                    f"{ref}: invalid compatibility.program_profile '{program_profile}'"
                )

        artifact = entry.get("artifact")
        if not isinstance(artifact, dict):
            errors.append(f"{ref}: missing required object 'artifact'")
            continue

        artifact_url = str(artifact.get("url") or "").strip()
        artifact_sha256 = str(artifact.get("sha256") or "").strip().lower()
        artifact_bytes = artifact.get("bytes")
        checksum_url = str(artifact.get("checksum_url") or "").strip()

        if not artifact_url:
            errors.append(f"{ref}: artifact.url is required")
        if not artifact_sha256:
            errors.append(f"{ref}: artifact.sha256 is required")
        elif not SHA256_RE.fullmatch(artifact_sha256):
            errors.append(f"{ref}: artifact.sha256 must be a 64-character lowercase hex digest")
        if not isinstance(artifact_bytes, int) or artifact_bytes <= 0:
            errors.append(f"{ref}: artifact.bytes must be a positive integer")
        if not checksum_url:
            errors.append(f"{ref}: artifact.checksum_url is required")

    return errors


def read_registry_document(index_location: str) -> tuple[dict[str, Any], RegistrySource]:
    location = str(index_location or "").strip()
    if not location:
        raise CoursepackRegistryError("Registry index location is required.")

    parsed = urlparse(location)
    if parsed.scheme in {"http", "https"}:
        remote_location = _registry_remote_url(location, label="Registry index")
        raw = _read_remote_bytes(
            remote_location,
            label="Registry index",
            max_bytes=_remote_index_max_bytes(),
        ).decode("utf-8")
        source = RegistrySource(location=remote_location, base_url=remote_location)
    elif parsed.scheme == "file":
        index_path = _registry_file_url_to_path(location, label="Registry index")
        raw = index_path.read_text(encoding="utf-8")
        source = RegistrySource(location=str(index_path), base_path=index_path.parent)
    elif parsed.scheme:
        raise CoursepackRegistryError("Registry index must use https, file, or a relative local path.")
    else:
        if location.replace("\\", "/").startswith("/"):
            raise CoursepackRegistryError("Registry index absolute local paths must use file://.")
        index_path = _registry_local_path(Path.cwd(), location, label="Registry index")
        if not index_path.exists() or not index_path.is_file():
            raise CoursepackRegistryError(f"Registry index file not found: {index_path}")
        raw = index_path.read_text(encoding="utf-8")
        source = RegistrySource(location=str(index_path), base_path=index_path.parent)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CoursepackRegistryError(f"Invalid registry JSON: {exc}") from exc

    errors = validate_registry_document(payload)
    if errors:
        raise CoursepackRegistryError("Invalid registry document:\n- " + "\n- ".join(errors))
    return payload, source


def write_registry_document(index_path: Path, payload: dict[str, Any]) -> None:
    errors = validate_registry_document(payload)
    if errors:
        raise CoursepackRegistryError("Cannot write invalid registry document:\n- " + "\n- ".join(errors))
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "generated_at": utc_now_iso()}
    index_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_registry_entry(
    payload: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise CoursepackRegistryError("Registry payload must include an 'entries' list.")

    normalized_entry = {key: value for key, value in entry.items() if key != "checksum_file"}
    target_key = (
        str(normalized_entry.get("slug") or "").strip(),
        str(normalized_entry.get("version") or "").strip(),
    )
    if not all(target_key):
        raise CoursepackRegistryError("Registry entry is missing slug or version.")

    updated = False
    new_entries: list[dict[str, Any]] = []
    for row in entries:
        row_key = (str(row.get("slug") or "").strip(), str(row.get("version") or "").strip())
        if row_key == target_key:
            new_entries.append(normalized_entry)
            updated = True
        else:
            new_entries.append(row)
    if not updated:
        new_entries.append(normalized_entry)

    new_entries.sort(key=lambda row: (str(row.get("slug") or ""), str(row.get("version") or "")))
    return {
        "schema_version": str(payload.get("schema_version") or REGISTRY_SCHEMA_VERSION),
        "generated_at": utc_now_iso(),
        "entries": new_entries,
    }


def resolve_registry_artifact_location(
    source: RegistrySource,
    artifact_url: str,
    *,
    label: str = "Registry artifact",
) -> str:
    raw = str(artifact_url or "").strip()
    if not raw:
        raise CoursepackRegistryError(f"{label} URL is required.")

    parsed = urlparse(raw)
    if source.base_path is not None:
        return str(_registry_local_path(source.base_path, raw, label=label))
    if source.base_url:
        resolved = raw if parsed.scheme in {"http", "https"} else urljoin(source.base_url, raw)
        return _registry_remote_url(
            resolved,
            label=label,
            allowed_hosts={_normalized_registry_host(urlparse(source.base_url).hostname or "")},
            expected_origin=source.base_url,
        )
    return raw


def select_registry_entry(
    payload: dict[str, Any],
    *,
    slug: str,
    version: str = "",
) -> dict[str, Any]:
    entries = payload.get("entries") or []
    candidates = [entry for entry in entries if str(entry.get("slug") or "").strip() == slug]
    if not candidates:
        raise CoursepackRegistryError(f"No registry entry found for slug '{slug}'.")

    if version:
        for entry in candidates:
            if str(entry.get("version") or "").strip() == version:
                return entry
        raise CoursepackRegistryError(f"No registry entry found for '{slug}' with version '{version}'.")

    candidates.sort(
        key=lambda entry: (
            str(entry.get("generated_at") or ""),
            str(entry.get("version") or ""),
        )
    )
    return candidates[-1]


def fetch_registry_artifact(
    source: RegistrySource,
    entry: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = entry.get("artifact") or {}
    artifact_url = str(artifact.get("url") or "").strip()
    expected_sha256 = str(artifact.get("sha256") or "").strip().lower()
    expected_bytes = int(artifact.get("bytes") or 0)
    max_artifact_bytes = _remote_artifact_max_bytes()
    if expected_bytes > max_artifact_bytes:
        raise CoursepackRegistryError(
            f"Registry artifact declared size {expected_bytes} bytes exceeds limit {max_artifact_bytes}."
        )

    resolved_location = resolve_registry_artifact_location(source, artifact_url)
    parsed = urlparse(resolved_location)
    checksum_location = str((artifact.get("checksum_url") or "")).strip()
    resolved_checksum_location = (
        _verify_registry_checksum_sidecar(
            source,
            checksum_location,
            expected_sha256=expected_sha256,
        )
        if checksum_location
        else ""
    )

    if output_path is None:
        output_path = _safe_registry_filename(
            str(artifact.get("filename") or "") or Path(urlparse(artifact_url).path).name,
            default="registry-artifact.zip",
        )
    output_path = _resolved_output_path(
        output_path,
        fallback_name=_safe_registry_filename(
            Path(urlparse(artifact_url).path).name,
            default="registry-artifact.zip",
        ),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if parsed.scheme == "https":
        actual_bytes, actual_sha256 = _stream_remote_url_to_path(
            resolved_location,
            output_path,
            label="Registry artifact",
            max_bytes=expected_bytes,
        )
    else:
        local_artifact_path = _registry_local_path(
            source.base_path or Path("."),
            artifact_url,
            label="Registry artifact",
        )
        if not local_artifact_path.exists() or not local_artifact_path.is_file():
            raise CoursepackRegistryError(f"Registry artifact file not found: {local_artifact_path}")
        actual_bytes, actual_sha256 = _stream_local_file_to_path(
            local_artifact_path,
            output_path,
            label="Registry artifact",
            max_bytes=expected_bytes,
        )

    if actual_sha256 != expected_sha256:
        output_path.unlink(missing_ok=True)
        raise CoursepackRegistryError(
            f"Checksum mismatch for '{entry.get('slug')}' version '{entry.get('version')}': "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    if expected_bytes and actual_bytes != expected_bytes:
        output_path.unlink(missing_ok=True)
        raise CoursepackRegistryError(
            f"Byte-size mismatch for '{entry.get('slug')}' version '{entry.get('version')}': "
            f"expected {expected_bytes}, got {actual_bytes}"
        )

    checksum_path = write_checksum_file(output_path, actual_sha256)

    return {
        "slug": str(entry.get("slug") or "").strip(),
        "version": str(entry.get("version") or "").strip(),
        "artifact": str(output_path),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
        "source_artifact_url": artifact_url,
        "resolved_artifact_location": resolved_location,
        "checksum_file": str(checksum_path),
        "resolved_checksum_location": resolved_checksum_location,
    }


def copy_registry_artifact_and_checksum(
    *,
    artifact_path: Path,
    checksum_path: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied_artifact = output_dir / artifact_path.name
    copied_checksum = output_dir / checksum_path.name
    shutil.copy2(artifact_path, copied_artifact)
    shutil.copy2(checksum_path, copied_checksum)
    return copied_artifact, copied_checksum
