# Screenshot Placeholders

## Summary
This file tracks remaining screenshot backlog and refresh items.

## Backlog governance
- Owner: Maintainer (repo-level accountability for press capture closeout)
- Target closeout date: 2026-04-30
- Maximum allowed backlog size: 5 items
- Review cadence: confirm status in each release-cycle docs sweep

## What to do now
1. Capture each target in a demo environment.
2. Save with the exact filename below in `press/screenshots/`.
3. Copy finalized images into `docs/images/press/` when public docs should display them.

## Verification signal
Every filename listed in backlog has a clear owner and can be validated as captured or refreshed in both screenshot folders:
- `press/screenshots/`
- `docs/images/press/`

## Capture backlog
1. `13-a11y-smoke-terminal.png` (refresh required: tracked public image is blank and must be recaptured from a real accessibility smoke run)
2. `15-lesson-helper-collapsed.png` (refresh required: tracked public image is blank and must be recaptured from the collapsed helper state)
3. `18-teacher-landing-editor.png` (refresh required: current tracked capture is blank and must be recaptured before public embedding)
4. `20-data-lifespan-evidence.png` (retention trend + export controls + RAG panel with curriculum-only statement)
5. `21-data-lifespan-export-terminal.png` (headless JSON export command + resulting artifact)

## Storyline-critical refresh guidance
- `02-student-class-view.png`: include account links for trust/data controls.
- `13-a11y-smoke-terminal.png`: capture the real `scripts/a11y_smoke.sh` terminal output, not a placeholder frame.
- `15-lesson-helper-collapsed.png`: capture the lesson page before opening helper, with the collapsed affordance visible.
- `06-submission-dropbox.png`: include publish toggle + moderation state copy.
- `18-teacher-landing-editor.png`: capture the actual landing-page editor fields; do not reuse the blank 2026-04-11 audit artifact.
- `19-rbac-tools-tab.png`: keep baseline default-state screenshot with approval workflow OFF.
- `19-rbac-tools-tab-approval-on.png` (optional): show queued change requests and review controls with approval workflow ON.

## Notes
- Baseline capture set `01` through `12`, `14`, `16`, `17`, and `19` is complete.
- `13`, `15`, and `18` moved back into refresh backlog after the 2026-04-11 machine audit found blank public assets.
- Do not use production or real student/staff data.
- Prefer local/demo class names and clearly synthetic emails.
- Keep visual style consistent with existing screenshot set (browser width, zoom, and crop).
