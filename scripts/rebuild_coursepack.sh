#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COURSE_SLUG="piper_scratch_12_session"
CLASS_CODE="${CLASS_CODE:-}"
CREATE_CLASS="false"

usage() {
  echo "Usage: $0 [--course-slug <slug>] [--class-code <code>] [--create-class]" >&2
  echo "  Or set CLASS_CODE env var to avoid passing it on the command line." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --course-slug)
      COURSE_SLUG="${2:-}"
      shift 2
      ;;
    --class-code)
      CLASS_CODE="${2:-}"
      shift 2
      ;;
    --create-class)
      CREATE_CLASS="true"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$CLASS_CODE" && "$CREATE_CLASS" != "true" ]]; then
  usage
  exit 1
fi

cd "$ROOT_DIR/compose"

cmd=(python manage.py import_coursepack --course-slug "$COURSE_SLUG" --replace)
if [[ "$CREATE_CLASS" == "true" ]]; then
  cmd+=(--create-class)
else
  cmd+=(--class-code "$CLASS_CODE")
fi

docker compose exec classhub_web "${cmd[@]}"
