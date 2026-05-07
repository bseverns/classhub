#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod|dev
BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/artifacts/stability/$(date +%F)}"
RTO_THRESHOLD_SECONDS="${RTO_THRESHOLD_SECONDS:-3600}"
RPO_THRESHOLD_SECONDS="${RPO_THRESHOLD_SECONDS:-900}"
HOST_CLASS="${HOST_CLASS:-same-host}" # same-host|replacement-host
HOST_LABEL="${HOST_LABEL:-}"
SCENARIO_LABEL="${SCENARIO_LABEL:-restore-rehearsal}"
EVIDENCE_NOTE="${EVIDENCE_NOTE:-}"

SKIP_BACKUP=0
KEEP_TEMP=0
UP_TIMEOUT_SECONDS=""
POSTGRES_BACKUP_PATH=""
UPLOADS_BACKUP_PATH=""
MINIO_BACKUP_PATH=""

usage() {
  cat <<'EOF'
Usage: bash scripts/restore_rehearsal_evidence.sh [options]

Runs backup/restore rehearsal and captures evidence artifacts in one command:
1) rehearsal log
2) backup copies + checksums
3) metrics.json (duration, RTO/RPO, thresholds)
4) summary.md

Options:
  --compose-mode <prod|dev>       Compose profile for rehearsal (default: prod)
  --backup-root <dir>             Backup root directory (default: ./backups)
  --out-dir <dir>                 Evidence output directory (default: artifacts/stability/<YYYY-MM-DD>)
  --rto-threshold-seconds <N>     Fail if duration exceeds N (default: 3600)
  --rpo-threshold-seconds <N>     Fail if backup age at completion exceeds N (default: 900)
  --host-class <same-host|replacement-host>
                                  Evidence label for where the rehearsal ran (default: same-host)
  --host-label <label>            Hostname or operator label for the rehearsal target
  --scenario-label <label>        Short scenario label recorded in evidence (default: restore-rehearsal)
  --evidence-note <text>          Optional operator note recorded in metrics and summary
  --skip-backup                   Reuse existing backup artifacts
  --postgres-backup <file>        Explicit Postgres backup path (used with --skip-backup)
  --uploads-backup <file>         Explicit uploads backup path (used with --skip-backup)
  --minio-backup <file>           Explicit MinIO backup path (used with --skip-backup)
  --keep-temp                     Keep rehearsal temporary restore directory
  --up-timeout-seconds <N>        Rehearsal Postgres health timeout override
  -h, --help                      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --backup-root)
      BACKUP_ROOT="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --rto-threshold-seconds)
      RTO_THRESHOLD_SECONDS="$2"
      shift 2
      ;;
    --rpo-threshold-seconds)
      RPO_THRESHOLD_SECONDS="$2"
      shift 2
      ;;
    --host-class)
      HOST_CLASS="$2"
      shift 2
      ;;
    --host-label)
      HOST_LABEL="$2"
      shift 2
      ;;
    --scenario-label)
      SCENARIO_LABEL="$2"
      shift 2
      ;;
    --evidence-note)
      EVIDENCE_NOTE="$2"
      shift 2
      ;;
    --skip-backup)
      SKIP_BACKUP=1
      shift
      ;;
    --postgres-backup)
      POSTGRES_BACKUP_PATH="$2"
      shift 2
      ;;
    --uploads-backup)
      UPLOADS_BACKUP_PATH="$2"
      shift 2
      ;;
    --minio-backup)
      MINIO_BACKUP_PATH="$2"
      shift 2
      ;;
    --keep-temp)
      KEEP_TEMP=1
      shift
      ;;
    --up-timeout-seconds)
      UP_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[restore-evidence] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${COMPOSE_MODE}" != "prod" && "${COMPOSE_MODE}" != "dev" ]]; then
  echo "[restore-evidence] --compose-mode must be prod or dev" >&2
  exit 1
fi
if [[ "${HOST_CLASS}" != "same-host" && "${HOST_CLASS}" != "replacement-host" ]]; then
  echo "[restore-evidence] --host-class must be same-host or replacement-host" >&2
  exit 1
fi
for n in "${RTO_THRESHOLD_SECONDS}" "${RPO_THRESHOLD_SECONDS}"; do
  if ! [[ "${n}" =~ ^[0-9]+$ ]]; then
    echo "[restore-evidence] threshold values must be non-negative integers" >&2
    exit 1
  fi
done
if [[ -z "${HOST_LABEL}" ]]; then
  HOST_LABEL="$(hostname 2>/dev/null || echo "unknown-host")"
