#!/usr/bin/env bash
set -euo pipefail

COURSE_SLUG="${1:-piper_scratch_12_session}"
STRICT_MODE="${2:-}"

LESSONS_DIR="services/classhub/content/courses/${COURSE_SLUG}/lessons"

echo "[preflight] Validating course manifest + lesson files for ${COURSE_SLUG}"
python3 scripts/validate_coursepack.py --course-slug "${COURSE_SLUG}"

echo "[preflight] Checking lesson video/copy sync for ${COURSE_SLUG}"
if [[ "${STRICT_MODE}" == "--strict-global" ]]; then
  python3 scripts/validate_lesson_video_order.py --lessons-dir "${LESSONS_DIR}" --strict-global
else
  python3 scripts/validate_lesson_video_order.py --lessons-dir "${LESSONS_DIR}"
fi

echo "[preflight] OK"
