# Security

This page is the practical security baseline for this project.

If you only do three things before production:

1. set strong secrets and `DJANGO_DEBUG=0`
2. require TLS and 2FA for admin users
3. run `bash scripts/validate_env_secrets.sh`

## Security posture at a glance

| Area | Current posture |
|---|---|
| Student identity | Pseudonymous (`class code + display name`) |
| Teacher/admin auth | Django auth; admin OTP required by default |
| Transport | Caddy at edge; HTTPS expected in production |
| Service exposure | Postgres/Redis internal-only; Ollama/MinIO localhost-bound on host |
| Helper scope protection | Student helper calls require signed `scope_token` |
| Upload access | Not public `/media`; downloads are permission-checked views |
| Auditing | Staff mutations logged as immutable `AuditEvent` rows |

## Day-1 production checklist

1. Set `DJANGO_DEBUG=0`.
2. Set a strong `DJANGO_SECRET_KEY` (non-default, 32+ chars).
3. Enable HTTPS behavior for domain deployments:
   - `DJANGO_SECURE_SSL_REDIRECT=1`
   - `DJANGO_SECURE_HSTS_SECONDS` (recommend `>=31536000` after verification)
   - `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=1` only when all subdomains are HTTPS-ready
4. Keep `DJANGO_ADMIN_2FA_REQUIRED=1`.
5. Validate secrets and guardrails:
   - `bash scripts/validate_env_secrets.sh`
6. Confirm edge request size limits are set:
   - `CADDY_CLASSHUB_MAX_BODY`
   - `CADDY_HELPER_MAX_BODY`

## Authentication and authorization boundaries

- Students do not have passwords in MVP.
- Teachers should be `is_staff=True`, `is_superuser=False` for daily use.
- Superusers should be limited to operational tasks.
- Helper chat requires either:
  - valid student classroom session, or
  - authenticated staff session.
- Student helper requests must include a valid signed scope token.
- Staff can also be forced to require signed scope tokens:
  - `HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF=1`

Admin 2FA bootstrap command:

```bash
docker compose exec classhub_web python manage.py bootstrap_admin_otp --username <admin_username> --with-static-backup
```

## Network and proxy trust model

- Caddy is the public edge.
- Postgres and Redis are not published on host ports.
- Ollama and MinIO are bound to `127.0.0.1` on the host for local/admin access.
- Proxy header trust is explicit opt-in:
  - `REQUEST_SAFETY_TRUST_PROXY_HEADERS=0` by default
  - set to `1` only when your first-hop proxy is trusted and rewrites `X-Forwarded-*`.

## Data handling and retention

### Student submissions

- Stored under `data/classhub_uploads/`.
- Not served as public static media.
- Access is permission-checked (`/submission/<id>/download`).
- Files use randomized server-side names; original filename is metadata only.

Retention commands:

```bash
python manage.py prune_submissions --older-than-days <N>
python manage.py prune_student_events --older-than-days <N>
```

### Event logging

- `AuditEvent` logs staff actions in `/teach/*`.
- `StudentEvent` stores metadata (status/request IDs/timing) only.
- No raw helper prompt text and no file contents are stored in `StudentEvent.details`.

## Helper-specific controls

- Unsigned helper scope fields (`context/topics/allowed_topics/reference`) are ignored.
- Student helper session-table checks are configurable:
  - default: fail-open when classhub tables are unavailable
  - production hardening option: `HELPER_REQUIRE_CLASSHUB_TABLE=1` (fail-closed)
- Local LLM (`Ollama`) keeps inference on your infrastructure, but logs and prompt handling still require governance.

## Upload malware scanning (optional)

Enable command-based scanning (for example ClamAV):

- `CLASSHUB_UPLOAD_SCAN_ENABLED=1`
- `CLASSHUB_UPLOAD_SCAN_COMMAND` (example: `clamscan --no-summary --stdout`)
- `CLASSHUB_UPLOAD_SCAN_FAIL_CLOSED=1` to block uploads on scanner errors/timeouts

## Content security policy rollout

Use `DJANGO_CSP_REPORT_ONLY_POLICY` first, then enforce later.

Suggested rollout:

1. Start in report-only mode.
2. Review violations.
3. Tighten directives iteratively.
4. Enforce only after classroom pages are clean.

Starter example:

`DJANGO_CSP_REPORT_ONLY_POLICY=default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'`

## Future hardening candidates

- Google SSO for teacher accounts.
- Separate databases per service if isolation requirements increase.
