# Classroom Kiosk PWA

## Summary
ClassHub now includes an optional kiosk shell mode for student-facing routes.
When enabled, the shell focuses navigation on join, class home, and upload flows.

## What to do now
1. Enable kiosk shell in `compose/.env`:
   - `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED=1`
2. Redeploy ClassHub.
3. Open `/?kiosk=1` on the classroom device.
4. Install the app from browser UI (Add to Home Screen / Install App).

## Verification signal
With kiosk mode active, opening `/student/portfolio` redirects to `/student?kiosk=1` and student pages show only class-focused links.

## Flags
- `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED` (default `0`)
  - Master switch for kiosk shell behavior.
- `CLASSHUB_STUDENT_KIOSK_DEFAULT` (default `0`)
  - If `1`, kiosk mode is on by default unless explicitly toggled off (`?kiosk=0`).
- `CLASSHUB_STUDENT_KIOSK_COOKIE_MAX_AGE_SECONDS` (default `2592000`)
  - Persistence window for kiosk mode cookie (`classhub_student_kiosk_mode`).

## Kiosk mode toggle
- Enable: `/?kiosk=1` or `/student?kiosk=1`
- Disable: `/?kiosk=0` or `/student?kiosk=0`

## Student shell manifest + worker
- Manifest: `/student-shell.webmanifest`
- Service worker: `/student-upload-sync-sw.js`
- Templates include manifest link on:
  - `/` (join)
  - `/student`
  - `/material/<id>/upload`

## Route allowlist (when kiosk mode is active)
Allowed:
- `/`, `/join`, `/student`
- `/material/<id>/upload`
- `/student/return-code`, `/student/micro-check`
- `/student/submission/<id>/publish`
- `/submission/<id>/download`
- `/course/*`, `/lesson-video/*`, `/lesson-asset/*`
- `/api/v1/student/*`
- `/student-upload-sync-sw.js`, `/student-shell.webmanifest`
- `/privacy`, `/trust`, `/logout`

Non-allowlisted student routes redirect back to class home.

## Related docs
- [ECOSYSTEM_MILESTONES_PLAN.md](ECOSYSTEM_MILESTONES_PLAN.md)
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- [RUNBOOK.md](RUNBOOK.md)
