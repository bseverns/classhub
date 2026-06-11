#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEADSCALE_ROOT="${HEADSCALE_ROOT:-/srv/headscale}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/artifacts/stability/$(date +%F)/headscale_restore_rehearsal/${STAMP}}"
BACKUP_PATH=""
HOST_CLASS="${HOST_CLASS:-replacement-host}" # replacement-host|same-host
HOST_LABEL="${HOST_LABEL:-}"
SCENARIO_LABEL="${SCENARIO_LABEL:-headscale-restore-rehearsal}"
EVIDENCE_NOTE="${EVIDENCE_NOTE:-}"
TIMEZONE="${TIMEZONE:-Etc/UTC}"
INSTALL_SYSTEMD="${INSTALL_SYSTEMD:-1}" # 0|1
RUN_INSTALL=1
START_STACK=1
KEEP_TEMP=0
HELPER_PROBE_COMMAND="${HELPER_PROBE_COMMAND:-cd /srv/lms/app && bash scripts/check_llm_backend.sh --probe-chat && curl -fsS https://lms.creatempls.org/healthz}"
HELPER_PROBE_OUTPUT=""
NODE_MEMBERSHIP_OUTPUT=""
GPU_HEALTH_OUTPUT=""

usage() {
  cat <<'EOF'
Usage: sudo bash scripts/headscale_restore_rehearsal_evidence.sh --backup <archive.tgz> [options]

Runs the repo-shipped Headscale bootstrap + restore path as a rehearsal wrapper and
captures evidence suitable for artifacts/stability/<date>/headscale_restore_rehearsal/.

What it does:
1) optionally runs ops/headscale/install.sh on a fresh/replacement Headscale host
2) restores one Headscale backup archive
3) re-enables the runtime stack and backup timer when systemd units are installed
4) captures local status evidence from the Headscale host
5) creates manual verification placeholders for LMS/model-host checks
6) writes log, metrics JSON, checklist, and markdown summary artifacts

Options:
  --headscale-root <dir>         Runtime root (default: /srv/headscale)
  --backup <archive.tgz>         Backup archive produced by ops/headscale/backup.sh
  --out-dir <dir>                Evidence output directory
  --host-class <replacement-host|same-host>
                                 Evidence label for where the rehearsal ran
  --host-label <label>           Hostname or operator label recorded in evidence
  --scenario-label <label>       Short scenario label (default: headscale-restore-rehearsal)
  --evidence-note <text>         Optional operator note recorded in metrics and summary
  --skip-install                 Skip ops/headscale/install.sh and assume host is already bootstrapped
  --timezone <tz>                Passed through to ops/headscale/install.sh (default: Etc/UTC)
  --install-systemd <0|1>        Whether install.sh should install systemd units (default: 1)
  --no-start-stack               Restore files only; do not start or enable the restored stack
  --keep-temp                    Keep restore temp extraction directory
  --helper-probe-command <cmd>   LMS-host command string recorded in the checklist
  --helper-probe-output <file>   Optional existing LMS helper-probe output to copy into the artifact
  --node-membership-output <file>
                                 Optional existing Headscale node-list output to copy into the artifact
  --gpu-health-output <file>     Optional existing GPU-host health output to copy into the artifact
  -h, --help                     Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headscale-root)
      HEADSCALE_ROOT="$2"
      shift 2
      ;;
    --backup)
      BACKUP_PATH="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
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
    --skip-install)
      RUN_INSTALL=0
      shift
      ;;
    --timezone)
      TIMEZONE="$2"
      shift 2
      ;;
    --install-systemd)
      INSTALL_SYSTEMD="$2"
      shift 2
      ;;
    --no-start-stack)
      START_STACK=0
      shift
      ;;
    --keep-temp)
      KEEP_TEMP=1
      shift
      ;;
    --helper-probe-command)
      HELPER_PROBE_COMMAND="$2"
      shift 2
      ;;
    --helper-probe-output)
      HELPER_PROBE_OUTPUT="$2"
      shift 2
      ;;
    --node-membership-output)
      NODE_MEMBERSHIP_OUTPUT="$2"
      shift 2
      ;;
    --gpu-health-output)
      GPU_HEALTH_OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[headscale-rehearsal] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BACKUP_PATH}" ]]; then
  echo "[headscale-rehearsal] --backup is required" >&2
  exit 1
