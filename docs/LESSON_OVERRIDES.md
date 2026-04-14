# Lesson Overrides

## Summary
Use this guide when a teacher needs to change one lesson for one class without changing the shared curriculum files for every class.

## What to do now
1. Confirm that the change should be local to one class, not a permanent curriculum change for all classes.
2. Open the lesson in class context and use `Edit Markdown`.
3. Save, review the class-specific lesson page, and reset to default later if the local change is no longer needed.

## Verification signal
After reading this page, a teacher should be able to explain the difference between a shared curriculum file change and a class-local lesson override.

## What a class-local lesson override is

- A per-class markdown version of one lesson stored in the database.
- A way to add class-specific wording, pacing notes, or temporary adjustments.
- A reversible teacher workflow inside the portal.

## What it is not

- It is not a change to the repository course files.
- It is not a new canonical course version for every class.
- It is not a live side-by-side preview editor.
- It is not a replacement for normal curriculum authoring when the shared source should change for everyone.

## Who can use it

- Staff who can manage the target class.
- In practice, this means teachers/admins with class-management access.
- Read-only staff do not get the `Edit Markdown` action for that class.

## Shared curriculum vs local class changes

- Shared curriculum remains file-first and repo-native.
- Repository course files stay the source of truth for the canonical curriculum.
- A lesson override affects one `Class` + one lesson only.
- If the override is removed, that class returns to the repository version automatically.

If the change should become the new shared curriculum, use the normal course authoring or coursepack workflow instead:
- [COURSE_AUTHORING.md](COURSE_AUTHORING.md)
- [TEACHER_COURSE_IMPORT.md](TEACHER_COURSE_IMPORT.md)

## How to enter the editor

1. Sign in to `/teach`.
2. Open the target class.
3. Open the lesson in that class context.
4. On the lesson page, use `Edit Markdown`.

The edit route is:

```text
/teach/course/<course_slug>/lesson/<lesson_slug>/edit?class_id=<class_id>
```

The `Edit Markdown` button is shown from the lesson page when:
- the request is in class context, and
- the signed-in staff user can manage that class.

## How save and preview work

- The editor starts with the current effective markdown for that class:
  - repository markdown if no override exists yet,
  - existing override markdown if the class already has one.
- `Save Override` stores the markdown as a class-local override.
- After save, the portal redirects back to the lesson page with the class context query string.
- That lesson page is the preview of the rendered result for that class.

Important distinction:
- This is a save-then-review workflow.
- There is no separate unsaved preview pane in the editor.

## How reset works

- `Reset to Default` deletes the class-local override for that lesson.
- After reset, the lesson falls back to the repository version for that class.
- Reset does not delete or change repository course files.

## What is audited

The following actions are written to immutable `AuditEvent` rows:
- create (`lesson_override.create`)
- update (`lesson_override.update`)
- reset (`lesson_override.reset`)

Audit metadata includes:
- class
- course slug
- lesson slug
- whether an override exists after the action

## What to use this for

Good uses:
- a pacing note for one cohort
- a class-specific reminder about materials or room setup
- temporary wording changes for one teacher's delivery
- a local adaptation while you decide whether the shared curriculum should change later

Do not use this when:
- the shared repository lesson is wrong for everyone
- the change belongs in the canonical curriculum
- you need a durable curriculum-authoring workflow rather than a class-local exception

## Related docs

- Teacher workflow reference: [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- Plain-language teacher workflow: [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md)
- First-time class checklist: [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md)
- Common classroom playbooks: [COMMON_SCENARIOS.md](COMMON_SCENARIOS.md)
- Shared curriculum / coursepack workflow: [TEACHER_COURSE_IMPORT.md](TEACHER_COURSE_IMPORT.md), [COURSE_AUTHORING.md](COURSE_AUTHORING.md)
