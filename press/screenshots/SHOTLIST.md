# Screenshot Shot List

## Summary
Use this list to capture consistent, privacy-safe screenshots for public sharing and future technical talks.

## What to do now
1. Capture each target file below.
2. Use demo data only (no real student names/emails/class codes).
3. Blur or redact any sensitive identifiers before publishing.

## Verification signal
When complete, `press/screenshots/` contains all filenames in this list and each image can be mapped to one product workflow.

## Conference demo spine

Recommended talk/demo order using the existing captures:

1. `01-student-join.png`: public classroom entry stays simple.
2. `03-teacher-dashboard.png`: teacher workflow is operational, not AI-first.
3. `11-invite-only-enrollment.png`: class-level controls include bounded staff-only remote helper compute.
4. `08-health-checks-terminal.png`: boring infra checks exist.
5. `20-data-lifespan-evidence.png` and `21-data-lifespan-export-terminal.png`: evidence/export posture is real, not rhetorical.

If you need a spoken architecture moment, pair this shotlist with:

- `press/architecture.md`
- `press/conference_packet.md`
- `press/failure_degradation_matrix.md`

## Capture targets
1. `01-student-join.png`
- Screen: homepage join form (`/`)
- Include: class code field + display name field
- Redact: any real class code

2. `02-student-class-view.png`
- Screen: student class page (`/student`)
- Include: class landing sections (`This week`, `Course links`, `Account`)
- Include: one open module + one collapsed module
- Redact: return codes

3. `03-teacher-dashboard.png`
- Screen: teacher home (`/teach`)
- Include: class cards and closeout actions
- Include: support-board signal summary if visible (unresolved “I'm stuck”, upload errors, deletion requests)
- Redact: real staff emails

4. `04-teacher-lesson-tracker.png`
- Screen: lessons view (`/teach/lessons`)
- Include: release controls and row actions
- Redact: real class names if needed

5. `05-lesson-with-helper.png`
- Screen: lesson page with helper panel visible
- Include: lesson section + helper opened from collapsed state
- Redact: student-specific text

6. `06-submission-dropbox.png`
- Screen: upload/dropbox flow
- Include: accepted file types, submit action, and simplified status pill (`Done` or `Open`)
- Include: student publish toggle state and resulting moderation status copy
- Redact: filenames if they include personal info

7. `07-admin-login.png`
- Screen: `/admin/login/`
- Include: login page only
- Redact: usernames in autofill

8. `08-health-checks-terminal.png`
- Screen: terminal running health checks
- Include: `/healthz` and `/helper/healthz` responses
- Redact: hostnames/IPs for non-local environments

## Additional capture targets (new features)
9. `09-teacher-profile-tab.png`
- Screen: teacher home (`/teach`) profile tab
- Include: profile details form + password change form
- Redact: real personal emails/usernames

10. `10-org-management-tab.png`
- Screen: teacher home (`/teach`) organizations tab (superuser)
- Include: organization create/rename controls + archive/restore actions + class-move form + memberships table row actions
- Redact: real organization names/emails if needed

11. `11-invite-only-enrollment.png`
- Screen: class dashboard (`/teach/class/<id>`)
- Include: enrollment mode controls + invite-link management
- Include: remote helper compute panel if the bounded staff-only control is enabled for the environment
- Include: visible state / expiry copy and JSON/CSV export affordance if present
- Include: support-board lane (or section) showing unresolved help signals
- Redact: live invite tokens/class codes

12. `12-certificate-eligibility.png`
- Screen: certificate eligibility page (`/teach/class/<id>/certificate-eligibility`)
- Include: eligibility table and issue/download actions
- Redact: real student names if needed

13. `13-a11y-smoke-terminal.png`
- Screen: terminal running `scripts/a11y_smoke.sh`
- Include: pass/fail summary lines
- Redact: hostnames/IPs if non-local

14. `14-student-compact-view.png`
- Screen: student class page (`/student`) in `compact` density mode
- Include: shortened copy, reduced helper/form emphasis, clear `This week` launch action
- Redact: return codes and student-specific text

15. `15-lesson-helper-collapsed.png`
- Screen: lesson page (`/course/...`) before opening helper
- Include: helper affordance in collapsed state plus lesson context
- Redact: student-specific content

16. `16-student-standard-view.png`
- Screen: student class page (`/student`) in `standard` density mode
- Include: default balance of copy and controls
- Redact: return codes

17. `17-student-expanded-view.png`
- Screen: student class page (`/student`) in `expanded` density mode
- Include: richer instructional/context copy with same core action path
- Redact: return codes

18. `18-teacher-landing-editor.png`
- Screen: teacher class page (`/teach/class/<id>`) landing-page editor
- Include: title/message/hero-url fields + save action
- Redact: real class names and real external image URLs if needed

19. `19-rbac-tools-tab.png`
- Screen: teacher home (`/teach?advanced=1&portal_mode=policy`) RBAC tools tab
- Include: scoped grant upsert form + existing grants table + simulation result block
- Include: custom-role forms/tables (custom roles, capabilities, and assignments)
- Include: policy import/export area
- Include: pending policy change request queue when approval workflow is enabled
- Include: one explicit `allow` or `deny` scoped grant example
- Redact: real usernames, class names, and organization identifiers
- Baseline capture mode: `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=0` (default-state screenshot)
- Optional companion capture filename: `19-rbac-tools-tab-approval-on.png` with `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1`

20. `20-data-lifespan-evidence.png`
- Screen: data lifespan dashboard (`/teach/data-lifespan`)
- Include: retention trend table + export JSON/CSV controls + RAG posture panel
- Include: explicit curriculum-only boundary copy (`Student uploads and student PII are excluded...`)
- Include: if available in the same talk/demo environment, one operator-facing evidence panel or doc excerpt that reinforces “measured, exportable, bounded”
- Redact: any sensitive class/user labels shown in prune summaries

21. `21-data-lifespan-export-terminal.png`
- Screen: terminal export run
- Include: one `curl` command pulling `/teach/data-lifespan/export?format=json` and resulting file listing
- Redact: live domains/session cookie filenames/tokens

## Storyline overlays (capture inside existing files)
- Trust/data controls:
  - `01-student-join.png`: include privacy-at-a-glance block and trust link.
  - `02-student-class-view.png`: include `Account` area with `My Data` and `Trust notes` links.
- Help-first facilitation:
  - `03-teacher-dashboard.png` or `11-invite-only-enrollment.png`: include unresolved support-board signals.
- Gallery moderation:
  - `06-submission-dropbox.png`: include publish toggle + moderation state.
  - `11-invite-only-enrollment.png` (or equivalent class dashboard view): include teacher moderation controls/state if available.

## Priority order
- Capture with approval workflow OFF (`CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=0`) first, then optional refresh with workflow ON.
- Optional supplemental file for ON mode: `19-rbac-tools-tab-approval-on.png`.
- When remote helper compute is part of the talk, prefer showing the class dashboard in a state where the remote panel is visible but not leaking provider internals.
- Pending in current backlog:
  - `13-a11y-smoke-terminal.png`
  - `15-lesson-helper-collapsed.png`
  - `18-teacher-landing-editor.png`
  - `20-data-lifespan-evidence.png`
  - `21-data-lifespan-export-terminal.png`

## Placeholders
- If these new screenshots are not captured yet, keep placeholders in
  `press/screenshots/PLACEHOLDERS.md` and avoid broken image links in docs until files exist.
