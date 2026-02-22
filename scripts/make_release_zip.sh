#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
STAMP="$(date +%Y%m%d_%H%M%S)"
GIT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "nogit")"

DEFAULT_OUT="${OUT_DIR}/classhub_release_${STAMP}_${GIT_SHA}.zip"
OUT_PATH="${1:-${DEFAULT_OUT}}"

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required (install zip package)." >&2
  exit 1
fi

mkdir -p "$(dirname "${OUT_PATH}")"
OUT_ABS="$(cd "$(dirname "${OUT_PATH}")" && pwd)/$(basename "${OUT_PATH}")"
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
