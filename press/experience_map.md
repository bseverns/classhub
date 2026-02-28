# Press Experience Map

## Summary
This page maps how different audiences experience ClassHub so external materials can describe the product accurately without overselling.

## Experience matrix
| Audience | Entry point | Primary workflow | Screenshot anchors |
| --- | --- | --- | --- |
| Student (all cohorts) | `/` join form | Join with class code + display name, then open `/student` landing (`This week`, `Course links`, `Account`) | `01-student-join.png`, `02-student-class-view.png` |
| Student (elementary profile) | `/student` + `/course/*` | Compact-density copy/layout, helper collapsed by default, reduced on-screen complexity | `14-student-compact-view.png`, `15-lesson-helper-collapsed.png` |
| Student (secondary/advanced profiles) | `/student` + `/course/*` | Standard/expanded density, richer context and guidance text, same privacy boundaries | `16-student-standard-view.png`, `17-student-expanded-view.png` |
| Teacher | `/teach` and `/teach/class/<id>` | Manage classes, lesson release timing, invite links, roster, submissions, landing-page content | `03-teacher-dashboard.png`, `04-teacher-lesson-tracker.png`, `11-invite-only-enrollment.png`, `18-teacher-landing-editor.png` |
| Teacher (reporting) | `/teach/class/<id>` reporting actions | Export outcomes and certificates, issue signed certificates, share parent/funder-facing proof | `12-certificate-eligibility.png` |
| Superuser | `/teach` organizations tab | Create organizations, set memberships/roles, enforce staff boundaries | `10-org-management-tab.png` |
| Operator / maintainer | shell + health endpoints | Health checks, a11y smoke, deploy/runbook workflows | `08-health-checks-terminal.png`, `13-a11y-smoke-terminal.png` |

## Narrative paths for external audiences
1. **Classroom path**: student joins quickly, sees the weekly launch point, completes lesson + submission, teacher reviews.
2. **Program operations path**: teacher configures enrollment mode and invite links, manages roster, monitors helper-access signals.
3. **Reporting path**: outcomes/certificates create exportable artifacts without helper prompt archives or surveillance analytics.
4. **Reliability path**: operator validates health and accessibility checks using documented runbooks.

## Scope guardrails for press language
- Describe verified workflows, not roadmap ideas.
- Avoid claims implying AI transcript retention or student surveillance.
- Treat UI density as presentation tuning only (`compact` / `standard` / `expanded`), not a permissions model.

## Source-of-truth references
- `docs/PUBLIC_OVERVIEW.md`
- `docs/PROGRAM_PROFILES.md`
- `docs/TEACHER_PORTAL.md`
- `press/screenshots/SHOTLIST.md`
