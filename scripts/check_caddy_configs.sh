#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CADDY_IMAGE="${CADDY_IMAGE:-caddy:2.10.2}"

docker run --rm "${CADDY_IMAGE}" sh -ec \
  'command -v getent >/dev/null && command -v wget >/dev/null && wget --help 2>&1 | grep -q -- "--header"'
echo "[caddy-config-guard] OK: deploy probe tools"

validate_config() {
  local primary_template="$1"
  local extra_template="$2"
  local proxy_template="$3"
  local label="$4"

  docker run --rm \
    -e DOMAIN=lms.school.example \
    -e ASSET_DOMAIN=assets.school.example \
    -e "CADDY_STATIC_SITE_DOMAINS=school.example, www.school.example" \
    -e CADDY_MEMORY_ENGINE_DOMAIN=memory.school.example \
    -e CADDY_MEMORY_ENGINE_UPSTREAM=memory_engine_proxy:80 \
    -v "${ROOT_DIR}/compose/${primary_template}:/etc/caddy/Caddyfile:ro" \
    -v "${ROOT_DIR}/compose/${extra_template}:/etc/caddy/Caddyfile.extra:ro" \
    -v "${ROOT_DIR}/compose/${proxy_template}:/etc/caddy/Caddyfile.proxy:ro" \
    -v "${ROOT_DIR}/compose/static-site.empty:/srv/caddy-static-site:ro" \
    "${CADDY_IMAGE}" \
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null

  echo "[caddy-config-guard] OK: ${label}"
}

validate_config Caddyfile.domain Caddyfile.extra.empty Caddyfile.proxy.empty "domain"
validate_config Caddyfile.domain.assets Caddyfile.extra.empty Caddyfile.proxy.empty "domain + assets"
validate_config Caddyfile.domain.assets Caddyfile.extra.static-site Caddyfile.proxy.empty "domain + assets + static site"
validate_config Caddyfile.domain.assets Caddyfile.extra.static-site Caddyfile.proxy.memory-engine \
  "domain + assets + static site + Memory Engine proxy"
