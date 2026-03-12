# Runtime Lock Profiles

Use this page to avoid mixing up two different contracts:

- **baseline profile**: safe/default runtime posture checks (for daily ops + example env files)
- **release profile**: strict closeout posture checks (for release-cycle evidence sign-off)

Last updated: March 11, 2026

## Why two profiles exist

`compose/.env.example.local` and `compose/.env.example.domain` are **deployment baseline examples**.  
They are not release-signoff files.

Release closeout requires stricter telemetry mode pairings and explicit lock values that may be applied only during closeout evidence runs.

## Profile matrix

| Profile | Intended use | Typical env file | Key expectation |
| --- | --- | --- | --- |
| `baseline` | Day-to-day operations, example env validation, operator sanity checks | `compose/.env`, `compose/.env.example.local`, `compose/.env.example.domain` | explicit boundary + telemetry + certificate values are present and coherent |
| `release` | Stability/release evidence closeout only | production `compose/.env` during closeout run | strict lock values required for sign-off |

## Commands

Baseline checks (examples + normal runtime):

```bash
python3 scripts/check_runtime_policy_lock.py --profile baseline --env-file compose/.env.example.local
python3 scripts/check_runtime_policy_lock.py --profile baseline --env-file compose/.env.example.domain
python3 scripts/check_runtime_policy_lock.py --profile baseline --env-file compose/.env
```

Release closeout check (strict):

```bash
python3 scripts/check_runtime_policy_lock.py --profile release --env-file compose/.env
```

Expected by design:

```bash
python3 scripts/check_runtime_policy_lock.py --profile release --env-file compose/.env.example.domain
```

The command above should fail because `compose/.env.example.domain` is a baseline deployment example (`off`/`core` telemetry), not a release-closeout lock state.

## Release-profile lock values

During closeout, the `release` profile expects:

- `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`
- `CLASSHUB_TELEMETRY_WRITE_MODE=dual`
- `CLASSHUB_TELEMETRY_READ_MODE=telemetry`
- explicit `CLASSHUB_CERTIFICATE_MIN_SESSIONS` (`>=1`)
- explicit `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS` (`>=1`)

## Operator guidance

- If `baseline` fails on an example env file: fix docs/example defaults.
- If `release` fails on production `compose/.env` during closeout: release sign-off is blocked until fixed.
- Do not treat `release` failures against `.env.example.*` as a bug; those files represent baseline deployment posture, not closeout posture.

## Related docs

- [RUNBOOK.md](RUNBOOK.md)
- [RELEASING.md](RELEASING.md)
- [MINIMUM_VIABLE_OPERATOR.md](MINIMUM_VIABLE_OPERATOR.md)
- [DECISIONS.md](DECISIONS.md)
