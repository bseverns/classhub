# Runbook

## Start / stop

```bash
cd /srv/classhub/compose
docker compose up -d
# stop:
docker compose down
```

## Logs

```bash
docker compose logs -f --tail=200 classhub_web
```

## Backups

- `scripts/backup_postgres.sh`
- `scripts/backup_minio.sh`

## Restore drill (recommended)

- Restore Postgres dump into a temporary DB
- Confirm Django can migrate and start