fi
if [[ "${HOST_CLASS}" == "replacement-host" && -z "${HOST_LABEL// }" ]]; then
  echo "[restore-evidence] --host-label is required for replacement-host evidence" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}" "${OUT_DIR}/backups"
LOG_PATH="${OUT_DIR}/restore_rehearsal.log"
METRICS_PATH="${OUT_DIR}/restore_rehearsal_metrics.json"
SUMMARY_PATH="${OUT_DIR}/restore_rehearsal_summary.md"
CHECKSUMS_PATH="${OUT_DIR}/backups/checksums.sha256"

latest_file() {
  local pattern="$1"
  python3 - "${pattern}" <<'PY'
import glob
import os
import sys

matches = glob.glob(sys.argv[1])
if not matches:
    sys.exit(0)
matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
print(matches[0])
PY
}

sha256_write() {
  local out="$1"
  shift
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@" > "${out}"
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@" > "${out}"
    return 0
  fi
  echo "[restore-evidence] missing checksum tool (sha256sum/shasum)" >&2
  return 1
}

start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
start_epoch="$(date +%s)"

cmd=(bash "${ROOT_DIR}/scripts/backup_restore_rehearsal.sh" --compose-mode "${COMPOSE_MODE}" --backup-root "${BACKUP_ROOT}")
if [[ "${SKIP_BACKUP}" == "1" ]]; then
  cmd+=(--skip-backup)
fi
if [[ -n "${POSTGRES_BACKUP_PATH}" ]]; then
  cmd+=(--postgres-backup "${POSTGRES_BACKUP_PATH}")
fi
if [[ -n "${UPLOADS_BACKUP_PATH}" ]]; then
  cmd+=(--uploads-backup "${UPLOADS_BACKUP_PATH}")
fi
if [[ -n "${MINIO_BACKUP_PATH}" ]]; then
  cmd+=(--minio-backup "${MINIO_BACKUP_PATH}")
fi
if [[ "${KEEP_TEMP}" == "1" ]]; then
  cmd+=(--keep-temp)
fi
if [[ -n "${UP_TIMEOUT_SECONDS}" ]]; then
  cmd+=(--up-timeout-seconds "${UP_TIMEOUT_SECONDS}")
fi

echo "[restore-evidence] started ${start_utc}" | tee "${LOG_PATH}"
{
  echo "[restore-evidence] host-class: ${HOST_CLASS}"
  echo "[restore-evidence] host-label: ${HOST_LABEL}"
  echo "[restore-evidence] scenario-label: ${SCENARIO_LABEL}"
  if [[ -n "${EVIDENCE_NOTE}" ]]; then
    echo "[restore-evidence] evidence-note: ${EVIDENCE_NOTE}"
  fi
  echo "[restore-evidence] command: ${cmd[*]}"
  "${cmd[@]}"
} | tee -a "${LOG_PATH}"

end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
end_epoch="$(date +%s)"
duration_seconds="$((end_epoch - start_epoch))"

if [[ -z "${POSTGRES_BACKUP_PATH}" ]]; then
  POSTGRES_BACKUP_PATH="$(latest_file "${BACKUP_ROOT}/postgres/classhub_*.sql")"
fi
if [[ -z "${UPLOADS_BACKUP_PATH}" ]]; then
  UPLOADS_BACKUP_PATH="$(latest_file "${BACKUP_ROOT}/uploads/classhub_uploads_*.tgz")"
fi
if [[ -z "${MINIO_BACKUP_PATH}" ]]; then
  MINIO_BACKUP_PATH="$(latest_file "${BACKUP_ROOT}/minio/minio_*.tgz")"
fi

for f in "${POSTGRES_BACKUP_PATH}" "${UPLOADS_BACKUP_PATH}" "${MINIO_BACKUP_PATH}"; do
  if [[ -z "${f}" || ! -f "${f}" ]]; then
    echo "[restore-evidence] missing backup artifact: ${f:-<empty>}" | tee -a "${LOG_PATH}" >&2
    exit 1
  fi
done

cp "${POSTGRES_BACKUP_PATH}" "${OUT_DIR}/backups/"
cp "${UPLOADS_BACKUP_PATH}" "${OUT_DIR}/backups/"
cp "${MINIO_BACKUP_PATH}" "${OUT_DIR}/backups/"
sha256_write "${CHECKSUMS_PATH}" "${OUT_DIR}/backups/"*

