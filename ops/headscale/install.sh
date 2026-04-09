#!/usr/bin/env bash
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-headscale}"
HEADSCALE_ROOT="${HEADSCALE_ROOT:-/srv/headscale}"
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TIMEZONE="${TIMEZONE:-Etc/UTC}"
INSTALL_SYSTEMD="${INSTALL_SYSTEMD:-1}"

log(){ echo -e "\n==> $*\n"; }
warn(){ echo -e "\n[WARN] $*\n" >&2; }

copy_if_missing() {
  local src="$1"
  local dest="$2"
  if [[ -e "${dest}" ]]; then
    echo "[headscale-install] keeping existing ${dest}"
    return 0
  fi
  install -D -m 0644 "${src}" "${dest}"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "[headscale-install] run as root (sudo)." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

log "OS updates"
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban unattended-upgrades openssl

log "Timezone"
timedatectl set-timezone "${TIMEZONE}" || true

log "Deploy user"
if ! id -u "${DEPLOY_USER}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "${DEPLOY_USER}"
  usermod -aG sudo "${DEPLOY_USER}"
  warn "Add SSH keys to /home/${DEPLOY_USER}/.ssh/authorized_keys before hardening SSH."
fi

log "Firewall"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

log "Fail2ban"
systemctl enable --now fail2ban

log "Install Docker"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  UBUNTU_CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

usermod -aG docker "${DEPLOY_USER}" || true
systemctl enable --now docker

log "Docker log limits"
mkdir -p /etc/docker
if [[ ! -f /etc/docker/daemon.json ]]; then
  cat >/etc/docker/daemon.json <<'J'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
J
fi
systemctl restart docker

log "Create Headscale directory spine"
mkdir -p \
  "${HEADSCALE_ROOT}/config" \
  "${HEADSCALE_ROOT}/data/lib" \
  "${HEADSCALE_ROOT}/data/run" \
  "${HEADSCALE_ROOT}/data/caddy_data" \
  "${HEADSCALE_ROOT}/data/caddy_config" \
  "${HEADSCALE_ROOT}/backups"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${HEADSCALE_ROOT}"
chmod 750 "${HEADSCALE_ROOT}"

log "Copy runtime templates"
copy_if_missing "${REPO_ROOT}/ops/headscale/docker-compose.yml" "${HEADSCALE_ROOT}/docker-compose.yml"
copy_if_missing "${REPO_ROOT}/ops/headscale/Caddyfile" "${HEADSCALE_ROOT}/Caddyfile"
copy_if_missing "${REPO_ROOT}/ops/headscale/env.example" "${HEADSCALE_ROOT}/.env.example"
copy_if_missing "${REPO_ROOT}/ops/headscale/config.yaml.example" "${HEADSCALE_ROOT}/config/config.yaml.example"
copy_if_missing "${REPO_ROOT}/ops/headscale/policy.hujson.example" "${HEADSCALE_ROOT}/config/policy.hujson.example"

log "Install backup / restore helper commands"
install -m 0755 "${REPO_ROOT}/ops/headscale/backup.sh" /usr/local/bin/classhub-headscale-backup
install -m 0755 "${REPO_ROOT}/ops/headscale/restore.sh" /usr/local/bin/classhub-headscale-restore

if [[ "${INSTALL_SYSTEMD}" == "1" ]]; then
  log "Install systemd units"
  install -m 0644 "${REPO_ROOT}/ops/headscale/classhub-headscale.service" /etc/systemd/system/classhub-headscale.service
  install -m 0644 "${REPO_ROOT}/ops/headscale/classhub-headscale-backup.service" /etc/systemd/system/classhub-headscale-backup.service
  install -m 0644 "${REPO_ROOT}/ops/headscale/classhub-headscale-backup.timer" /etc/systemd/system/classhub-headscale-backup.timer
  systemctl daemon-reload
fi

cat <<EOF
[headscale-install] base bootstrap complete.

Next steps:
1. Copy ${HEADSCALE_ROOT}/.env.example to ${HEADSCALE_ROOT}/.env and fill host-specific values.
2. Copy ${HEADSCALE_ROOT}/config/config.yaml.example to ${HEADSCALE_ROOT}/config/config.yaml and set server_url/base_domain.
3. Copy ${HEADSCALE_ROOT}/config/policy.hujson.example to ${HEADSCALE_ROOT}/config/policy.hujson and review ACL/tag owners.
4. Start the stack: sudo systemctl enable --now classhub-headscale
5. Enable backups: sudo systemctl enable --now classhub-headscale-backup.timer
6. Verify locally: cd ${HEADSCALE_ROOT} && docker compose ps && curl -fsS http://127.0.0.1:9090/metrics >/dev/null
EOF
