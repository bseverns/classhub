# Bootstrap the server

Use `scripts/bootstrap_day1.sh`.

It will:
- update packages
- enable UFW + fail2ban
- install Docker + Compose
- set Docker log rotation limits
- create `/srv/classhub` folder structure

After bootstrapping:
- add SSH keys for deploy user
- (optionally) enable SSH hardening
- point DNS when domain is known
- install/configure the LLM backend (Ollama by default)
