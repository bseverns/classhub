# Homework Helper Service Notebook (`services/homework_helper`)

This is the AI tutor engine routed under `/helper/*`.
Its job is to help students learn, **not** to become a copy/paste cheating oracle.

## What this service owns

- Helper chat endpoint behavior.
- Tutor policy and anti-cheating guardrails.
- Request safety controls (rate limits + topic gating where configured).
- Minimal redaction pass for obvious PII patterns before model calls/logging.

## Core files to know

- `tutor/views.py` = HTTP endpoint plumbing for helper requests.
- `tutor/policy.py` = tutor stance + response constraints.
- `tutor/queueing.py` = helper request scheduling/backpressure behavior.
- `tutor/classhub_events.py` = helper-side event shaping for class context.
- `config/settings.py` = cache/rate-limit + provider wiring.

## API/provider posture

Project direction is OpenAI Responses API for hosted model calls.
If you touch provider integrations, keep interfaces narrow and easy to swap.

## Local developer loop

From repo root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r services/homework_helper/requirements.txt
DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret-dev-secret-dev-secret-123 python3 services/homework_helper/manage.py check
DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret-dev-secret-dev-secret-123 python3 services/homework_helper/manage.py test
```

For full-stack behavior (redis, routing, classhub integration), run Compose:

```bash
cd compose
docker compose up -d --build
docker compose exec helper_web python manage.py check
```

## Guardrail checklist before PR

- Rate limiting still works with Redis-backed cache settings.
- Policy language still pushes explanation/learning over answer dumping.
- Redaction changes are documented and intentionally minimal (avoid over-collection).
- Superuser `/admin` remains OTP-verified when `DJANGO_ADMIN_2FA_REQUIRED=1`.
- Any behavior changes are reflected in `docs/OPENAI_HELPER.md`, `docs/HELPER_POLICY.md`, or `docs/DECISIONS.md`.

## Design attitude

Ship helper behavior that teachers can defend in front of parents/admins.
If a feature is flashy but raises misuse risk or support burden, kill it.