fi
if [[ ! -f "${BACKUP_PATH}" ]]; then
  echo "[headscale-rehearsal] missing backup archive: ${BACKUP_PATH}" >&2
  exit 1
fi
if [[ "${HOST_CLASS}" != "replacement-host" && "${HOST_CLASS}" != "same-host" ]]; then
  echo "[headscale-rehearsal] --host-class must be replacement-host or same-host" >&2
  exit 1
fi
if [[ "${INSTALL_SYSTEMD}" != "0" && "${INSTALL_SYSTEMD}" != "1" ]]; then
  echo "[headscale-rehearsal] --install-systemd must be 0 or 1" >&2
  exit 1
fi
if [[ "${EUID}" -ne 0 ]]; then
  echo "[headscale-rehearsal] run as root (sudo)." >&2
  exit 1
fi
for optional_file in "${HELPER_PROBE_OUTPUT}" "${NODE_MEMBERSHIP_OUTPUT}" "${GPU_HEALTH_OUTPUT}"; do
  if [[ -n "${optional_file}" && ! -f "${optional_file}" ]]; then
    echo "[headscale-rehearsal] missing attachment: ${optional_file}" >&2
    exit 1
  fi
done

if [[ -z "${HOST_LABEL}" ]]; then
  HOST_LABEL="$(hostname 2>/dev/null || echo "unknown-host")"
fi

mkdir -p "${OUT_DIR}" "${OUT_DIR}/automated" "${OUT_DIR}/manual"
LOG_PATH="${OUT_DIR}/headscale_restore_rehearsal.log"
METRICS_PATH="${OUT_DIR}/headscale_restore_rehearsal_metrics.json"
SUMMARY_PATH="${OUT_DIR}/headscale_restore_rehearsal_summary.md"
CHECKLIST_PATH="${OUT_DIR}/manual_verification_checklist.md"
AUTOMATED_DIR="${OUT_DIR}/automated"
MANUAL_DIR="${OUT_DIR}/manual"

start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
start_epoch="$(date +%s)"

echo "[headscale-rehearsal] started ${start_utc}" | tee "${LOG_PATH}"
echo "[headscale-rehearsal] host-class: ${HOST_CLASS}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] host-label: ${HOST_LABEL}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] scenario-label: ${SCENARIO_LABEL}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] headscale-root: ${HEADSCALE_ROOT}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] backup: ${BACKUP_PATH}" | tee -a "${LOG_PATH}"
if [[ -n "${EVIDENCE_NOTE}" ]]; then
  echo "[headscale-rehearsal] evidence-note: ${EVIDENCE_NOTE}" | tee -a "${LOG_PATH}"
fi

run_capture() {
  local label="$1"
  local out_path="$2"
  shift 2
  if "$@" >"${out_path}" 2>&1; then
    echo "[headscale-rehearsal] PASS ${label}" | tee -a "${LOG_PATH}"
    return 0
  fi
  local status=$?
  echo "[headscale-rehearsal] FAIL ${label} (exit ${status})" | tee -a "${LOG_PATH}"
  return "${status}"
}

copy_or_template() {
  local dest_path="$1"
  local supplied_path="$2"
  local template_body="$3"
  if [[ -n "${supplied_path}" ]]; then
    cp "${supplied_path}" "${dest_path}"
    return 0
  fi
  cat > "${dest_path}" <<EOF
${template_body}
EOF
}

INSTALL_OK=1
RESTORE_OK=0
STACK_ENABLE_OK=0
BACKUP_TIMER_OK=0
SERVICE_STATUS_OK=0
BACKUP_TIMER_STATUS_OK=0
COMPOSE_PS_OK=0
METRICS_OK=0
LOGS_OK=0
NODE_LIST_OK=0

