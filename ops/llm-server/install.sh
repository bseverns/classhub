#!/usr/bin/env bash
set -euo pipefail

MODE="${MODE:-ollama}" # ollama or vllm

if [[ "${EUID}" -ne 0 ]]; then
  echo "[llm-install] run as root (or via sudo)" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  jq \
  python3 \
  python3-venv \
  python3-pip

curl -fsSL https://tailscale.com/install.sh | sh

mkdir -p /etc/classhub /opt/classhub-llm

if [[ "${MODE}" == "ollama" ]]; then
  curl -fsSL https://ollama.com/install.sh | sh
elif [[ "${MODE}" == "vllm" ]]; then
  python3 -m venv /opt/classhub-llm/.venv
  /opt/classhub-llm/.venv/bin/pip install --upgrade pip
  /opt/classhub-llm/.venv/bin/pip install "vllm>=0.8,<1"
else
  echo "[llm-install] MODE must be ollama or vllm" >&2
  exit 1
fi

cat <<'EOF'
[llm-install] base packages installed.

Next steps:
1. Copy ops/llm-server/env.example to /etc/classhub/llm-server.env and fill secrets.
2. Install Caddy separately if you plan to use the private Ollama auth proxy.
3. Copy the service files you plan to use into /etc/systemd/system/.
4. Copy runtime scripts/Caddyfile into /opt/classhub-llm/.
5. Run `tailscale up --ssh --advertise-tags=tag:llm`.
6. Start the chosen model service.
7. Start the optional private proxy if using Ollama.
8. Publish the private HTTPS endpoint with `tailscale serve`.
EOF
