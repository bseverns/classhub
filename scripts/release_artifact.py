#!/usr/bin/env python3
"""Build and verify ClassHub release artifacts from an exported Git tree."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

MANIFEST_NAME = "RELEASE-MANIFEST.json"
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

BLOCKED_PARTS = {
    ".git",
    ".venv",
    ".venv_docs",
    "__pycache__",
    "__MACOSX",
    "media",
    "staticfiles",
    "data",
    ".deploy",
    "site",
    "dist",
}
BLOCKED_EXACT = {"compose/.env", "compose/.env.local"}
BLOCKED_SUFFIXES = (".pyc", ".pyo", ".DS_Store")


class ArtifactError(RuntimeError):
    """A release artifact violated its integrity contract."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_forbidden(path: str) -> bool:
    posix = PurePosixPath(path)
    if posix.is_absolute() or ".." in posix.parts or "\\" in path:
        return True
    if any(part in BLOCKED_PARTS for part in posix.parts):
        return True
    normalized = str(posix).lstrip("./")
    if normalized in BLOCKED_EXACT:
        return True
    if normalized.startswith("compose/.env.") and normalized not in {
        "compose/.env.example",
        "compose/.env.example.local",
        "compose/.env.example.domain",
    }:
        return True
    return normalized.endswith(BLOCKED_SUFFIXES)


def _payload_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ArtifactError(f"release payload must not contain symlinks: {path.relative_to(root)}")
        if path.is_file() and path.relative_to(root).as_posix() != MANIFEST_NAME:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _file_inventory(root: Path) -> list[dict[str, object]]:
    inventory: list[dict[str, object]] = []
    for path in _payload_files(root):
        relative = path.relative_to(root).as_posix()
        if _is_forbidden(relative):
            raise ArtifactError(f"forbidden release payload path: {relative}")
        mode = stat.S_IMODE(path.stat().st_mode)
        inventory.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
                "mode": f"{mode:04o}",
            }
        )
    return inventory


def _migration_heads(root: Path) -> dict[str, list[str]]:
    migrations: dict[str, set[str]] = {}
    referenced: dict[str, set[str]] = {}
    for path in sorted(root.glob("services/*/*/migrations/[0-9]*.py")):
        app_label = path.parent.parent.name
        migrations.setdefault(app_label, set()).add(path.stem)
        referenced.setdefault(app_label, set())
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            raise ArtifactError(f"cannot parse migration dependencies in {path}: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "dependencies" for target in node.targets):
                continue
            dependency_nodes = (
                node.value.elts
                if isinstance(node.value, (ast.List, ast.Tuple))
                else [node.value]
            )
            for dependency_node in dependency_nodes:
                try:
                    dependency = ast.literal_eval(dependency_node)
                except (ValueError, TypeError):
                    # Django helpers such as swappable_dependency() are
                    # cross-app edges and do not affect this app's leaf set.
                    continue
                if (
                    isinstance(dependency, (list, tuple))
                    and len(dependency) == 2
                    and dependency[0] == app_label
                    and isinstance(dependency[1], str)
                ):
                    referenced[app_label].add(dependency[1])
    return {
        app: sorted(names - referenced.get(app, set()))
        for app, names in sorted(migrations.items())
    }


def _env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _requirement_version(path: Path, package: str) -> str:
    prefix = f"{package}=="
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.lower().startswith(prefix.lower()):
            return line.split("==", 1)[1]
    raise ArtifactError(f"{package} exact pin not found in {path}")


def _python_image(path: Path) -> str:
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^FROM\s+python:([^\s]+)", raw.strip())
        if match:
            return match.group(1)
    raise ArtifactError(f"Python base image not found in {path}")


def _runtime_versions(root: Path) -> dict[str, object]:
    domain_env = _env_values(root / "compose/.env.example.domain")
    image_keys = (
        "CADDY_IMAGE",
        "POSTGRES_IMAGE",
        "REDIS_IMAGE",
        "OLLAMA_IMAGE",
        "MINIO_IMAGE",
    )
    return {
        "python_images": {
            "classhub": _python_image(root / "services/classhub/Dockerfile"),
            "homework_helper": _python_image(root / "services/homework_helper/Dockerfile"),
        },
        "django": {
            "classhub": _requirement_version(root / "services/classhub/requirements.txt", "Django"),
            "homework_helper": _requirement_version(
                root / "services/homework_helper/requirements.txt", "Django"
            ),
        },
        "infrastructure_images": {key: domain_env[key] for key in image_keys if key in domain_env},
    }


def _load_policy(root: Path) -> dict[str, object]:
    path = root / "release/policy.json"
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"invalid release policy {path}: {exc}") from exc
    origins = policy.get("supported_upgrade_origins")
    if not isinstance(origins, list) or not origins or not all(isinstance(row, str) and row for row in origins):
        raise ArtifactError("release policy must define non-empty supported_upgrade_origins")
    return policy