if (( RUN_INSTALL == 1 )); then
  if run_capture \
    "bootstrap install" \
    "${AUTOMATED_DIR}/install.txt" \
    env REPO_ROOT="${ROOT_DIR}" HEADSCALE_ROOT="${HEADSCALE_ROOT}" TIMEZONE="${TIMEZONE}" \
      INSTALL_SYSTEMD="${INSTALL_SYSTEMD}" bash "${ROOT_DIR}/ops/headscale/install.sh"; then
    INSTALL_OK=1
  else
    INSTALL_OK=0
  fi
fi
if (( RUN_INSTALL == 0 )); then
  cat > "${AUTOMATED_DIR}/install.txt" <<'EOF'
Install step skipped by operator request (--skip-install).
Assume the host was already bootstrapped with ops/headscale/install.sh.
EOF
fi

if (( INSTALL_OK == 1 )); then
  restore_cmd=(env HEADSCALE_ROOT="${HEADSCALE_ROOT}" bash "${ROOT_DIR}/ops/headscale/restore.sh" --backup "${BACKUP_PATH}")
  if (( KEEP_TEMP == 1 )); then
    restore_cmd+=(--keep-temp)
  fi
  if (( START_STACK == 1 )) && [[ "${INSTALL_SYSTEMD}" == "0" ]]; then
    restore_cmd+=(--start-stack)
  fi
  if run_capture "restore archive" "${AUTOMATED_DIR}/restore.txt" "${restore_cmd[@]}"; then
    RESTORE_OK=1
  fi
fi
if [[ ! -f "${AUTOMATED_DIR}/restore.txt" ]]; then
  cat > "${AUTOMATED_DIR}/restore.txt" <<'EOF'
Restore step did not run because an earlier prerequisite failed.
Inspect install.txt and the main rehearsal log for the blocking failure.
EOF
fi

if (( RESTORE_OK == 1 )) && (( START_STACK == 1 )); then
  if [[ "${INSTALL_SYSTEMD}" == "1" ]]; then
    if run_capture \
      "enable runtime stack" \
      "${AUTOMATED_DIR}/enable_stack.txt" \
      bash -lc "systemctl daemon-reload && systemctl enable --now classhub-headscale"; then
      STACK_ENABLE_OK=1
    fi
    if run_capture \
      "enable backup timer" \
      "${AUTOMATED_DIR}/enable_backup_timer.txt" \
      bash -lc "systemctl enable --now classhub-headscale-backup.timer"; then
      BACKUP_TIMER_OK=1
    fi
  else
    STACK_ENABLE_OK=1
    BACKUP_TIMER_OK=1
  fi
fi
if [[ ! -f "${AUTOMATED_DIR}/enable_stack.txt" ]]; then
  cat > "${AUTOMATED_DIR}/enable_stack.txt" <<'EOF'
Runtime stack enable step did not run.
This happens when restore failed, --no-start-stack was used, or systemd management was disabled.
EOF
fi
if [[ ! -f "${AUTOMATED_DIR}/enable_backup_timer.txt" ]]; then
  cat > "${AUTOMATED_DIR}/enable_backup_timer.txt" <<'EOF'
Backup timer enable step did not run.
This happens when restore failed, --no-start-stack was used, or systemd management was disabled.
EOF
fi

if [[ "${INSTALL_SYSTEMD}" == "1" ]]; then
  if run_capture \
    "service status" \
    "${AUTOMATED_DIR}/systemctl_classhub_headscale.txt" \
    systemctl status classhub-headscale --no-pager; then
    SERVICE_STATUS_OK=1
  fi
  if run_capture \
    "backup timer status" \
    "${AUTOMATED_DIR}/systemctl_headscale_backup_timer.txt" \
    systemctl status classhub-headscale-backup.timer --no-pager; then
    BACKUP_TIMER_STATUS_OK=1
  fi
else
  cat > "${AUTOMATED_DIR}/systemctl_classhub_headscale.txt" <<'EOF'
Systemd status capture skipped because install-systemd=0.
Start and inspect the stack manually with:
  cd /srv/headscale
  docker compose up -d --remove-orphans
  docker compose ps
EOF
  cp "${AUTOMATED_DIR}/systemctl_classhub_headscale.txt" "${AUTOMATED_DIR}/systemctl_headscale_backup_timer.txt"
fi

