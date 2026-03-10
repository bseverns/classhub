# Turnover Drill Log

Use this as the canonical evidence log for Issue 10 / Risk R5 turnover survivability drills.

Last updated: March 10, 2026

## Drill Scope

Each drill should exercise both paths:
- 60-minute safe takeover path from [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
- first-day confidence path from [TURNOVER_PACKET.md](TURNOVER_PACKET.md)

## Run Commands (minimum)

Run from `/srv/lms/app`:

```bash
bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden
bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical
bash scripts/restore_rehearsal_evidence.sh --compose-mode prod --out-dir artifacts/stability/$(date +%F)
bash scripts/retention_health_snapshot.sh --compose-mode prod --out artifacts/stability/$(date +%F)/retention_health.log
```

## Evidence Record Template

Add one row per drill.

| Drill date | Operator(s) | 60-minute path result | first-day path result | Independent run without coaching? | Key blockers found | Docs patched same day? | Evidence directory | Next drill date | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-10 | ben | FAIL | FAIL | no | Backup-maintainer drill not yet executed end-to-end for this cycle; closeout evidence is complete, but final sign-off remains open until this drill is run and documented. | no | `artifacts/stability/2026-03-10/` | 2026-03-17 | Tracking row keeps the remaining R5 turnover blocker explicit after telemetry closeout passed. |
| YYYY-MM-DD | names | PASS/FAIL | PASS/FAIL | yes/no | short list | yes/no | `artifacts/stability/<date>/` | YYYY-MM-DD | drill summary |

## Acceptance Rule

A turnover drill is complete only when:
- both 60-minute and first-day paths are exercised,
- blockers are recorded,
- doc updates are made for blockers (or follow-up tickets are linked),
- next drill date is explicitly set.

## Related docs

- [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)
