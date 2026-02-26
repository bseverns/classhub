# Public Overview

## Summary
Class Hub is a classroom-first, self-hosted micro-LMS with a separate Homework Helper service. It is designed for calm classroom operations, low-friction student access, and operator control over infrastructure and data.

## What to do now
1. Decide if this fits your context (quick bullets below).
2. Try the local demo path in [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md).
3. If you plan public deployment, read [SECURITY.md](SECURITY.md), then [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) and [RUNBOOK.md](RUNBOOK.md).

## Verification signal
If this page is useful, you should be able to answer: who this is for, what it deliberately does not do, and the next 2 docs to read for an evaluation.

## Organization and place acknowledgment
- createMPLS is a Minneapolis-based 501(c)(3) nonprofit organization.
- Minneapolis is located on land ceded by treaty and has historically been home to the Anishinaabe, Dakota, and Oceti Sakowin peoples.

## What it is
- A self-hosted learning hub for classes, modules, and lesson materials.
- A simple student join flow (`class code + display name`) without student password accounts in MVP.
- A teacher/admin workflow built on Django auth, with safety controls for public-domain operation.

## Who it is for
- Small schools and programs that want self-hosted control.
- Makerspaces, after-school labs, and classroom pilots.
- Teams that prefer simple operational primitives over large platform complexity.

## What makes it different
- Privacy-first defaults (minimal student identity model, explicit retention controls).
- Calm student join model (no student email/password in MVP).
- Public-domain hardening options (CSP, site-mode degradation, proxy guardrails).
- Self-hosted architecture with boring, inspectable components (Django, Postgres, Redis, Caddy).

## What it will not do
- No surveillance analytics posture.
- No ad-tech or data resale model.
- No dark-pattern growth loops.
- No hidden SaaS lock-in requirement for core operation.

## Try it in 10 minutes
- Local demo path: [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md)

## Screenshots (placeholders)
- Student join screen: `press/screenshots/01-student-join.png`
- Teacher dashboard: `press/screenshots/03-teacher-dashboard.png`
- Lesson page with helper: `press/screenshots/05-lesson-with-helper.png`
- Teacher profile tab: `press/screenshots/09-teacher-profile-tab.png` (planned placeholder)
- Organization management tab: `press/screenshots/10-org-management-tab.png` (planned placeholder)
- Invite-only enrollment controls: `press/screenshots/11-invite-only-enrollment.png` (planned placeholder)
- Certificate eligibility page: `press/screenshots/12-certificate-eligibility.png` (planned placeholder)
- Accessibility smoke terminal: `press/screenshots/13-a11y-smoke-terminal.png` (planned placeholder)

## Ops and security links
- [SECURITY.md](SECURITY.md)
- [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md)
- [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md)
- [RUNBOOK.md](RUNBOOK.md)
