# Press Experience Map

## Summary
This page maps how different audiences experience ClassHub so external materials can describe the product accurately without overselling.

## Experience matrix
| Audience | Entry point | Primary workflow | Screenshot anchors |
| --- | --- | --- | --- |
| Student (all cohorts) | `/` join form | Join with class code + display name, then open `/student` landing (`This week`, `Course links`, `Account`) | `01-student-join.png`, `02-student-class-view.png` |
| Student (trust + data controls) | `/trust` and `/student/my-data` | Read plain-language “what we store/never store”, then rename/export/delete/request deletion controls | `01-student-join.png`, `02-student-class-view.png` |
| Student (artifact-first) | `/student/portfolio` and `/student/gallery` | Review personal “What I made” history, choose opt-in publish per artifact, view only approved gallery entries | `06-submission-dropbox.png`, `15-lesson-helper-collapsed.png` |
| Student (elementary profile) | `/student` + `/course/*` | Compact-density copy/layout, helper collapsed by default, reduced on-screen complexity | `14-student-compact-view.png`, `15-lesson-helper-collapsed.png` |
| Student (secondary/advanced profiles) | `/student` + `/course/*` | Standard/expanded density, richer context and guidance text, same privacy boundaries | `16-student-standard-view.png`, `17-student-expanded-view.png` |
| Teacher | `/teach` and `/teach/class/<id>` | Manage classes, lesson release timing, invite links, roster, submissions, landing-page content | `03-teacher-dashboard.png`, `04-teacher-lesson-tracker.png`, `11-invite-only-enrollment.png`, `18-teacher-landing-editor.png` |
| Teacher (help-first facilitation) | `/teach/class/<id>` support board | Prioritize unresolved “I’m stuck” signals, review upload errors, resolve support requests without ranking students | `03-teacher-dashboard.png`, `04-teacher-lesson-tracker.png` |
| Teacher (reporting) | `/teach/class/<id>` reporting actions | Export outcomes and certificates, issue signed certificates, share parent/funder-facing proof | `12-certificate-eligibility.png` |
| Superuser | `/teach` organizations tab | Create organizations, set memberships/roles, enforce staff boundaries | `10-org-management-tab.png` |
| Operator / maintainer | shell + health endpoints | Health checks, a11y smoke, deploy/runbook workflows | `08-health-checks-terminal.png`, `13-a11y-smoke-terminal.png` |

## Narrative paths for external audiences
1. **Classroom path**: student joins quickly, sees the weekly launch point, completes lesson + submission, teacher reviews.
2. **Trust path**: student/family can read `/trust` and use `/student/my-data` without support tickets.
3. **Artifact path**: student portfolio is personal by default; gallery visibility requires explicit publish + teacher approval.
4. **Program operations path**: teacher configures enrollment mode and invite links, manages roster, and works from help-first facilitator signals.
5. **Reliability path**: operator validates health and accessibility checks using documented runbooks.

## Scope guardrails for press language
- Describe verified workflows, not roadmap ideas.
- Avoid claims implying AI transcript retention or student surveillance.
- Treat UI density as presentation tuning only (`compact` / `standard` / `expanded`), not a permissions model.
- Treat student artifact sharing as teacher-only by default unless student opt-in + teacher approval are both present.

## Source-of-truth references
- `docs/PUBLIC_OVERVIEW.md`
- `docs/PROGRAM_PROFILES.md`
- `docs/TEACHER_PORTAL.md`
- `press/screenshots/SHOTLIST.md`
