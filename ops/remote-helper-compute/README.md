# Remote Helper Compute Bridge

This directory documents the expected server-side orchestration seam for bounded remote helper compute.

Use this when the createMPLS deployment wants staff in `/teach` to request expensive Thunder-backed helper compute for a live class window without exposing provider controls to the browser.

## Purpose

The bridge sits between Homework Helper and the remote provider.

It should:

- accept server-to-server activate requests
- accept server-to-server stop requests
- report whether the remote path is actually ready
- keep provider credentials and raw orchestration APIs off the LMS/browser path

It must not:

- serve public LMS traffic
- become a student-facing control surface
- expose provider secrets or instance ids to browsers

## Current app seam

ClassHub and Homework Helper expect these URLs:

```bash
HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER=thunder_webhook
HELPER_REMOTE_COMPUTE_ACTIVATE_URL=https://ops.creatempls.org/helper-remote/activate
HELPER_REMOTE_COMPUTE_DEACTIVATE_URL=https://ops.creatempls.org/helper-remote/deactivate
HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL=https://ops.creatempls.org/helper-remote/health
HELPER_REMOTE_COMPUTE_CONTROL_API_KEY=REPLACE_ME_STRONG
```

The app treats `thunder_webhook` as a replaceable adapter seam, not as a hard-coded provider dependency.

## Minimal JSON contract

Activate:

```json
{"ok": true, "state": "starting", "request_id": "req-123", "detail": "booting Thunder GPU node"}
```

Health:

```json
{"ok": true, "state": "ready", "detail": "model warm and reachable"}
```

Stop:

```json
{"ok": true, "state": "off", "detail": "remote helper compute returned to off"}
```

Allowed states:

- `requested`
- `starting`
- `ready`
- `degraded`
- `stopping`
- `error`
- `off`

Only `ready` lets Homework Helper route class traffic to the remote backend.

## Operator expectation

- keep the bridge small and auditable
- keep it private and server-to-server only
- return honest readiness; do not claim `ready` before the remote model path is actually warm
- stop the expensive backend after class or let the bounded lease/idle stop return it to `off`

## Related docs

- [REMOTE_HELPER_COMPUTE_CONTROL.md](../../docs/REMOTE_HELPER_COMPUTE_CONTROL.md)
- [PRIVATE_LLM_BACKEND.md](../../docs/PRIVATE_LLM_BACKEND.md)
- [HEADSCALE_CONTROL_PLANE.md](../../docs/HEADSCALE_CONTROL_PLANE.md)
