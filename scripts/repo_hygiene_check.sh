#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

offenders=()

while IFS= read -r path; do
  case "${path}" in
    .venv/*|*/.venv/*|\
    .DS_Store|*/.DS_Store|\
    __pycache__/*|*/__pycache__/*|\
    .pytest_cache/*|*/.pytest_cache/*|\
    media/*|*/media/*|\
    staticfiles/*|*/staticfiles/*|\
    .env|*/.env|\
    *.sqlite3)
      offenders+=("${path}")
      ;;
  esac
done < <(git ls-files)

if ((${#offenders[@]} > 0)); then
  echo "[hygiene] FAIL: blocked tracked paths detected:"
  for row in "${offenders[@]}"; do
    echo " - ${row}"
  done
  exit 1
fi

if [[ -n "${1:-}" ]]; then
  python3 "${ROOT_DIR}/scripts/lint_release_artifact.py" "$1"
fi

echo "[hygiene] OK"

