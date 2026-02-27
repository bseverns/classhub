# ClassHub Docs

ClassHub is a self-hosted, classroom-first LMS designed for real programming:
fast student join → lesson → submission → teacher review, with a quarantined Homework Helper behind `/helper/*`.

Evaluating for your org? Start with [Public Overview](PUBLIC_OVERVIEW.md) and [Try It Local](TRY_IT_LOCAL.md).

## Organization and place acknowledgment
- createMPLS is a Minneapolis-based 501(c)(3) nonprofit organization.
- Minneapolis is located on land ceded by treaty and has historically been home to the Anishinaabe, Dakota, and Oceti Sakowin peoples.

## Quick links
- [Start Here](START_HERE.md)
- [Executive Director Start Here](START_HERE_ED.md)
- [Ops Director Start Here](START_HERE_OD.md)
- [Fundraising Start Here](START_HERE_FUNDRAISING.md)
- [Instructor / Assistant Start Here](START_HERE_INSTRUCTOR.md)
- [Run a Class Tomorrow](RUN_A_CLASS_TOMORROW.md)
- [Risk & Data Posture](RISK_AND_DATA_POSTURE.md)
- [Program Lifecycle](PROGRAM_LIFECYCLE.md)
- [Things to Install First](START_HERE.md#things-you-need-to-install-first)
- [Public Overview](PUBLIC_OVERVIEW.md)
- [Tool Charter](TOOL_CHARTER.md)
- [Try It Local](TRY_IT_LOCAL.md)
- [Day 1 Checklist](DAY1_DEPLOY_CHECKLIST.md)
- [Runbook](RUNBOOK.md)
- [Accessibility](ACCESSIBILITY.md)
- [Security Baseline](SECURITY_BASELINE.md)
- [Endpoint Checklist](ENDPOINT_CHECKLIST.md)
- [Privacy Addendum](PRIVACY-ADDENDUM.md)
- [Disaster Recovery](DISASTER_RECOVERY.md)

## Pilot in a box
- Time to deploy: local demo in minutes; domain pilot typically in a single setup session.
- Week 1 success: students can join, submit once, and teachers can review from `/teach` without manual triage.
- Deliberate non-goals: no gradebook, no surveillance analytics, no ad-tech stack.
- Student control is visible: `/student/my-data` export/delete/end-session works in rehearsal before class day.
- Reliability signal: strict smoke passes (`/healthz`, `/helper/healthz`, join, helper, teacher route checks).
- Measure without surveillance: onboarding time, submissions per session, and teacher minutes saved on closeout.
- Pilot guide: [Pilot Playbook](PILOT_PLAYBOOK.md).

## Human entry points
- Executive Director: [START_HERE_ED.md](START_HERE_ED.md)
- Ops Director: [START_HERE_OD.md](START_HERE_OD.md)
- Fundraising: [START_HERE_FUNDRAISING.md](START_HERE_FUNDRAISING.md)
- Instructor / assistant: [START_HERE_INSTRUCTOR.md](START_HERE_INSTRUCTOR.md)
- First-time class launch: [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md)
- Common day-of-class issues: [COMMON_SCENARIOS.md](COMMON_SCENARIOS.md)

## Press screenshots
Synced from `press/screenshots/` for wiki/docs browsing.

![Student join](images/press/01-student-join.png)

![Student class view](images/press/02-student-class-view.png)

![Teacher dashboard](images/press/03-teacher-dashboard.png)

![Teacher lesson tracker](images/press/04-teacher-lesson-tracker.png)

![Lesson with helper](images/press/05-lesson-with-helper.png)

![Submission dropbox](images/press/06-submission-dropbox.png)

![Admin login](images/press/07-admin-login.png)

![Health checks terminal](images/press/08-health-checks-terminal.png)

Planned next captures (placeholders):
- `09-teacher-profile-tab.png`
- `10-org-management-tab.png`
- `11-invite-only-enrollment.png`
- `12-certificate-eligibility.png`
- `13-a11y-smoke-terminal.png`

See `press/screenshots/PLACEHOLDERS.md` and `press/screenshots/SHOTLIST.md`.
