# Teacher Top 10 Tasks (Stability Freeze Baseline)

This is the canonical Day 0-30 task map for `/teach`.

Use it for:
- weekly regression walkthroughs
- copy/order decisions in teacher surfaces
- release readiness checks against real teacher workflows

Last updated: March 10, 2026

## Task Map

| # | Task | Primary routes/actions | Completion signal |
| --- | --- | --- | --- |
| 1 | Create a class | `POST /teach/create-class` from `/teach` | New class row appears with join code and open status. |
| 2 | Share join access with students | `GET /teach/class/<id>/join-card`, copy class join code on `/teach` or `/teach/class/<id>` | Students can join via class code or printed join card. |
| 3 | Open class dashboard for live teaching | `GET /teach/class/<id>` | Class dashboard loads with roster, modules, and status controls. |
| 4 | Review submission queue and download work | `GET /teach/material/<material_id>/submissions`, `GET /submission/<id>/download` | Teacher can see missing/submitted rows and retrieve files. |
| 5 | Close/open class access at session boundaries | `POST /teach/class/<id>/toggle-lock` (and closeout lock action) | Class state pill changes (`Open`/`Locked`) and student join behavior changes accordingly. |
| 6 | Set lesson release schedule and helper scope | `POST /teach/lessons/release` from class lesson release grid | Release date/scope values persist and appear in lesson release table. |
| 7 | Export day-of-class outputs | `GET /teach/class/<id>/export-submissions-today`, `GET /teach/class/<id>/export-outcomes-csv`, `GET /teach/class/<id>/export-summary-csv` | Export downloads succeed and include current class data. |
| 8 | Correct roster identity mistakes | `POST /teach/class/<id>/rename-student`, `POST /teach/class/<id>/merge-students` | Target student names/records update without duplicate roster confusion. |
| 9 | Create/invite and maintain teacher accounts (admin/superuser) | `POST /teach/create-teacher`, `POST /teach/teacher-account/*` actions | Teacher account row reflects expected active/superuser/invite state. |
| 10 | Maintain organization boundaries and assignments (admin/superuser) | `POST /teach/org-membership/upsert`, `POST /teach/class-staff-assignment/upsert`, `POST /teach/class-organization/set` | Membership/assignment rows update and class scope reflects intended org boundary. |

## Weekly Walkthrough Sequence

Run in this order for stability checks:

1. Tasks 1-4 (daily classroom start path).
2. Tasks 5-8 (in-session and closeout controls).
3. Tasks 9-10 (admin/operator boundary controls).

If wording, discoverability, or completion signals are unclear for any task:
- log friction in the weekly stability notes
- file a stabilization ticket (copy/order/clarity), not a new workflow primitive

## Related Docs

- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [STABILITY_ISSUES.md](STABILITY_ISSUES.md)
- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