if run_capture \
  "compose ps" \
  "${AUTOMATED_DIR}/docker_compose_ps.txt" \
  bash -lc "cd '${HEADSCALE_ROOT}' && docker compose ps"; then
  COMPOSE_PS_OK=1
fi

if run_capture \
  "metrics sample" \
  "${AUTOMATED_DIR}/headscale_metrics_sample.txt" \
  bash -lc "curl -fsS http://127.0.0.1:9090/metrics | sed -n '1,40p'"; then
  METRICS_OK=1
fi

if run_capture \
  "compose logs" \
  "${AUTOMATED_DIR}/docker_compose_logs.txt" \
  bash -lc "cd '${HEADSCALE_ROOT}' && docker compose logs --tail=120"; then
  LOGS_OK=1
fi

if run_capture \
  "node list" \
  "${AUTOMATED_DIR}/headscale_nodes_list.txt" \
  bash -lc "cd '${HEADSCALE_ROOT}' && docker compose exec -T headscale headscale nodes list"; then
  NODE_LIST_OK=1
fi

BACKUP_REFERENCE_PATH="${AUTOMATED_DIR}/backup_reference.txt"
{
  echo "backup_path=${BACKUP_PATH}"
  if [[ -f "${BACKUP_PATH}.sha256" ]]; then
    echo "backup_checksum_file=${BACKUP_PATH}.sha256"
    echo
    cat "${BACKUP_PATH}.sha256"
  else
    echo "backup_checksum_file="
  fi
} > "${BACKUP_REFERENCE_PATH}"

copy_or_template \
  "${MANUAL_DIR}/lms_helper_probe.txt" \
  "${HELPER_PROBE_OUTPUT}" \
"Run from the LMS host after the Headscale host restore completes:

${HELPER_PROBE_COMMAND}

Paste the command output here and note whether helper-private-path readiness recovered without app config changes."

copy_or_template \
  "${MANUAL_DIR}/node_rejoin_notes.txt" \
  "${NODE_MEMBERSHIP_OUTPUT}" \
"Record whether the LMS host and private model host rejoined cleanly after the restore.

Suggested command from the Headscale host:
cd ${HEADSCALE_ROOT} && docker compose exec -T headscale headscale nodes list

Expected outcome:
- LMS host present
- private model host present
- no improvised enrollment flow required"

copy_or_template \
  "${MANUAL_DIR}/gpu_health_check.txt" \
  "${GPU_HEALTH_OUTPUT}" \
"Optional model-host follow-up if the LMS helper probe fails:

curl -fsS http://127.0.0.1:11434/api/tags

Paste the output here or explain why the model-host check was not needed."

cat > "${CHECKLIST_PATH}" <<EOF
# Headscale Restore Rehearsal Manual Checklist

