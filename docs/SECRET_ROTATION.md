# Secret Rotation

## Summary
This page is the operator reference for ClassHub signing keys, bearer tokens, and provider API secrets.

Use it when you need to:

1. inventory which secret protects which boundary,
2. rotate a compromised or aging token safely,
3. understand what user-visible impact rotation should cause.

## What this covers

This page covers deploy-time secrets that materially affect runtime trust boundaries:

- Django signing keys
- helper scope signing key
- cross-service internal bearer tokens
- private/backend API keys used by Homework Helper

It does not try to replace your password manager or cloud secret store.

## Inventory

| Secret | Scope | Used by | Rotation impact |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django signing root | `classhub_web`, `helper_web` | invalidates Django-signed sessions/tokens; treat as highest-impact rotation |
| `DEVICE_HINT_SIGNING_KEY` | student same-device rejoin hint cookie | `classhub_web` | existing same-device student hint cookies stop working; students can still rejoin with class code + return code |
| `HELPER_SCOPE_SIGNING_KEY` | signed helper lesson scope token | `classhub_web`, `helper_web` | existing helper scope tokens stop validating until lesson pages are reloaded |
| `CLASSHUB_INTERNAL_EVENTS_TOKEN` | helper -> ClassHub event ingest | `helper_web` caller, `classhub_web` receiver | helper event forwarding fails until both services match again |
| `HELPER_INTERNAL_API_TOKEN` | ClassHub -> helper internal control/status endpoints | `classhub_web` caller, `helper_web` receiver | teacher-side helper control/status panels fail closed until both services match again |
| `LLM_API_KEY` / `OLLAMA_API_KEY` | helper -> private LLM/auth proxy | `helper_web`, private model edge | helper backend calls fail until helper and private proxy agree |
| `OPENAI_API_KEY` | helper -> hosted OpenAI path | `helper_web` | OpenAI helper backend fails until helper has the new key |
| `REMOTE_LLM_API_KEY` | helper -> remote helper-compute target | `helper_web`, remote backend | remote helper compute leases cannot route remotely until helper and remote backend agree |
| `HELPER_REMOTE_COMPUTE_CONTROL_API_KEY` | helper -> orchestration bridge | `helper_web`, remote-compute bridge | remote compute activate/deactivate/health calls fail until helper and bridge agree |

## Source of truth

- Runtime env contract: `compose/.env.example.domain`
- Baseline security posture: [SECURITY.md](SECURITY.md)
- Operator command flow: [RUNBOOK.md](RUNBOOK.md)
- Disaster recovery env restore set: [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)

## General rotation rules

- Never commit live secrets to git.
- Rotate in your secret manager first, then update `compose/.env` or the deployment environment.
- Prefer one secret per trust boundary; do not reuse one token for multiple paths.
- After rotation, restart only the services that actually consume the secret.
- Verify with the smallest relevant probe instead of jumping directly to full smoke.
- Record the rotation date and owner in your ops notes.

## Rotation order

### 1) Signing keys

Rotate these carefully because they invalidate existing signed artifacts.

#### `DEVICE_HINT_SIGNING_KEY`

Use when:
- you suspect hint-cookie leakage,
- you want to rotate periodic signing material without affecting Django auth globally.

Steps:

1. Set a new strong `DEVICE_HINT_SIGNING_KEY`.
2. Recreate `classhub_web`.
3. Verify student join + same-device rejoin behavior.

Expected impact:
- existing hint cookies no longer work,
- student return-code rejoin still works,
- no teacher/admin auth impact.

#### `HELPER_SCOPE_SIGNING_KEY`

Use when:
- helper scope token leakage is suspected,
- you want to rotate helper-only signing material separately from Django root signing.

Steps:

1. Set a new strong `HELPER_SCOPE_SIGNING_KEY`.
2. Recreate both `classhub_web` and `helper_web`.
3. Reload a lesson page and verify `/helper/chat`.

Expected impact:
- already-rendered lesson pages may hold stale helper scope tokens,
- a page reload should restore helper access.

#### `DJANGO_SECRET_KEY`

Use when:
- you suspect broad signing compromise,
- or you are doing an intentional full root secret rotation.

Steps:

1. Set a new strong `DJANGO_SECRET_KEY`.
2. Keep `DEVICE_HINT_SIGNING_KEY` and `HELPER_SCOPE_SIGNING_KEY` distinct from it.
3. Recreate both Django services.
4. Verify admin login, teacher login, and student join after rotation.

Expected impact:
- Django sessions and any Django-root-signed values are invalidated,
- this is the highest-friction rotation and should be scheduled.

## Cross-service internal token rotation

These tokens protect service-to-service traffic and should fail closed when mismatched.

