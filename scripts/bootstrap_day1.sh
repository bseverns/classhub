#!/usr/bin/env bash
set -euo pipefail

# Day-1 bootstrap for a fresh Ubuntu server.
# Safe-by-default: does NOT harden SSH unless HARDEN_SSH=1.
#
# Usage:
#   sudo DOMAIN="lms.example.org" DEPLOY_USER="deploy" ./bootstrap_day1.sh

DEPLOY_USER="${DEPLOY_USER:-deploy}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/classhub}"
TIMEZONE="${TIMEZONE:-Etc/UTC}"
HARDEN_SSH="${HARDEN_SSH:-0}"

log(){ echo -e "\n==> $*\n"; }
warn(){ echo -e "\n[WARN] $*\n" >&2; }

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

log "OS updates"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw fail2ban unattended-upgrades openssl

log "Timezone"
timedatectl set-timezone "$TIMEZONE" || true

log "Deploy user"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
  usermod -aG sudo "$DEPLOY_USER"
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
  UBUNTU_CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

usermod -aG docker "$DEPLOY_USER" || true
systemctl enable --now docker

log "Docker log limits"
mkdir -p /etc/docker
if [[ ! -f /etc/docker/daemon.json ]]; then
  cat > /etc/docker/daemon.json <<'J'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
J
fi
systemctl restart docker

log "Create directory spine"
mkdir -p "$PROJECT_ROOT"/{compose,data/postgres,data/minio,data/ollama,data/classhub_uploads,backups/postgres,backups/minio,logs}
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$PROJECT_ROOT"
chmod 750 "$PROJECT_ROOT"

log "Optional SSH hardening"
if [[ "$HARDEN_SSH" == "1" ]]; then
  warn "Hardening SSH. Ensure you can log in via SSH key first."
  sed -i -E 's/^#?PermitRootLogin\s+.*/PermitRootLogin no/' /etc/ssh/sshd_config || true
  sed -i -E 's/^#?PasswordAuthentication\s+.*/PasswordAuthentication no/' /etc/ssh/sshd_config || true
  sed -i -E 's/^#?KbdInteractiveAuthentication\s+.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config || true
  systemctl restart ssh || systemctl restart sshd || true
fi

log "Done"
echo "Next: copy this repo's compose/* into $PROJECT_ROOT/compose and set .env"
