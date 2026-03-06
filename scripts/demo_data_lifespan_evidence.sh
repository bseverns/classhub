#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/demo_data_lifespan_evidence.sh \
    --base-url https://YOUR_DOMAIN \
    --cookie-file classhub_teach_cookie.txt \
    [--out-dir /tmp/classhub_evidence_demo] \
    [--insecure]

Description:
  Captures operator-facing privacy evidence artifacts from /teach/data-lifespan:
  - JSON snapshot export
  - CSV snapshot export
  - HTML dashboard capture

Notes:
  - Requires a valid authenticated teacher/admin/superuser session cookie file.
  - Use --insecure only for local/self-signed TLS test environments.
EOF
}

BASE_URL="${BASE_URL:-http://localhost}"
COOKIE_FILE="${COOKIE_FILE:-}"
OUT_DIR="${OUT_DIR:-/tmp/classhub_evidence_$(date +%Y%m%d_%H%M%S)}"
INSECURE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --cookie-file)
      COOKIE_FILE="${2:-}"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    --insecure)
      INSECURE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${COOKIE_FILE}" ]]; then
  echo "ERROR: --cookie-file is required" >&2
  usage >&2
  exit 2
fi

if [[ ! -f "${COOKIE_FILE}" ]]; then
  echo "ERROR: cookie file not found: ${COOKIE_FILE}" >&2
  exit 2
fi

mkdir -p "${OUT_DIR}"

curl_flags=(-sS -L --fail --show-error --max-time 60 -b "${COOKIE_FILE}")
if [[ "${INSECURE}" == "1" ]]; then
  curl_flags+=(-k)
fi

json_out="${OUT_DIR}/data_lifespan_snapshot.json"
csv_out="${OUT_DIR}/data_lifespan_snapshot.csv"
html_out="${OUT_DIR}/data_lifespan_dashboard.html"
meta_out="${OUT_DIR}/capture_metadata.txt"

echo "[evidence-demo] base url: ${BASE_URL}"
echo "[evidence-demo] output dir: ${OUT_DIR}"

curl "${curl_flags[@]}" \
  "${BASE_URL}/teach/data-lifespan/export?format=json" \
  -o "${json_out}"

curl "${curl_flags[@]}" \
  "${BASE_URL}/teach/data-lifespan/export?format=csv" \
  -o "${csv_out}"

curl "${curl_flags[@]}" \
  "${BASE_URL}/teach/data-lifespan" \
  -o "${html_out}"

{
  echo "captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "base_url=${BASE_URL}"
  echo "json_file=${json_out}"
  echo "csv_file=${csv_out}"
  echo "html_file=${html_out}"
} > "${meta_out}"

if grep -Eqi 'rag|curriculum|index' "${html_out}"; then
  echo "[evidence-demo] RAG posture section detected in dashboard HTML."
else
  echo "[evidence-demo] WARNING: RAG posture strings not detected in dashboard HTML; verify panel visibility manually."
fi

echo "[evidence-demo] captured:"
echo "  - ${json_out}"
echo "  - ${csv_out}"
echo "  - ${html_out}"
echo "  - ${meta_out}"
