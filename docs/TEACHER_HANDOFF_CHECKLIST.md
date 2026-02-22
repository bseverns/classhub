# Teacher Handoff Checklist

Use this checklist when teacher staffing changes (new teacher, replacement, or role change).

## 1) Prep

- Confirm you have admin access (`createsuperuser` account or equivalent).
- Confirm stack is running:

```bash
cd /srv/lms/compose
docker compose up -d
```

## 2) Create the incoming teacher account

```bash
cd /srv/lms/compose
docker compose exec classhub_web python manage.py create_teacher \
  --username new_teacher \
  --email new_teacher@example.org \
  --password TEMP_PASSWORD
```

Notes:
- Default behavior creates `is_staff=True`, `is_superuser=False`.
- This is preferred for daily teaching access.

## 3) Verify access with the incoming teacher

- Sign in via `/admin/login/`.
- Confirm they can open:
  - `/teach`
  - `/teach/lessons`
- Confirm they can open at least one class and submission queue.

## 4) Rotate password after handoff

```bash
cd /srv/lms/compose
docker compose exec classhub_web python manage.py create_teacher \
  --username new_teacher \
  --password FINAL_PASSWORD \
  --update
```

## 5) Offboard old teacher account

Disable old account (recommended instead of deleting):

```bash
cd /srv/lms/compose
docker compose exec classhub_web python manage.py create_teacher \
  --username old_teacher \
  --inactive \
  --update
```

## 6) Optional role changes

Promote to superuser only when needed:

```bash
cd /srv/lms/compose
docker compose exec classhub_web python manage.py create_teacher \
  --username new_teacher \
  --superuser \
  --update
```

Demote from superuser:

```bash
cd /srv/lms/compose
docker compose exec classhub_web python manage.py create_teacher \
  --username new_teacher \
  --no-superuser \
  --update
```

## 7) Recordkeeping

- Note who was onboarded/offboarded and when.
- Confirm old account can no longer log in.
- Store new credentials in your password manager.

## Quick links

- Teacher account guide: [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- Command cookbook script: `scripts/examples/teacher_accounts.sh`
- Handoff record template: [TEACHER_HANDOFF_RECORD_TEMPLATE.md](TEACHER_HANDOFF_RECORD_TEMPLATE.md)
