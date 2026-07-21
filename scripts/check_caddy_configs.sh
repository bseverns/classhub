#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CADDY_IMAGE="${CADDY_IMAGE:-caddy:2.10.2}"

validate_config() {
  local primary_template="$1"
  local extra_template="$2"
  local label="$3"

  docker run --rm \
    -e DOMAIN=lms.school.example \
    -e ASSET_DOMAIN=assets.school.example \
    -e CADDY_STATIC_SITE_DOMAINS=school.example,www.school.example \
    -v "${ROOT_DIR}/compose/${primary_template}:/etc/caddy/Caddyfile:ro" \
    -v "${ROOT_DIR}/compose/${extra_template}:/etc/caddy/Caddyfile.extra:ro" \
    -v "${ROOT_DIR}/compose/static-site.empty:/srv/caddy-static-site:ro" \
    "${CADDY_IMAGE}" \
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null

  echo "[caddy-config-guard] OK: ${label}"
}

validate_config Caddyfile.domain Caddyfile.extra.empty "domain"
validate_config Caddyfile.domain.assets Caddyfile.extra.empty "domain + assets"
validate_config Caddyfile.domain.assets Caddyfile.extra.static-site "domain + assets + static site"