def build_artifact(
    *,
    root: Path,
    output: Path,
    version: str,
    commit: str,
    source_ref: str,
    source_tag: str | None,
    tag_object: str | None,
    build_timestamp: str,
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if not SEMVER_RE.fullmatch(version):
        raise ArtifactError(f"VERSION is not valid semantic versioning: {version}")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ArtifactError("release commit must be a full 40-character Git SHA")
    try:
        parsed_timestamp = datetime.fromisoformat(build_timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ArtifactError(f"invalid build timestamp: {build_timestamp}") from exc
    if parsed_timestamp.tzinfo is None:
        raise ArtifactError("build timestamp must include UTC timezone")
    timestamp_utc = parsed_timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    policy = _load_policy(root)
    inventory = _file_inventory(root)
    payload_sha256 = _sha256_bytes(_canonical_json(inventory))
    manifest: dict[str, object] = {
        "schema_version": 1,
        "product": "ClassHub",
        "version": version,
        "source": {
            "commit": commit,
            "ref": source_ref,
            "tag": source_tag,
            "annotated_tag_object": tag_object,
        },
        "build": {
            "timestamp_utc": timestamp_utc,
            "tool": "scripts/make_release_zip.sh",
        },
        "supported_upgrade_origins": policy["supported_upgrade_origins"],
        "runtime_versions": _runtime_versions(root),
        "migration_heads": _migration_heads(root),
        "payload": {
            "sha256": payload_sha256,
            "file_count": len(inventory),
            "files": inventory,
        },
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    (root / MANIFEST_NAME).write_bytes(manifest_bytes)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            info = ZipInfo.from_file(path, arcname=relative)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)

    archive_sha256 = _sha256_file(output)
    detached = {
        **manifest,
        "artifact": {
            "filename": output.name,
            "sha256": archive_sha256,
            "size_bytes": output.stat().st_size,
            "embedded_manifest_sha256": _sha256_bytes(manifest_bytes),
        },
    }
    detached_path = Path(f"{output}.manifest.json")
    detached_path.write_text(json.dumps(detached, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum_path = Path(f"{output}.sha256")
    checksum_path.write_text(f"{archive_sha256}  {output.name}\n", encoding="utf-8")
    return detached


def verify_artifact(zip_path: Path) -> dict[str, object]:
    zip_path = zip_path.resolve()
    with ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != len(set(names)):
            raise ArtifactError("release artifact contains duplicate paths")
        if MANIFEST_NAME not in names:
            raise ArtifactError(f"release artifact is missing {MANIFEST_NAME}")
        forbidden = sorted(name for name in names if _is_forbidden(name))
        if forbidden:
            raise ArtifactError(f"forbidden paths found: {', '.join(forbidden)}")
        symlinks = sorted(
            name
            for name in names
            if stat.S_ISLNK((archive.getinfo(name).external_attr >> 16) & 0xFFFF)
        )
        if symlinks:
            raise ArtifactError(f"release artifact contains symlinks: {', '.join(symlinks)}")
        manifest_bytes = archive.read(MANIFEST_NAME)
        try:
            manifest = json.loads(manifest_bytes)
        except (KeyError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid embedded release manifest: {exc}") from exc
        if manifest.get("schema_version") != 1:
            raise ArtifactError("unsupported release manifest schema")
        version = manifest.get("version")
        if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
            raise ArtifactError("release manifest has invalid semantic version")
        source = manifest.get("source")
        if not isinstance(source, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
            raise ArtifactError("release manifest has invalid source commit")
        source_tag = source.get("tag")
        tag_object = source.get("annotated_tag_object")
        if source_tag is None:
            if tag_object is not None:
                raise ArtifactError("untagged release manifest includes a tag object")
        elif not isinstance(source_tag, str) or not re.fullmatch(r"[0-9a-f]{40}", str(tag_object or "")):
            raise ArtifactError("tagged release manifest is missing an annotated tag object")
        origins = manifest.get("supported_upgrade_origins")
        if not isinstance(origins, list) or not origins or not all(
            isinstance(row, str) and row for row in origins
        ):
            raise ArtifactError("release manifest has invalid supported upgrade origins")
        if not isinstance(manifest.get("runtime_versions"), dict):
            raise ArtifactError("release manifest is missing runtime versions")
        if not isinstance(manifest.get("migration_heads"), dict):
            raise ArtifactError("release manifest is missing migration heads")
        payload = manifest.get("payload")
        inventory = payload.get("files") if isinstance(payload, dict) else None
        if not isinstance(inventory, list):
            raise ArtifactError("release manifest is missing payload inventory")
        inventory_paths = [row.get("path") for row in inventory if isinstance(row, dict)]
        actual_payload_paths = sorted(name for name in names if name != MANIFEST_NAME)
        if sorted(inventory_paths) != actual_payload_paths:
            raise ArtifactError("release payload inventory does not match archive paths")
        for row in inventory:
            if not isinstance(row, dict):
                raise ArtifactError("release payload inventory row is invalid")
            path = str(row.get("path", ""))
            content = archive.read(path)
            if len(content) != row.get("size_bytes"):
                raise ArtifactError(f"release payload size mismatch: {path}")
            if _sha256_bytes(content) != row.get("sha256"):
                raise ArtifactError(f"release payload checksum mismatch: {path}")
            archive_mode = (archive.getinfo(path).external_attr >> 16) & 0o7777
            if f"{archive_mode:04o}" != row.get("mode"):
                raise ArtifactError(f"release payload mode mismatch: {path}")
        if payload.get("file_count") != len(inventory):
            raise ArtifactError("release payload file count mismatch")
        if payload.get("sha256") != _sha256_bytes(_canonical_json(inventory)):
            raise ArtifactError("release payload inventory checksum mismatch")

    archive_sha256 = _sha256_file(zip_path)
    checksum_path = Path(f"{zip_path}.sha256")
    if not checksum_path.is_file():
        raise ArtifactError("archive checksum sidecar is missing")
    expected_line = f"{archive_sha256}  {zip_path.name}"
    if checksum_path.read_text(encoding="utf-8").strip() != expected_line:
        raise ArtifactError("archive checksum sidecar mismatch")
    detached_path = Path(f"{zip_path}.manifest.json")
    if not detached_path.is_file():
        raise ArtifactError("detached release manifest is missing")
    try:
        detached = json.loads(detached_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"invalid detached release manifest: {exc}") from exc
    artifact = detached.get("artifact")
    if not isinstance(artifact, dict) or artifact.get("sha256") != archive_sha256:
        raise ArtifactError("detached release manifest archive checksum mismatch")
    if artifact.get("filename") != zip_path.name:
        raise ArtifactError("detached release manifest filename mismatch")
    if artifact.get("size_bytes") != zip_path.stat().st_size:
        raise ArtifactError("detached release manifest size mismatch")
    if artifact.get("embedded_manifest_sha256") != _sha256_bytes(manifest_bytes):
        raise ArtifactError("detached embedded-manifest checksum mismatch")
    detached_without_artifact = {key: value for key, value in detached.items() if key != "artifact"}
    if detached_without_artifact != manifest:
        raise ArtifactError("detached release manifest metadata differs from embedded manifest")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build a release ZIP and detached integrity files")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--version", required=True)
    build.add_argument("--commit", required=True)
    build.add_argument("--source-ref", required=True)
    build.add_argument("--source-tag")
    build.add_argument("--tag-object")
    build.add_argument("--build-timestamp", required=True)
    verify = subparsers.add_parser("verify", help="Verify an existing release ZIP")
    verify.add_argument("zip_path", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build_artifact(
                root=args.root,
                output=args.output,
                version=args.version,
                commit=args.commit,
                source_ref=args.source_ref,
                source_tag=args.source_tag,
                tag_object=args.tag_object,
                build_timestamp=args.build_timestamp,
            )
            verify_artifact(args.output)
            print(f"Release artifact built and verified: {args.output}")
        else:
            manifest = verify_artifact(args.zip_path)
            print(
                "Release artifact verified: "
                f"version={manifest['version']} commit={manifest['source']['commit']}"
            )
    except ArtifactError as exc:
        print(f"Release artifact check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
