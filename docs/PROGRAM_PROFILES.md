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

| Profile | Join/rejoin default | Helper strictness default | Helper scope default | Helper topic filter default |
|---|---|---|---|---|
| `elementary` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1` | `HELPER_STRICTNESS=strict` | `HELPER_SCOPE_MODE=strict` | `HELPER_TOPIC_FILTER_MODE=strict` |
| `secondary` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0` | `HELPER_STRICTNESS=light` | `HELPER_SCOPE_MODE=soft` | `HELPER_TOPIC_FILTER_MODE=soft` |
| `advanced` | `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0` | `HELPER_STRICTNESS=light` | `HELPER_SCOPE_MODE=soft` | `HELPER_TOPIC_FILTER_MODE=soft` |

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

## Related docs

- [PILOT_PLAYBOOK.md](PILOT_PLAYBOOK.md)
- [CLASS_CODE_AUTH.md](CLASS_CODE_AUTH.md)
- [HELPER_POLICY.md](HELPER_POLICY.md)
- [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md)
