#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
STAMP="$(date +%Y%m%d_%H%M%S)"
GIT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "nogit")"

DEFAULT_OUT="${OUT_DIR}/classhub_release_${STAMP}_${GIT_SHA}.zip"

usage() {
  cat <<'EOF'
Usage: bash scripts/make_release_zip.sh [output.zip]

Creates a zip from tracked git files only and runs release artifact lint checks.
EOF
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
esac

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

OUT_PATH="${1:-${DEFAULT_OUT}}"

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required (install zip package)." >&2
  exit 1
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
rm -f "${OUT_ABS}"

if ! git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "make_release_zip.sh must run from a git working tree." >&2
  exit 1
fi

cd "${ROOT_DIR}"
file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git -C "${ROOT_DIR}" ls-files > "${file_list}"
zip -q -@ "${OUT_ABS}" < "${file_list}"

python3 "${ROOT_DIR}/scripts/lint_release_artifact.py" "${OUT_ABS}"

echo "Release zip created: ${OUT_ABS}"
