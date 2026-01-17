# Security notes (MVP)

- Student accounts are pseudonymous (class-code + display name).
- Teacher/admin uses Django auth (password).
- Keep `DJANGO_SECRET_KEY` secret.
- Use HTTPS in production.
- Rate limit join + helper endpoints.

## Student submissions (uploads)

- Uploads are stored on the server under `data/classhub_uploads/`.
- Uploads are **not** served as public `/media/*` URLs.
  - Students download only their own files via `/submission/<id>/download`.
  - Staff/admin can download any submission.
- Decide on a retention policy (e.g. delete uploads after N days) if you are working
  in higher-risk environments.

## Future
- Google SSO for teachers
- Audit logs for teacher/admin actions
- Separate DBs per service if needed
