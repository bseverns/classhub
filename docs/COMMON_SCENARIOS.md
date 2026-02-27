# Common Scenarios

Use these short playbooks when a normal class day turns into an ops problem.

## Student lost return code

1. Confirm the student is in the correct `Class`.
2. Verify the student can still use the class code or active `Invite link` if re-entry is allowed.
3. If you need to look up the student, use their `display_name` within the class context rather than asking for extra personal data.
4. If the class is `Invite only`, confirm the invite is still valid before troubleshooting anything else.
5. If the issue persists, escalate to ops and verify the session/cookie host is correct.

See also: [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Invite link full or expired

1. Open the class in `/teach`.
2. Check whether the class is set to `Invite only`.
3. Review the relevant invite's expiration and seat cap.
4. Create a fresh `Invite link` or raise the cap if policy allows.
5. Re-send only the new link so students do not keep retrying a dead one.

See also: [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Staff member leaves

1. Remove or deactivate their organization membership.
2. Reassign any classes that depend on them as the visible staff owner.
3. Review whether their account should remain active for audit/history or be disabled entirely.
4. If handoff is needed, use a documented teacher handoff process instead of informal password sharing.

See also: [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [TEACHER_HANDOFF_CHECKLIST.md](TEACHER_HANDOFF_CHECKLIST.md), [SECURITY.md](SECURITY.md)

## Org boundary confusion

1. Confirm which `Organization` owns the class.
2. Confirm whether the staff user has an active org membership.
3. Check whether `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` is enforcing a hard boundary in this deployment.
4. If the staff member should have access, fix the org membership instead of sharing a broader account.
5. If the staff member should not have access, leave the boundary intact and document the request.

See also: [SECURITY.md](SECURITY.md), [TEACHER_PORTAL.md](TEACHER_PORTAL.md)

## Helper offline

1. Confirm whether the helper service is down or whether the issue is specific to one browser/session.
2. Keep class moving: students can continue with class materials and submissions even if helper access is unavailable.
3. Notify ops with time, class, and visible error.
4. Do not promise that helper prompts are recoverable later; prompt content is intentionally not a reporting archive.
5. Use normal troubleshooting or smoke checks before escalating to restore/redeploy work.

See also: [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [RUNBOOK.md](RUNBOOK.md), [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md)

## Restore rehearsal when something breaks

1. First decide whether this is a service outage, bad configuration, or actual data-loss event.
2. If data integrity is in question, stop improvising and follow the documented recovery path.
3. Check the latest backup status and restore-rehearsal notes.
4. Use the recovery procedure to restore into a temporary workspace before touching production data.
5. Verify the restored state, then decide whether production restore is actually necessary.

See also: [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md), [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
