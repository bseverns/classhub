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

For unstable-network validation, run:

```bash
bash scripts/kiosk_resilience_check.sh --class-code <YOUR_SMOKE_CLASS_CODE>
```

This generates a timestamped report under `/tmp/classhub_kiosk_resilience_<timestamp>.md`.

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

## Tablet QA matrix

| Device/browser | Installability target | Required checks | Status |
|---|---|---|---|
| iPadOS Safari (latest stable) | Add to Home Screen succeeds from `/?kiosk=1` | Join -> class -> upload, offline queue, reconnect flush, relaunch behavior | Pending per deployment |
| Android tablet Chrome (latest stable) | Install App prompt available from `/?kiosk=1` | Join -> class -> upload, offline queue, reconnect flush, relaunch behavior | Pending per deployment |

## Unstable-network drill checklist
Use `bash scripts/kiosk_resilience_check.sh --class-code <CODE>` and record outcomes:
1. Confirm `/student-shell.webmanifest` and `/student-upload-sync-sw.js` checks pass.
2. Open kiosk mode and verify non-allowlisted routes redirect to class flow.
3. On upload page, force Offline in devtools and submit a small file.
4. Verify queued-upload status message appears and session remains usable.
5. Restore Online and confirm queue flushes automatically or via retry button.
6. Confirm uploaded file appears in `Your uploads` after reconnect.
7. Relaunch installed app and verify join/class/upload flows still function.

## Related docs
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- [RUNBOOK.md](RUNBOOK.md)
