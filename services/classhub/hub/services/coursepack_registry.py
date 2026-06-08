from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

import yaml


COURSES_ROOT = Path(__file__).resolve().parents[2] / "content" / "courses"
REGISTRY_SCHEMA_VERSION = "2026-06-08"
DEFAULT_RELEASE_CHANNEL = "stable"
VALID_UI_LEVELS = {"elementary", "secondary", "advanced"}
VALID_PROGRAM_PROFILES = {"elementary", "secondary", "advanced"}
COURSE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def write_checksum_file(path: Path, sha256: str) -> Path:
    checksum_path = Path(f"{path}.sha256")
    checksum_path.write_text(f"{sha256}  {path.name}\n", encoding="utf-8")
    return checksum_path


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
    if parsed.scheme in {"http", "https", "file"}:
        with urlopen(location) as handle:
            raw = handle.read().decode("utf-8")
        source = RegistrySource(location=location, base_url=location)
    else:
        index_path = Path(location).expanduser().resolve()
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


def resolve_registry_artifact_location(source: RegistrySource, artifact_url: str) -> str:
    raw = str(artifact_url or "").strip()
    if not raw:
        raise CoursepackRegistryError("Artifact URL is required.")

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https", "file"}:
        return raw
    if raw.startswith("/"):
        return raw
    if source.base_path is not None:
        return str((source.base_path / raw).resolve())
    if source.base_url:
        return urljoin(source.base_url, raw)
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
    resolved_location = resolve_registry_artifact_location(source, artifact_url)
    parsed = urlparse(resolved_location)

    if parsed.scheme in {"http", "https", "file"}:
        with urlopen(resolved_location) as handle:
            payload = handle.read()
    else:
        payload = Path(resolved_location).read_bytes()

    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise CoursepackRegistryError(
            f"Checksum mismatch for '{entry.get('slug')}' version '{entry.get('version')}': "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    if expected_bytes and len(payload) != expected_bytes:
        raise CoursepackRegistryError(
            f"Byte-size mismatch for '{entry.get('slug')}' version '{entry.get('version')}': "
            f"expected {expected_bytes}, got {len(payload)}"
        )

    if output_path is None:
        output_path = Path(str(artifact.get("filename") or "") or Path(artifact_url).name)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    checksum_path = write_checksum_file(output_path, actual_sha256)

    checksum_location = str((artifact.get("checksum_url") or "")).strip()
    resolved_checksum_location = resolve_registry_artifact_location(source, checksum_location) if checksum_location else ""

    return {
        "slug": str(entry.get("slug") or "").strip(),
        "version": str(entry.get("version") or "").strip(),
        "artifact": str(output_path),
        "bytes": len(payload),
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