backup_stamp="$(basename "${POSTGRES_BACKUP_PATH}")"
backup_stamp="${backup_stamp#classhub_}"
backup_stamp="${backup_stamp%.sql}"
if [[ ! "${backup_stamp}" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo "[restore-evidence] unexpected backup stamp format: ${backup_stamp}" | tee -a "${LOG_PATH}" >&2
  exit 1
fi

backup_epoch="$(
python3 - "${backup_stamp}" <<'PY'
from datetime import datetime, timezone
import sys

stamp = sys.argv[1]
dt = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
print(int(dt.timestamp()))
PY
)"
rpo_seconds="$((end_epoch - backup_epoch))"
replacement_host_proof="false"
if [[ "${HOST_CLASS}" == "replacement-host" ]]; then
  replacement_host_proof="true"
fi

python3 - <<'PY' "${METRICS_PATH}" "${SUMMARY_PATH}" "${start_utc}" "${end_utc}" "${duration_seconds}" \
  "${RTO_THRESHOLD_SECONDS}" "${rpo_seconds}" "${RPO_THRESHOLD_SECONDS}" "${HOST_CLASS}" "${HOST_LABEL}" \
  "${SCENARIO_LABEL}" "${EVIDENCE_NOTE}" "${COMPOSE_MODE}" "${BACKUP_ROOT}" "${OUT_DIR}" \
  "$(basename "${POSTGRES_BACKUP_PATH}")" "$(basename "${UPLOADS_BACKUP_PATH}")" "$(basename "${MINIO_BACKUP_PATH}")" \
  "${CHECKSUMS_PATH}" "${replacement_host_proof}"
from pathlib import Path
import json
import sys

(
    metrics_path,
    summary_path,
    start_utc,
    end_utc,
    duration_seconds,
    rto_threshold_seconds,
    rpo_seconds,
    rpo_threshold_seconds,
    host_class,
    host_label,
    scenario_label,
    evidence_note,
    compose_mode,
    backup_root,
    out_dir,
    postgres_backup,
    uploads_backup,
    minio_backup,
    checksums_path,
    replacement_host_proof,
) = sys.argv[1:]

metrics = {
    "workflow": "restore-rehearsal",
    "started_at_utc": start_utc,
    "ended_at_utc": end_utc,
    "duration_seconds": int(duration_seconds),
    "rto_threshold_seconds": int(rto_threshold_seconds),
    "rpo_seconds": int(rpo_seconds),
    "rpo_threshold_seconds": int(rpo_threshold_seconds),
    "host_class": host_class,
    "host_label": host_label,
    "replacement_host_proof": replacement_host_proof == "true",
    "scenario_label": scenario_label,
    "evidence_note": evidence_note,
    "compose_mode": compose_mode,
    "backup_root": backup_root,
    "out_dir": out_dir,
    "postgres_backup": postgres_backup,
    "uploads_backup": uploads_backup,
    "minio_backup": minio_backup,
    "checksums_path": checksums_path,
}
Path(metrics_path).write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

summary_lines = [
    "### Restore Rehearsal Evidence",
    f"- Host class: {host_class}",
    f"- Host label: {host_label}",
    f"- Replacement-host proof: {'yes' if replacement_host_proof == 'true' else 'no'}",
    f"- Scenario: {scenario_label}",
    f"- Compose mode: {compose_mode}",
    f"- Started (UTC): {start_utc}",
    f"- Ended (UTC): {end_utc}",
    f"- Duration (RTO): {duration_seconds}s (threshold: {rto_threshold_seconds}s)",
    f"- Backup age at completion (RPO): {rpo_seconds}s (threshold: {rpo_threshold_seconds}s)",
]
if evidence_note:
    summary_lines.append(f"- Operator note: {evidence_note}")
summary_lines.extend(
    [
        "- Artifacts:",
        f"  - {postgres_backup}",
        f"  - {uploads_backup}",
        f"  - {minio_backup}",
        f"- Checksums: {checksums_path}",
    ]
)
Path(summary_path).write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
PY

cat "${SUMMARY_PATH}"

if (( duration_seconds > RTO_THRESHOLD_SECONDS )); then
  echo "[restore-evidence] RTO threshold exceeded: ${duration_seconds}s > ${RTO_THRESHOLD_SECONDS}s" | tee -a "${LOG_PATH}" >&2
  exit 1
fi
if (( rpo_seconds > RPO_THRESHOLD_SECONDS )); then
  echo "[restore-evidence] RPO threshold exceeded: ${rpo_seconds}s > ${RPO_THRESHOLD_SECONDS}s" | tee -a "${LOG_PATH}" >&2
  exit 1
fi

echo "[restore-evidence] PASS (output: ${OUT_DIR})" | tee -a "${LOG_PATH}"
