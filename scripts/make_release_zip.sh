#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
SOURCE_REF="HEAD"
ALLOW_UNTAGGED=0
OUT_PATH=""

usage() {
  cat <<'EOF'
Usage: bash scripts/make_release_zip.sh [--ref REF] [--allow-untagged] [output.zip]

Creates an immutable release zip from an exact Git object.

Publishing requires an annotated tag matching VERSION. --allow-untagged is for
CI verification only and must not be used for a published release.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)
      [[ $# -ge 2 ]] || { echo "--ref requires a value" >&2; exit 1; }
      SOURCE_REF="$2"
      shift 2
      ;;
    --allow-untagged)
      ALLOW_UNTAGGED=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "${OUT_PATH}" ]]; then
        usage >&2
        exit 1
      fi
      OUT_PATH="$1"
      shift
      ;;
  esac
done

if ! git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "make_release_zip.sh must run from a git working tree." >&2
  exit 1
fi

if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain --untracked-files=normal)" ]]; then
  echo "release builds require a clean working tree" >&2
  exit 1
fi

COMMIT="$(git -C "${ROOT_DIR}" rev-parse --verify "${SOURCE_REF}^{commit}")"
HEAD_COMMIT="$(git -C "${ROOT_DIR}" rev-parse --verify "HEAD^{commit}")"
SHORT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short=12 "${COMMIT}")"
VERSION="$(git -C "${ROOT_DIR}" show "${COMMIT}:VERSION" | tr -d '[:space:]')"
if [[ -z "${VERSION}" ]]; then
  echo "VERSION is empty at ${COMMIT}" >&2
  exit 1
fi

SOURCE_TAG=""
TAG_OBJECT=""
for candidate in "${VERSION}" "v${VERSION}"; do
  if git -C "${ROOT_DIR}" show-ref --verify --quiet "refs/tags/${candidate}"; then
    if [[ "$(git -C "${ROOT_DIR}" cat-file -t "refs/tags/${candidate}")" == "tag" ]]; then
      tagged_commit="$(git -C "${ROOT_DIR}" rev-parse "refs/tags/${candidate}^{commit}")"
      if [[ "${tagged_commit}" == "${COMMIT}" ]]; then
        SOURCE_TAG="${candidate}"
        TAG_OBJECT="$(git -C "${ROOT_DIR}" rev-parse "refs/tags/${candidate}^{tag}")"
        break
      fi
    fi
  fi
done

if [[ -z "${SOURCE_TAG}" && "${ALLOW_UNTAGGED}" != "1" ]]; then
  echo "publishing requires an annotated ${VERSION} (or v${VERSION}) tag at ${COMMIT}" >&2
  echo "use --allow-untagged only for CI verification" >&2
  exit 1
fi
if [[ "${ALLOW_UNTAGGED}" != "1" && "${HEAD_COMMIT}" != "${COMMIT}" ]]; then
  echo "publishing requires checking out the tagged release commit ${COMMIT}" >&2
  exit 1
fi

if [[ -z "${OUT_PATH}" ]]; then
  OUT_PATH="${OUT_DIR}/classhub_${VERSION}_${SHORT_SHA}.zip"
fi
OUT_PARENT="${OUT_PATH%/*}"
if [[ "${OUT_PARENT}" == "${OUT_PATH}" ]]; then
  OUT_PARENT="."
fi
OUT_BASE="$(basename "${OUT_PATH}")"
if [[ -z "${OUT_BASE}" || "${OUT_BASE}" == "." || "${OUT_BASE}" == ".." ]]; then
  echo "invalid output path: ${OUT_PATH}" >&2
  exit 1
fi
mkdir -p "${OUT_PARENT}"
OUT_ABS="$(cd "${OUT_PARENT}" && pwd)/${OUT_BASE}"

STAGE_DIR="$(mktemp -d)"
SOURCE_TAR="$(mktemp)"
cleanup() {
  rm -rf "${STAGE_DIR}"
  rm -f "${SOURCE_TAR}"
}
trap cleanup EXIT

git -C "${ROOT_DIR}" -c tar.umask=0022 archive \
  --format=tar \
  --output="${SOURCE_TAR}" \
  "${COMMIT}"
tar -xf "${SOURCE_TAR}" -C "${STAGE_DIR}"
BUILD_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

build_args=(
  build
  --root "${STAGE_DIR}"
  --output "${OUT_ABS}"
  --version "${VERSION}"
  --commit "${COMMIT}"
  --source-ref "${SOURCE_REF}"
  --build-timestamp "${BUILD_TIMESTAMP}"
)
if [[ -n "${SOURCE_TAG}" ]]; then
  build_args+=(--source-tag "${SOURCE_TAG}" --tag-object "${TAG_OBJECT}")
fi
python3 "${ROOT_DIR}/scripts/release_artifact.py" "${build_args[@]}"

python3 "${ROOT_DIR}/scripts/lint_release_artifact.py" "${OUT_ABS}"

echo "Release zip: ${OUT_ABS}"
echo "Detached manifest: ${OUT_ABS}.manifest.json"
echo "SHA-256 sidecar: ${OUT_ABS}.sha256"
