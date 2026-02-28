# Screenshot Shot List

## Summary
Use this list to capture consistent, privacy-safe screenshots for public sharing.

## What to do now
1. Capture each target file below.
2. Use demo data only (no real student names/emails/class codes).
3. Blur or redact any sensitive identifiers before publishing.

## Verification signal
When complete, `press/screenshots/` contains all filenames in this list and each image can be mapped to one product workflow.

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
- Include: organization create form + memberships table
- Redact: real organization names/emails if needed

11. `11-invite-only-enrollment.png`
- Screen: class dashboard (`/teach/class/<id>`)
- Include: enrollment mode controls + invite-link management
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

## Priority order (refresh first)
1. `02-student-class-view.png`
2. `05-lesson-with-helper.png`
3. `06-submission-dropbox.png`
4. `11-invite-only-enrollment.png`
5. `12-certificate-eligibility.png`
6. `14-student-compact-view.png`
7. `16-student-standard-view.png`
8. `17-student-expanded-view.png`

## Placeholders
- If these new screenshots are not captured yet, keep placeholders in
  `press/screenshots/PLACEHOLDERS.md` and avoid broken image links in docs until files exist.
