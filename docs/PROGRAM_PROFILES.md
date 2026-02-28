# Program Profiles

Use one setting to choose default behavior by cohort type:

```dotenv
CLASSHUB_PROGRAM_PROFILE=secondary
```

Allowed values:
- `elementary`
- `secondary` (default)
- `advanced`

This does not create a separate product mode. It only sets safer defaults for existing toggles. You can still override each toggle directly in `compose/.env`.

## Default map

| Profile | Join/rejoin default | Helper strictness default | Helper scope default | Helper topic filter default | UI density default |
|---|---|---|---|---|---|
| `elementary` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1` | `HELPER_STRICTNESS=strict` | `HELPER_SCOPE_MODE=strict` | `HELPER_TOPIC_FILTER_MODE=strict` | `compact` |
| `secondary` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0` | `HELPER_STRICTNESS=light` | `HELPER_SCOPE_MODE=soft` | `HELPER_TOPIC_FILTER_MODE=soft` | `standard` |
| `advanced` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0` | `HELPER_STRICTNESS=light` | `HELPER_SCOPE_MODE=soft` | `HELPER_TOPIC_FILTER_MODE=soft` | `expanded` |

## Override precedence

1. Explicit env var wins (for example, `HELPER_STRICTNESS=light`).
2. If not set, profile default is used.
3. If profile is missing/invalid, `secondary` behavior is used.

## Recommended operator presets

### Elementary pilot

```dotenv
CLASSHUB_PROGRAM_PROFILE=elementary
# Optional explicit lock-ins:
CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1
HELPER_STRICTNESS=strict
HELPER_SCOPE_MODE=strict
HELPER_TOPIC_FILTER_MODE=strict
```

### Middle/high school pilot

```dotenv
CLASSHUB_PROGRAM_PROFILE=secondary
# Optional explicit lock-ins:
CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0
HELPER_STRICTNESS=light
HELPER_SCOPE_MODE=soft
HELPER_TOPIC_FILTER_MODE=soft
```

### Advanced/project cohort

```dotenv
CLASSHUB_PROGRAM_PROFILE=advanced
# Optional explicit lock-ins:
CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0
HELPER_STRICTNESS=light
HELPER_SCOPE_MODE=soft
HELPER_TOPIC_FILTER_MODE=soft
```

## Practical notes

- For shared elementary devices, keep `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1` to reduce accidental identity reuse.
- If you need strict helper boundaries in any profile, set helper toggles explicitly; profile defaults are only a baseline.
- Keep privacy posture unchanged across profiles: no prompt archive, no surveillance analytics.

## UI density behaviors (current student structure)

All profiles use the same core student layout and permissions:
- class landing with `This week`, `Course links`, and `Account` blocks
- module cards are collapsible
- helper widget is collapsed by default
- checklist/reflection/rubric editors are shown via details-on-demand

Density mode changes text and visual complexity, not security/privacy boundaries:
- `compact`: shortest status copy and reduced instructional text
- `standard`: balanced detail for most middle/high cohorts
- `expanded`: studio-mode structure for advanced/project contexts

## Advanced Studio Contract

When `ui_density_mode=expanded`, ClassHub should bias toward structured autonomy:

- Keep core handles visible:
  - rubric access links,
  - portfolio export link,
  - gallery-share controls.
- Add explicit articulation prompts:
  - design-log prompt each lesson,
  - changelog and release-note expectations.
- Expose challenge branches as clear optional blocks when lesson `extend` items exist.
- Emphasize reading/explaining code paths, not only remix completion.

## Course-level UI override (optional)

If a specific course needs a different learner-facing UI density than the global profile, add `ui_level` in that course manifest:

```yaml
# services/classhub/content/courses/<course_slug>/course.yaml
ui_level: elementary  # elementary | secondary | advanced
```

Resolution order:
1. Lesson front matter `ui_level` / `learner_level` (if present),
2. Course manifest `ui_level` / `learner_level` / `program_profile`,
3. `CLASSHUB_PROGRAM_PROFILE`.

This only changes learner UI density text/layout (`compact`, `standard`, `expanded`). It does not alter privacy, retention, or permission boundaries.

## Related docs

- [PILOT_PLAYBOOK.md](PILOT_PLAYBOOK.md)
- [CLASS_CODE_AUTH.md](CLASS_CODE_AUTH.md)
- [HELPER_POLICY.md](HELPER_POLICY.md)
- [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md)
