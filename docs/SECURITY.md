# Security notes (MVP)

- Student accounts are pseudonymous (class-code + display name).
- Teacher/admin uses Django auth (password).
- Keep `DJANGO_SECRET_KEY` secret.
- Use HTTPS in production.
- Rate limit join + helper endpoints.

## Future
- Google SSO for teachers
- Audit logs for teacher/admin actions
- Separate DBs per service if needed