### `CLASSHUB_INTERNAL_EVENTS_TOKEN`

Path:
- `helper_web` -> `classhub_web` internal helper event ingest

Steps:

1. Set the new `CLASSHUB_INTERNAL_EVENTS_TOKEN` in the deployment env for both services.
2. Recreate `classhub_web` and `helper_web`.
3. Run:

```bash
cd /srv/lms/app
bash scripts/validate_env_secrets.sh
bash scripts/system_doctor.sh --smoke-mode golden
```

Expected impact if mismatched:
- helper event forwarding fails,
- user-visible helper chat may still work, but event ingest does not.

### `HELPER_INTERNAL_API_TOKEN`

Path:
- `classhub_web` -> `helper_web` internal reset/status/remote-compute control endpoints

Steps:

1. Set the new `HELPER_INTERNAL_API_TOKEN` for both services.
2. Recreate `classhub_web` and `helper_web`.
3. Verify teacher-side helper status/reset surfaces.

Fast check:

```bash
cd /srv/lms/app
python3 scripts/operator_preflight.py --env-file compose/.env
```

Expected impact if mismatched:
- teacher-side helper control/status panels fail closed,
- helper internal endpoints return `401 unauthorized`,
- student-facing classroom pages still load.

## Backend/provider secret rotation

### `LLM_API_KEY` / `OLLAMA_API_KEY`

Path:
- `helper_web` -> private LLM auth proxy or private backend

Steps:

1. Rotate the private proxy/backend bearer token on the GPU/private model side.
2. Update `LLM_API_KEY` in the LMS deployment env.
3. Recreate `helper_web`.
4. Verify:

```bash
cd /srv/lms/app
bash scripts/check_llm_backend.sh --probe-chat
```

Expected impact if mismatched:
- helper backend path fails,
- core LMS pages still load,
- remote/private helper lane degrades.

### `OPENAI_API_KEY`

Path:
- `helper_web` -> OpenAI hosted backend

Steps:

1. Update `OPENAI_API_KEY`.
2. Recreate `helper_web`.
3. Verify the helper backend path using the same helper probe flow.

### `REMOTE_LLM_API_KEY`

Path:
- `helper_web` -> remote helper-compute target used only when lease state is `ready`

Steps:

1. Rotate the token on the remote backend side.
2. Update `REMOTE_LLM_API_KEY` in LMS env.
3. Recreate `helper_web`.
4. Verify remote routing only after the backend is `ready`.

Expected impact if mismatched:
- remote helper-compute path fails,
- helper should stay or fall back to local/default mode.

### `HELPER_REMOTE_COMPUTE_CONTROL_API_KEY`

Path:
- `helper_web` -> orchestration bridge activate/health/stop endpoints

Steps:

1. Rotate the token on the bridge.
2. Update `HELPER_REMOTE_COMPUTE_CONTROL_API_KEY` in LMS env.
3. Recreate `helper_web`.
4. Verify teacher-side remote-compute controls.

Expected impact if mismatched:
- bridge calls fail,
- class stays on local/default helper compute,
- student browsers never receive bridge credentials.

## Break-glass revoke actions

If you suspect active misuse and need to reduce blast radius immediately:

### Internal helper control path

If `HELPER_INTERNAL_API_TOKEN` is suspected:

1. Set a new token in both services immediately.
2. Recreate `classhub_web` and `helper_web`.
3. Verify teacher-side helper panels after restart.

### Private LLM path

If `LLM_API_KEY` is suspected:

1. Rotate the backend/private-proxy token.
2. Update LMS env and recreate `helper_web`.
3. If rotation cannot happen immediately, temporarily disable the remote path by switching helper back to local/default backend settings.

### Remote helper compute bridge

If `HELPER_REMOTE_COMPUTE_CONTROL_API_KEY` is suspected:

1. Set:

```bash
CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED=0
CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED=0
```

2. Recreate `helper_web`.
3. Rotate the bridge token separately before re-enabling the feature.

This keeps the main LMS and helper baseline path available while removing bridge control exposure.

## Verification checklist after any rotation

Run the smallest matching checks first:

```bash
cd /srv/lms/app
bash scripts/validate_env_secrets.sh
python3 scripts/operator_preflight.py --env-file compose/.env
```

Then run path-specific verification:

- Django/session impact: teacher login + student join
- helper backend impact: `bash scripts/check_llm_backend.sh --probe-chat`
- full stack: `bash scripts/system_doctor.sh --smoke-mode golden`

## Disaster recovery note

Backups must include the current values for:

- signing keys,
- internal service tokens,
- backend/provider API keys,
- remote-compute bridge token if that feature is enabled.

If you restore data but not the matching secret set, expect helper control paths and signed artifacts to fail until secrets are restored coherently.
