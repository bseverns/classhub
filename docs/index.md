# ClassHub Docs

ClassHub is a self-hosted, classroom-first LMS designed for real programming:
fast student join → lesson → submission → teacher review, with a quarantined Homework Helper behind `/helper/*`.

Evaluating for your org? Start with [Public Overview](PUBLIC_OVERVIEW.md) and [Try It Local](TRY_IT_LOCAL.md).

Current platform snapshot: [CURRENT_STATE.md](CURRENT_STATE.md).

## Choose one path
- Leadership and strategy: [START_HERE_ED.md](START_HERE_ED.md), [START_HERE_OD.md](START_HERE_OD.md), [START_HERE_FUNDRAISING.md](START_HERE_FUNDRAISING.md)
- Instructors and assistants: [START_HERE_INSTRUCTOR.md](START_HERE_INSTRUCTOR.md), [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md)
- Non-technical evaluation: [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md), [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- Daily teaching operations: [TEACHER_DOCS_JOURNEY.md](TEACHER_DOCS_JOURNEY.md), [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md), [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- Technical operations: [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md), [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Organization and place acknowledgment
- createMPLS is a Minneapolis-based 501(c)(3) nonprofit organization.
- Minneapolis is located on the ancestral and contemporary homeland of the Dakota Nation (specifically the Mdewakanton, Wahpeton, and Sisseton bands of the Očhéthi Šakówiŋ). The area is known as Mni Sota Makoce and is also a significant territory for the Anishinaabe/Ojibwe people, following their migration to the region.

## Core links
- [Current State](CURRENT_STATE.md)
- [Canonical Truths](CANONICAL_TRUTHS.md)
- [Feature Maturity](FEATURE_MATURITY.md)
- [Coursepack Registry Publishing Guide](COURSEPACK_REGISTRY_PUBLISHING.md)
- [Start Here Overview](START_HERE.md)
- [Teacher Docs Journey](TEACHER_DOCS_JOURNEY.md)
- [Start Here Evaluator](START_HERE_EVALUATOR.md)
- [Risk & Data Posture](RISK_AND_DATA_POSTURE.md)
- [Organization Boundaries](ORG_BOUNDARY_EXPLAINER.md)
- [RBAC Guide](RBAC_GUIDE.md)
- [Privacy Addendum](PRIVACY-ADDENDUM.md)
- [Program Lifecycle](PROGRAM_LIFECYCLE.md)
- [Screenshot Gallery](SCREENSHOT_GALLERY.md)
- [Docs Map](DOCS_MAP.md)
- [Async Self-Paced RFC](ASYNC_SELF_PACED_RFC.md)
- [RBAC Capabilities RFC](RBAC_CAPABILITIES_RFC.md)

## Pilot in a box
- Pilot guide: [PILOT_PLAYBOOK.md](PILOT_PLAYBOOK.md)
- Week 1 target: students can join, submit, and teachers can review from `/teach` without manual triage.
- Reliability checks: `/healthz`, `/helper/healthz`, join flow, helper flow, teacher route checks.
- Trust checks: `/trust` and `/student/my-data` are visible and functional for student data controls.

## Optional: screenshots
??? info "Open press screenshots"
    This section mirrors the full shot list in `press/screenshots/SHOTLIST.md`.

    Captured now (`01`–`19`; `02`, `05`, and `06` are queued for refresh):

    ![01 Student join](images/press/01-student-join.png)

    ![02 Student class view](images/press/02-student-class-view.png)

    ![03 Teacher dashboard](images/press/03-teacher-dashboard.png)

    ![04 Teacher lesson tracker](images/press/04-teacher-lesson-tracker.png)

    ![05 Lesson with helper](images/press/05-lesson-with-helper.png)

    ![06 Submission dropbox](images/press/06-submission-dropbox.png)

    ![07 Admin login](images/press/07-admin-login.png)

    ![08 Health checks terminal](images/press/08-health-checks-terminal.png)

    Additional captured workflow screenshots (`09`–`18`):

    ![09 Teacher profile tab](images/press/09-teacher-profile-tab.png)

    ![10 Org management tab](images/press/10-org-management-tab.png)

    ![11 Invite-only enrollment](images/press/11-invite-only-enrollment.png)

    ![12 Certificate eligibility](images/press/12-certificate-eligibility.png)

    ![14 Student compact view](images/press/14-student-compact-view.png)

    ![16 Student standard view](images/press/16-student-standard-view.png)

    ![17 Student expanded view](images/press/17-student-expanded-view.png)

    Shot list coverage status:

    | Shot | Status | Notes |
    | --- | --- | --- |
    | `01-student-join.png` | Captured | Student join |
    | `02-student-class-view.png` | Captured | Student landing |
    | `03-teacher-dashboard.png` | Captured | Teacher home |
    | `04-teacher-lesson-tracker.png` | Captured | Lessons tracker |
    | `05-lesson-with-helper.png` | Captured | Lesson + helper |
    | `06-submission-dropbox.png` | Captured | Submission flow |
    | `07-admin-login.png` | Captured | Admin login |
    | `08-health-checks-terminal.png` | Captured | Ops checks |
    | `09-teacher-profile-tab.png` | Captured | Teacher profile tab |
    | `10-org-management-tab.png` | Captured | Superuser org tab |
    | `11-invite-only-enrollment.png` | Captured | Invite controls |
    | `12-certificate-eligibility.png` | Captured | Eligibility page |
    | `13-a11y-smoke-terminal.png` | Captured | Accessibility smoke transcript |
    | `14-student-compact-view.png` | Captured | Compact density mode |
    | `15-lesson-helper-collapsed.png` | Captured | Helper collapsed state |
    | `16-student-standard-view.png` | Captured | Standard density mode |
    | `17-student-expanded-view.png` | Captured | Expanded density mode |
    | `18-teacher-landing-editor.png` | Captured | Landing editor |
    | `19-rbac-tools-tab.png` | Captured | RBAC tools tab |
    | `19-rbac-tools-tab-approval-on.png` | Captured | RBAC approval queue companion |
    | `20-data-lifespan-evidence.png` | Captured | Data lifespan evidence dashboard |
    | `21-data-lifespan-export-terminal.png` | Captured | Export command + artifact listing |

    Shot list is fully captured. For capture guidance and future drift tracking, see `press/screenshots/SHOTLIST.md` and `press/screenshots/PLACEHOLDERS.md`.
