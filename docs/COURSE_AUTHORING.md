# Course Authoring Guide

This project loads courses directly from disk. No backend changes are required.

## Course folder structure

```
services/classhub/content/courses/<course_slug>/
  course.yaml
  lessons/
    01-lesson-slug.md
    02-lesson-slug.md
    ...
```

## Create a new course (scaffold)

```bash
python3 scripts/new_course_scaffold.py \
  --slug robotics_intro \
  --title "Robotics: Sensors + Motion" \
  --sessions 8 \
  --duration 75 \
  --age-band "5th-7th"
```

This creates:
- `course.yaml` (manifest)
- lesson markdown stubs
- a helper reference file at `services/homework_helper/tutor/reference/<slug>.md`

## Change the course title after scaffolding

1) Update the course manifest:
   - `services/classhub/content/courses/<course_slug>/course.yaml`
   - Change `title: "..."`.

2) (Optional) Update lesson titles:
   - `services/classhub/content/courses/<course_slug>/lessons/*.md`
   - Edit the `title:` field in the front matter (`---` block).

No backend changes are required; the app reads these files at runtime.

## Lesson front matter template (recommended fields)

```yaml
---
course: <course slug>
session: 1
slug: s01-<lesson-slug>
title: <Lesson Title>
duration_minutes: 75
makes: <short outcome>
needs:
  - <materials or tools>
privacy:
  - <privacy guardrails>
videos: []
submission:
  type: file
  accepted:
    - .<ext>
  naming: <example>
done_looks_like:
  - <objective check>
help:
  quick_fixes:
    - <common fix>
extend:
  - <optional stretch>
teacher_panel:
  purpose: <goal>
  snags:
    - <common pitfalls>
  assessment:
    - <what to look for>
---
```

## Helper configuration (optional)

- Per-course reference: set `helper_reference` in `course.yaml`.
- Per-lesson reference: set `helper_reference` in the lesson entry in `course.yaml`.
- Per-lesson allowed topics: add `helper_allowed_topics` in lesson front matter.

Auto-generate allowed topics:

```bash
python3 scripts/add_helper_allowed_topics.py \
  --lessons-dir services/classhub/content/courses/<course_slug>/lessons \
  --write
```
