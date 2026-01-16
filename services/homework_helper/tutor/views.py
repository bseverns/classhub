import json

import os
import re

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

# OpenAI Python SDK: Responses API + output_text helper.
# Examples in OpenAI docs show:
#   response = client.responses.create(model="gpt-5.2", input="...")
#   print(response.output_text)
# See OpenAI quickstart / guides for current usage.
# Ref: https://platform.openai.com/docs/quickstart
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def _redact(text: str) -> str:
    """Very light redaction.

    Goal: reduce accidental PII in prompts.
    Not a complete privacy solution.
    """
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


def _rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Return True if allowed; False if blocked."""
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=window_seconds)
        return True
    if int(current) >= limit:
        return False
    try:
        cache.incr(key)
    except Exception:
        cache.set(key, int(current) + 1, timeout=window_seconds)
    return True


@require_GET
def healthz(request):
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST


def chat(request):
    """POST /helper/chat

    Input JSON:
      {"message": "..."}

    Output JSON:
      {"text": "...", "model": "..."}

    Day-1 note:
    - This endpoint is not yet tied to class materials (RAG planned).
    - Caddy routes /helper/* to this service.
    """
    who = request.META.get("REMOTE_ADDR", "unknown")

    # Rate limit: 20 req/min per IP (MVP). Replace with user-id when auth exists here.
    if not _rate_limit(f"rl:{who}:m", limit=20, window_seconds=60):
        return JsonResponse({"error": "rate_limited"}, status=429)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad_json"}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "missing_message"}, status=400)

    # Bound size + redact obvious PII patterns
    message = _redact(message)[:8000]

    model = os.getenv("OPENAI_MODEL", "gpt-5.2")

    # Tutor stance:
    # - guide with steps, hints, and questions
    # - avoid producing direct final answers for graded work
    instructions = (
        "You are a calm, encouraging homework helper. "
        "Teach by guiding: ask clarifying questions, give hints, outline steps, "
        "and check understanding. "
        "If asked to produce a final answer for graded work, refuse and instead "
        "provide a learning-oriented approach. "
        "Keep responses concise."
    )

    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=message,
        )
    except Exception as e:
        # Do not leak internal exceptions to clients.
        return JsonResponse({"error": "openai_error"}, status=502)

    return JsonResponse({
        "text": getattr(response, "output_text", "") or "",
        "model": model,
    })
