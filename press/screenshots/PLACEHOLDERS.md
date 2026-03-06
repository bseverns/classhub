# Screenshot Placeholders

## Summary
This file tracks screenshot work that is either still placeholder-only or captured but queued for refresh.

## What to do now
1. Capture each target in a demo environment.
2. Save with the exact filename below in `press/screenshots/`.
3. Copy finalized images into `docs/images/press/` when public docs should display them.

## Verification signal
Each placeholder entry below has a `.png` present in both screenshot folders:
- `press/screenshots/`
- `docs/images/press/`

During planning, these may be generated placeholder images. Replace them with real captures before external publication.

## Refresh captures (real screenshot exists)
- `02-student-class-view.png` (refresh capture to show current landing structure)
- `05-lesson-with-helper.png` (refresh capture to show helper collapsed/open behavior)
- `06-submission-dropbox.png` (refresh capture for simplified status copy)

## Placeholder-to-capture backlog
1. `11-invite-only-enrollment.png` (must show invite controls + support-board unresolved signals)
2. `12-certificate-eligibility.png`
3. `14-student-compact-view.png`
4. `16-student-standard-view.png`
5. `17-student-expanded-view.png`
6. `18-teacher-landing-editor.png`
7. `10-org-management-tab.png` (refresh target should include rename/archive controls, class-org move, and inline membership actions)
8. `09-teacher-profile-tab.png`
9. `15-lesson-helper-collapsed.png`
10. `13-a11y-smoke-terminal.png`
11. `19-rbac-tools-tab.png` (refresh target should include custom-role tooling + policy change request queue)
12. `19-rbac-tools-tab-approval-on.png` (optional RBAC companion capture with `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1`)
13. `20-data-lifespan-evidence.png` (retention trend + export controls + RAG panel with curriculum-only statement)
14. `21-data-lifespan-export-terminal.png` (headless JSON export command + resulting artifact)

## Storyline-critical refresh guidance
- `02-student-class-view.png`: include account links for trust/data controls.
- `06-submission-dropbox.png`: include publish toggle + moderation state copy.
- `19-rbac-tools-tab.png`: keep baseline default-state screenshot with approval workflow OFF.
- `19-rbac-tools-tab-approval-on.png` (optional): show queued change requests and review controls with approval workflow ON.

## Notes
- Do not use production or real student/staff data.
- Prefer local/demo class names and clearly synthetic emails.
- Keep visual style consistent with existing screenshot set (browser width, zoom, and crop).
