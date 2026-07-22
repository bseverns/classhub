# Screenshot Placeholders

## Summary
This file tracks screenshot backlog state after the 2026-07-21 browser refresh and the 2026-04-14 terminal closeout pass.

## Backlog governance
- Owner: Maintainer (repo-level accountability for press capture closeout)
- Target closeout date: 2026-04-30
- Maximum allowed backlog size: 5 items
- Review cadence: confirm status in each release-cycle docs sweep

## What to do now
1. Keep this file as the single place to record any future screenshot drift or missing assets.
2. Save new or refreshed files with the exact filename in `press/screenshots/`.
3. Copy finalized public images into `docs/images/press/`.

## Verification signal
Every filename listed in backlog has a clear owner and can be validated as captured or refreshed in both screenshot folders:
- `press/screenshots/`
- `docs/images/press/`

## Capture backlog
No pending captures.

## Storyline-critical refresh guidance
- If a future audit finds blank, stale, or missing public assets, add them back here with the exact filename and the minimum recapture note needed to reproduce the shot.

## Notes
- Public screenshot set is complete through `21`, plus optional companion `19-rbac-tools-tab-approval-on.png`, in both screenshot folders.
- Browser captures `01`–`06`, `09`–`11`, and `14`–`20` were refreshed on 2026-07-21 from the local deterministic demo fixture at 1400 px width; the matching capture manifest is tracked under `scripts/a11y/artifacts/press_capture_fullpage/`.
- Browser captures `07` and `12`, plus terminal captures `08`, `13`, and `21`, remain current from their prior evidence runs and were not regenerated during this refresh.
- The refreshed `20-data-lifespan-evidence.png` uses a local synthetic helper-status response so the curriculum-only RAG boundary is visible without connecting to production services.
- `13` and `21` returned to the public set after the 2026-04-14 terminal closeout pass.
- Do not use production or real student/staff data.
- Prefer local/demo class names and clearly synthetic emails.
- Keep visual style consistent with existing screenshot set (browser width, zoom, and crop).
