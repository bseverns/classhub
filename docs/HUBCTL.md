# hubctl (Facilitator CLI)

## Summary
`hubctl` is a terminal-first operator client for the existing teacher API (`/api/v1/teacher/*`).
It is intended for fast class controls without opening `/teach` in a browser.

## What to do now
1. Create a staff session with `auth login`.
2. Run `classes list` to confirm visibility.
3. Use `class lock|unlock|rotate-code|set-enrollment` for live operations.

## Verification signal
A teacher/admin can rotate a class join code from terminal in under 30 seconds while preserving existing RBAC boundaries.

## Command scope (MVP)
- `classes list`
- `class lock <id>`
- `class unlock <id>`
- `class rotate-code <id>`
- `class set-enrollment <id> <open|invite_only|closed>`
- `class roster <id>`
- `class submissions <id> --limit N --offset N`
- `auth login|check|logout`

## Run command
From repository root:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --base-url http://localhost auth login --username admin
```

If 2FA is required:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --base-url https://lms.example.org \
  auth login --username admin --otp-token 123456
```

List classes:

```bash
PYTHONPATH=tools/hubctl python -m hubctl classes list
```

Enable JSON output for automation:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --json class submissions 12 --limit 25
```

## Auth/session contract
- `hubctl` intentionally reuses existing teacher auth policy.
- Login path is `/teach/login` (Django session auth).
- If OTP verification is required, login completes through `/teach/2fa/setup`.
- No separate teacher bearer-token bypass exists.
- Session cookies persist at `~/.classhub/hubctl.cookies` by default.

## Exit codes
- `0`: success
- `2`: invalid CLI input
- `3`: authentication/session failure (includes OTP required)
- `4`: forbidden
- `5`: not found
- `6`: rate limited
- `7`: network/server failure

## Troubleshooting
- `ERROR: 2FA is required...`
  - Re-run `auth login` with `--otp-token`.
- `ERROR: Session is missing CSRF state...`
  - Run `auth login` again; the saved cookie jar may be stale.
- `ERROR: Network error while contacting ...`
  - Confirm `--base-url` and service health (`/healthz`).

## Related docs
- [API.md](API.md)
- [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- [RUNBOOK.md](RUNBOOK.md)
