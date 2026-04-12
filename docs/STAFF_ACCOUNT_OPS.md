# Staff Account Operations (System Administrators)

This guide documents the technical procedures for creating and managing staff/teacher accounts via the deployment terminal.

> [!NOTE]
> This guide is intended for server ops. For the general Teacher Navigation Guide, see [TEACHER_PORTAL.md](TEACHER_PORTAL.md).

## Create teacher accounts

Prerequisite: stack is running.

```bash
cd compose
docker compose up -d
```

Create first admin (if needed):

```bash
cd compose
docker compose exec classhub_web python manage.py createsuperuser
```

Create a staff teacher account:

```bash
cd compose
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher1 \
  --email teacher1@example.org \
  --password CHANGE_ME
```

Reset a teacher password:

```bash
cd compose
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher1 \
  --password NEW_PASSWORD \
  --update
```

Disable teacher access without deleting account:

```bash
cd compose
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher1 \
  --inactive \
  --update
```

Useful flags:
- `--update`: required when modifying an existing teacher.
- `--clear-email`: clear existing email on update.
- `--superuser` / `--no-superuser`: elevate or remove admin-level access.
- `--active` / `--inactive`: explicitly control account state.

## Changing personnel (new or different teachers)

Operational handoff scripts:

```bash
# 1) onboard new teacher
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher2 \
  --email teacher2@example.org \
  --password TEMP_PASSWORD

# 2) rotate their password after first login or handoff
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher2 \
  --password FINAL_PASSWORD \
  --update

# 3) offboard previous teacher account
docker compose exec classhub_web python manage.py create_teacher \
  --username teacher1 \
  --inactive \
  --update
```

Operational checklist can be found in [TEACHER_HANDOFF_CHECKLIST.md](TEACHER_HANDOFF_CHECKLIST.md).
