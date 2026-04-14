# Incident Response

## Summary
This is the small-team incident guide for ClassHub. Use it when something may have affected service availability, data integrity, account access, or the privacy boundary of the system.

## What to do now
1. Decide whether this is an outage, a data/integrity problem, or a possible security/privacy incident.
2. Stabilize the system before improvising fixes.
3. Preserve evidence early, then communicate clearly to the people who need to know.

## Verification signal
An operator should be able to open this page and answer: who owns the response, what evidence to save first, and when leadership or partner consultation is required.

## Keep it proportionate

This project is built for nonprofits and small operators. Incident response here should be calm, documented, and real. It should not become enterprise theater.

Use this guide for:
- service outages that affect classes,
- suspicious staff-account activity,
- possible exposure of sensitive data or secrets,
- data corruption or restore decisions,
- any event that may require leadership, partner, or legal review.

## 1. Preparation

Before an incident:
- keep owner and backup-owner names current in [TOOL_CHARTER.md](TOOL_CHARTER.md),
- know who can make deploy, rollback, and restore decisions,
- keep backups and restore rehearsal current,
- know where deploy logs, app logs, and reverse-proxy logs live,
- keep partner/leadership contacts written down outside chat memory.

Supporting docs:
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [SECRET_ROTATION.md](SECRET_ROTATION.md)

## 2. Detection and analysis

Start by answering:
- What happened?
- When did it start?
- Is class use blocked right now?
- Is this availability only, or does it involve data/privacy/integrity risk?

Initial checks:
- `/healthz`
- `/helper/healthz`
- current deploy or reverse-proxy logs
- recent auth/account changes
- recent configuration changes
- recent restore, migration, or release actions

Classify the event:
- `Availability`: the site/helper is down or degraded.
- `Integrity`: data may be wrong, missing, or inconsistent.
- `Privacy/Security`: secrets, account misuse, or unexpected data exposure may be involved.

## 3. Containment and recovery

Use the smallest action that reduces harm:
- pause risky writes if needed,
- move to a safer site mode if that reduces impact,
- disable a compromised account or rotate a compromised token,
- roll back a bad deploy when the change is clearly causal,
- restore only after you have evidence that restore is the right move.

Guidance:
- Do not destroy evidence while trying to recover.
- Do not delete logs "to clean things up."
- Do not restore production first when you can validate a restore in a safe workspace.
- If student privacy may be affected, slow down and treat communication as part of the response, not an afterthought.

## 4. Who to notify

Always notify:
- the primary tool owner,
- the backup owner or operational second,
- the staff member running the affected class or cohort.

Notify leadership or partner contacts when:
- class delivery is materially affected,
- a restore or rollback will change what users see,
- a partner-hosted deployment or district relationship may be involved,
- privacy, records, or contractual questions are in play.

Notify legal or partner counsel when:
- there is a plausible data exposure,
- contractual notice obligations may apply,
- law-enforcement or regulator contact is being considered,
- you are unsure whether a privacy/security event requires formal notice.

This page is not legal advice.

## 5. Evidence to preserve

Preserve first:
- timeline of what was observed and by whom,
- relevant app and proxy logs,
- release/deploy identifier or commit SHA,
- current env/profile information that may explain behavior,
- affected URLs, class IDs, org IDs, and account IDs,
- screenshots only when they add information not present in logs,
- backup/restore artifacts if recovery is being considered.

For suspected security/privacy incidents also preserve:
- token rotation decisions and timestamps,
- account-disable / password-reset actions,
- any indicators of unexpected IPs, sessions, or admin actions.

Keep evidence bounded:
- do not export unrelated student data "just in case,"
- do not circulate raw logs broadly if they contain sensitive operational details.

## 6. Post-incident review

After the system is stable:
- write a short factual timeline,
- record the root cause or most likely cause,
- record what was changed to recover,
- record what follow-up guardrail or docs fix is needed,
- update [DECISIONS.md](DECISIONS.md) when the incident changed a standing practice or control.

Good post-incident questions:
- What signal should have told us sooner?
- What manual step was too implicit?
- What doc or runbook was missing or hard to find?
- What should be automated next time?

## Related docs

- Operator runbook: [RUNBOOK.md](RUNBOOK.md)
- Security posture: [SECURITY.md](SECURITY.md)
- Disaster recovery: [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- Secret rotation: [SECRET_ROTATION.md](SECRET_ROTATION.md)
- Tool ownership and support boundary: [TOOL_CHARTER.md](TOOL_CHARTER.md)
