# Headscale Control Plane Ops

This directory is the repo-shipped bootstrap and recovery bundle for the createMPLS Headscale VPS.

Use it to make the Headscale control plane more boring:

- one canonical VPS layout
- one canonical Compose stack
- one canonical systemd wrapper
- one canonical backup command
- one canonical restore command

This bundle is intentionally narrow.

It is for the Headscale control plane only.
It is not for the public LMS.
It is not for the model service.
It is not for general office VPN routing.

## Recommended host

- tiny Ubuntu VPS
- 1 vCPU
- 1 GB RAM
- stable hostname such as `hs.creatempls.org`
- Docker Engine + Docker Compose plugin

## Canonical layout

Recommended root on the Headscale VPS:

- repo checkout: `/srv/headscale/app`
- runtime root: `/srv/headscale`

Runtime root contents after bootstrap:

- `/srv/headscale/docker-compose.yml`
- `/srv/headscale/.env`
- `/srv/headscale/Caddyfile`
- `/srv/headscale/config/config.yaml`
- `/srv/headscale/config/policy.hujson`
- `/srv/headscale/data/lib`
- `/srv/headscale/data/caddy_data`
- `/srv/headscale/data/caddy_config`
- `/srv/headscale/backups`

## Files

- `install.sh`: Ubuntu-first bootstrap for the Headscale VPS
- `docker-compose.yml`: canonical Headscale + Caddy stack
- `env.example`: env template copied to `/srv/headscale/.env`
- `Caddyfile`: public HTTPS front door for `hs.creatempls.org`
- `config.yaml.example`: minimal Headscale config template
- `policy.hujson.example`: narrow ACL/tag policy starting point
- `backup.sh`: one-command backup bundle creator
- `restore.sh`: one-command restore helper for a replacement VPS
- `classhub-headscale.service`: systemd wrapper for the Headscale Compose stack
- `classhub-headscale-backup.service`: systemd wrapper for periodic backups
- `classhub-headscale-backup.timer`: daily backup timer
- `../../scripts/headscale_restore_rehearsal_evidence.sh`: replacement-host rehearsal wrapper that captures recovery evidence artifacts

## Fresh bootstrap

On a fresh Ubuntu VPS with the repo already present:

```bash
cd /srv/headscale/app
sudo bash ops/headscale/install.sh
```

Then fill the runtime config:

```bash
sudo cp /srv/headscale/.env.example /srv/headscale/.env
sudo cp /srv/headscale/config/config.yaml.example /srv/headscale/config/config.yaml
sudo cp /srv/headscale/config/policy.hujson.example /srv/headscale/config/policy.hujson
sudoedit /srv/headscale/.env
sudoedit /srv/headscale/config/config.yaml
sudoedit /srv/headscale/config/policy.hujson
```

Then start the stack:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now classhub-headscale
```

## First verification

From the Headscale VPS:

```bash
sudo systemctl status classhub-headscale --no-pager
cd /srv/headscale
docker compose ps
curl -fsS http://127.0.0.1:9090/metrics >/dev/null
```

Optional CLI checks from inside the container:

```bash
cd /srv/headscale
docker compose exec headscale headscale users list
docker compose exec headscale headscale preauthkeys list
```

## Backups

Manual backup:

```bash
sudo /usr/local/bin/classhub-headscale-backup --headscale-root /srv/headscale
```

Enable periodic backups:

```bash
sudo systemctl enable --now classhub-headscale-backup.timer
sudo systemctl status classhub-headscale-backup.timer --no-pager
```

What the backup includes:

- `.env`
- `docker-compose.yml`
- `Caddyfile`
- `config/config.yaml`
- `config/policy.hujson`
- `data/lib`
- `data/caddy_data`
- `data/caddy_config`

Backups land under:

- `/srv/headscale/backups`

Keep a copy off the VPS as well.

## Restore onto a replacement VPS

Bootstrap the replacement host first:

```bash
cd /srv/headscale/app
sudo bash ops/headscale/install.sh
```

Then restore the latest backup:

```bash
sudo /usr/local/bin/classhub-headscale-restore \
  --headscale-root /srv/headscale \
  --backup /srv/headscale/backups/headscale_<STAMP>.tgz \
  --start-stack
```

Verify after restore:

```bash
sudo systemctl status classhub-headscale --no-pager
cd /srv/headscale
docker compose ps
curl -fsS http://127.0.0.1:9090/metrics >/dev/null
```

Then verify node membership and helper path from the LMS host:

```bash
cd /srv/lms/app
bash scripts/check_llm_backend.sh --probe-chat
```

## Replacement-host rehearsal wrapper

When you want evidence instead of just a successful shell session, use the repo wrapper:

```bash
cd /srv/headscale/app
sudo bash scripts/headscale_restore_rehearsal_evidence.sh \
  --backup /srv/headscale/backups/headscale_<STAMP>.tgz \
  --host-class replacement-host \
  --host-label hs-replacement-01
```

Default artifact location:

- `artifacts/stability/<date>/headscale_restore_rehearsal/<timestamp>/`

What the wrapper captures automatically on the Headscale VPS:

- bootstrap/install output when not skipped
- restore output
- `systemctl status classhub-headscale --no-pager`
- `systemctl status classhub-headscale-backup.timer --no-pager`
- `docker compose ps`
- a small `http://127.0.0.1:9090/metrics` sample
- compose logs
- `headscale nodes list`

What still needs operator review:

- LMS-host helper probe output (`bash scripts/check_llm_backend.sh --probe-chat`)
- confirmation that the LMS host and private model host rejoined cleanly
- optional model-host local checks when the LMS helper probe fails

## Recovery expectations

Recovery should not require improvisation.

The intended sequence is:

1. bootstrap replacement VPS
2. restore one archived Headscale bundle
3. start the stack
4. verify metrics + container state
5. verify LMS-to-helper private path from the LMS host

If recovery requires custom shell surgery, the bundle is incomplete and should be improved.

## What stays intentionally manual

The repo does not make the app depend on Headscale internals.

Still manual and operator-reviewed:

- actual node enrollment
- preauth key creation and rotation
- policy review before widening tailnet membership
- hostname/DNS ownership for `hs.creatempls.org`

## Related docs

- `docs/HEADSCALE_CONTROL_PLANE.md`
- `docs/PRIVATE_LLM_BACKEND.md`
- `docs/RUNBOOK.md`
- `ops/llm-server/README.md`
