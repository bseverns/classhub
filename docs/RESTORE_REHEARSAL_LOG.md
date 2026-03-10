# Restore Rehearsal Log

Use this as the canonical evidence log for Issue 8 / Risk R4 restore drills.

Last updated: March 10, 2026

## Run Command

Preferred command:

```bash
cd /srv/lms/app
bash scripts/restore_rehearsal_evidence.sh \
  --compose-mode prod \
  --out-dir artifacts/stability/$(date +%F)
```

This command writes:
- `restore_rehearsal.log`
- `restore_rehearsal_metrics.json`
- `restore_rehearsal_summary.md`
- `backups/checksums.sha256`

## Evidence Record Template

Add one row per rehearsal.

| Rehearsal date | Deployment | Operator(s) | Result | RTO seconds | RPO seconds | Thresholds (RTO/RPO) | Evidence directory | Next rehearsal date | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | prod | names | PASS/FAIL | N | N | `3600/900` | `artifacts/stability/<date>/` | YYYY-MM-DD | blockers/follow-up |

## Acceptance Rule

A quarterly rehearsal is complete only when:
- evidence artifacts are present for the run,
- one evidence row is added here,
- next rehearsal date is recorded.

## Related docs

- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)
- [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)
