# hubctl (Facilitator CLI)

`hubctl` is a terminal-first client for ClassHub teacher/admin actions.

## What it supports now
- `classes list`
- `class lock <id>` / `class unlock <id>`
- `class rotate-code <id>`
- `class set-enrollment <id> <open|invite_only|closed>`
- `class roster <id>`
- `class submissions <id> --limit N --offset N`
- `auth login|check|logout`

## Run it

From repo root:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --base-url http://localhost auth login --username admin
```

If your deployment enforces teacher 2FA, include OTP code:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --base-url https://lms.example.org \
  auth login --username admin --otp-token 123456
```

List classes:

```bash
PYTHONPATH=tools/hubctl python -m hubctl classes list
```

Machine-readable output:

```bash
PYTHONPATH=tools/hubctl python -m hubctl --json class submissions 12 --limit 25
```

## Session + auth contract
- Uses the same Django session flow as `/teach/login` (no bypass token flow).
- If OTP is required, `auth login` must complete `/teach/2fa/setup` verification.
- Session cookies are stored in `~/.classhub/hubctl.cookies` by default.
- Override with `--session-file` or `HUBCTL_SESSION_FILE`.

## Exit codes
- `0`: success
- `2`: bad CLI input
- `3`: auth/session issue (unauthorized, OTP required)
- `4`: permission denied
- `5`: resource not found
- `6`: rate limited
- `7`: network/server failure