Artifact directory: \`${OUT_DIR}\`

Fill this in during or immediately after the rehearsal.

| Step | Expected command or evidence | Pass/Fail | Notes |
| --- | --- | --- | --- |
| Fresh host bootstrap completed | \`sudo bash ops/headscale/install.sh\` or attach skip rationale |  |  |
| Backup archive restored | \`sudo bash ops/headscale/restore.sh --backup ...\` |  |  |
| Headscale stack active | \`systemctl status classhub-headscale --no-pager\` |  |  |
| Backup timer active | \`systemctl status classhub-headscale-backup.timer --no-pager\` |  |  |
| Compose services up | \`cd ${HEADSCALE_ROOT} && docker compose ps\` |  |  |
| Metrics reachable locally | \`curl -fsS http://127.0.0.1:9090/metrics >/dev/null\` |  |  |
| Tailnet nodes rejoined | See \`manual/node_rejoin_notes.txt\` |  |  |
| LMS helper probe recovered | See \`manual/lms_helper_probe.txt\` |  |  |
| Public LMS still healthy | \`curl -fsS https://lms.creatempls.org/healthz\` from LMS host or public edge |  |  |
| Model host only checked if needed | See \`manual/gpu_health_check.txt\` |  |  |

## Operator got stuck here

- Step:
- Symptom:
- What was improvised, if anything:
- What should be turned into a calmer artifact next:
EOF

end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
end_epoch="$(date +%s)"
duration_seconds="$((end_epoch - start_epoch))"

HELPER_PROBE_ATTACHED=0
NODE_MEMBERSHIP_ATTACHED=0
GPU_HEALTH_ATTACHED=0
if [[ -n "${HELPER_PROBE_OUTPUT}" ]]; then
  HELPER_PROBE_ATTACHED=1
fi
if [[ -n "${NODE_MEMBERSHIP_OUTPUT}" ]]; then
  NODE_MEMBERSHIP_ATTACHED=1
fi
if [[ -n "${GPU_HEALTH_OUTPUT}" ]]; then
  GPU_HEALTH_ATTACHED=1
fi

OVERALL_STATUS="pass"
if (( INSTALL_OK == 0 || RESTORE_OK == 0 || COMPOSE_PS_OK == 0 || METRICS_OK == 0 )); then
  OVERALL_STATUS="fail"
fi
if [[ "${INSTALL_SYSTEMD}" == "1" ]] && (( STACK_ENABLE_OK == 0 || BACKUP_TIMER_OK == 0 || SERVICE_STATUS_OK == 0 || BACKUP_TIMER_STATUS_OK == 0 )); then
  OVERALL_STATUS="fail"
fi

export START_UTC="${start_utc}"
export END_UTC="${end_utc}"
export DURATION_SECONDS="${duration_seconds}"
export HOST_CLASS
export HOST_LABEL
export SCENARIO_LABEL
export HEADSCALE_ROOT
export BACKUP_PATH
export EVIDENCE_NOTE
export RUN_INSTALL
export INSTALL_SYSTEMD
export START_STACK
export KEEP_TEMP
export INSTALL_OK
export RESTORE_OK
export STACK_ENABLE_OK
export BACKUP_TIMER_OK
export SERVICE_STATUS_OK
export BACKUP_TIMER_STATUS_OK
export COMPOSE_PS_OK
export METRICS_OK
export LOGS_OK
export NODE_LIST_OK
export HELPER_PROBE_ATTACHED
export NODE_MEMBERSHIP_ATTACHED
export GPU_HEALTH_ATTACHED
export HELPER_PROBE_COMMAND
export OVERALL_STATUS

python3 - <<'PY' > "${METRICS_PATH}"
import json
import os


def as_int(name: str) -> int:
    return int(os.environ.get(name, "0") or "0")


payload = {
    "started_at": os.environ["START_UTC"],
    "completed_at": os.environ["END_UTC"],
    "duration_seconds": as_int("DURATION_SECONDS"),
    "overall_status": os.environ["OVERALL_STATUS"],
    "host_class": os.environ["HOST_CLASS"],
    "host_label": os.environ["HOST_LABEL"],
    "scenario_label": os.environ["SCENARIO_LABEL"],
    "headscale_root": os.environ["HEADSCALE_ROOT"],
    "backup_path": os.environ["BACKUP_PATH"],
    "evidence_note": os.environ.get("EVIDENCE_NOTE", ""),
    "replacement_host_proof_expected": os.environ["HOST_CLASS"] == "replacement-host",
    "bootstrap": {
        "run_install": bool(as_int("RUN_INSTALL")),
        "install_systemd": bool(as_int("INSTALL_SYSTEMD")),
        "start_stack": bool(as_int("START_STACK")),
        "keep_temp": bool(as_int("KEEP_TEMP")),
        "install_ok": bool(as_int("INSTALL_OK")),
        "restore_ok": bool(as_int("RESTORE_OK")),
        "stack_enable_ok": bool(as_int("STACK_ENABLE_OK")),
        "backup_timer_enable_ok": bool(as_int("BACKUP_TIMER_OK")),
    },
    "automated_checks": {
        "service_status_ok": bool(as_int("SERVICE_STATUS_OK")),
        "backup_timer_status_ok": bool(as_int("BACKUP_TIMER_STATUS_OK")),
        "compose_ps_ok": bool(as_int("COMPOSE_PS_OK")),
        "metrics_ok": bool(as_int("METRICS_OK")),
        "compose_logs_ok": bool(as_int("LOGS_OK")),
        "node_list_ok": bool(as_int("NODE_LIST_OK")),
    },
    "manual_evidence": {
        "helper_probe_attached": bool(as_int("HELPER_PROBE_ATTACHED")),
        "node_membership_attached": bool(as_int("NODE_MEMBERSHIP_ATTACHED")),
        "gpu_health_attached": bool(as_int("GPU_HEALTH_ATTACHED")),
        "helper_probe_command": os.environ.get("HELPER_PROBE_COMMAND", ""),
    },
}

print(json.dumps(payload, indent=2))
PY

cat > "${SUMMARY_PATH}" <<EOF
# Headscale Restore Rehearsal Summary

- Started: \`${start_utc}\`
- Completed: \`${end_utc}\`
- Duration: \`${duration_seconds}\` seconds
- Overall status: \`${OVERALL_STATUS}\`
- Host class: \`${HOST_CLASS}\`
- Host label: \`${HOST_LABEL}\`
- Scenario: \`${SCENARIO_LABEL}\`
- Headscale root: \`${HEADSCALE_ROOT}\`
- Backup archive: \`${BACKUP_PATH}\`
- Fresh bootstrap attempted: \`$( [[ "${RUN_INSTALL}" == "1" ]] && echo yes || echo no )\`
- Replacement-host proof expected: \`$( [[ "${HOST_CLASS}" == "replacement-host" ]] && echo yes || echo no )\`

## Automated step results

| Step | Result |
| --- | --- |
| Install/bootstrap | \`$( [[ "${INSTALL_OK}" == "1" ]] && echo pass || echo fail )\` |
| Restore archive | \`$( [[ "${RESTORE_OK}" == "1" ]] && echo pass || echo fail )\` |
| Enable runtime stack | \`$( [[ "${STACK_ENABLE_OK}" == "1" ]] && echo pass || echo fail )\` |
| Enable backup timer | \`$( [[ "${BACKUP_TIMER_OK}" == "1" ]] && echo pass || echo fail )\` |
| Service status capture | \`$( [[ "${SERVICE_STATUS_OK}" == "1" ]] && echo pass || echo fail )\` |
| Backup timer status capture | \`$( [[ "${BACKUP_TIMER_STATUS_OK}" == "1" ]] && echo pass || echo fail )\` |
| Compose status capture | \`$( [[ "${COMPOSE_PS_OK}" == "1" ]] && echo pass || echo fail )\` |
| Metrics sample capture | \`$( [[ "${METRICS_OK}" == "1" ]] && echo pass || echo fail )\` |
| Compose logs capture | \`$( [[ "${LOGS_OK}" == "1" ]] && echo pass || echo fail )\` |
| Node list capture | \`$( [[ "${NODE_LIST_OK}" == "1" ]] && echo pass || echo fail )\` |

## Manual follow-up still required

- Review and complete \`manual_verification_checklist.md\`.
- Confirm LMS/helper-side private path readiness using:
  - \`${HELPER_PROBE_COMMAND}\`
- Attach or edit:
  - \`manual/lms_helper_probe.txt\`
  - \`manual/node_rejoin_notes.txt\`
  - \`manual/gpu_health_check.txt\`

## Evidence files

- \`headscale_restore_rehearsal.log\`
- \`headscale_restore_rehearsal_metrics.json\`
- \`manual_verification_checklist.md\`
- \`automated/install.txt\`
- \`automated/restore.txt\`
- \`automated/systemctl_classhub_headscale.txt\`
- \`automated/systemctl_headscale_backup_timer.txt\`
- \`automated/docker_compose_ps.txt\`
- \`automated/headscale_metrics_sample.txt\`
- \`automated/docker_compose_logs.txt\`
- \`automated/headscale_nodes_list.txt\`
- \`automated/backup_reference.txt\`

## Notes

${EVIDENCE_NOTE:-No operator note supplied.}
EOF

echo "[headscale-rehearsal] wrote ${OUT_DIR}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] summary ${SUMMARY_PATH}" | tee -a "${LOG_PATH}"
echo "[headscale-rehearsal] checklist ${CHECKLIST_PATH}" | tee -a "${LOG_PATH}"

if [[ "${OVERALL_STATUS}" != "pass" ]]; then
  exit 1
fi
