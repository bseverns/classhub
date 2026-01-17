# Piper + Scratch (12 Sessions) — Repo-first Course Pack

This folder is meant to be copied into your Tailoredu Django repo as repo-authored course content.

## Recommended placement in the site repo

Place this folder at:

- `content/courses/piper_scratch_12_session/`

So your repo becomes:

```
repo-root/
  content/
    courses/
      piper_scratch_12_session/
        course.yaml
        lessons/
          01-welcome-private-workflow.md
          ...
        video-scripts/
          V01-boot-desktop.md
          ...
        checklists/
          bug-report-template.md
```

### Django wiring (notes)
- Your `courses` app should treat `content/courses/<course_slug>/course.yaml` as the **manifest**.
- Each lesson record should map to the Markdown path declared in `course.yaml`.
- Rendering approach: read the markdown file from disk, convert to HTML (server-side), and wrap it with your lesson template.

If you don't have this yet, the simplest path is:
1. Add a `CONTENT_ROOT = BASE_DIR / "content"` setting.
2. Create a management command (e.g., `courses.management.commands.import_content`) that:
   - scans `content/courses/**/course.yaml`
   - upserts `Course` + `Lesson` rows (slug, title, session number, md path)
3. Route: `/course/<course_slug>/lesson/<lesson_slug>/` reads and renders the md file declared.

## Privacy defaults
These lessons assume:
- No camera required; voice optional
- Local save first; upload privately
- Optional Scratch public sharing only by student choice

## What to edit
- Replace placeholder LMS help-form link text with your actual route.
- If you host video internally, replace `videos:` IDs in front matter with real URLs/IDs.
