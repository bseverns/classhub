"""Internal helper conversation reset endpoint."""

import hmac
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .engine import memory as engine_memory
from .engine import runtime as engine_runtime

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    return engine_runtime.env_int(name, default, getenv=os.getenv)


def _env_bool(name: str, default: bool) -> bool:
    return engine_runtime.env_bool(name, default, getenv=os.getenv)


def _request_id(request) -> str:
    return engine_runtime.request_id(request)


def _json_response(payload: dict, *, request_id: str, status: int = 200):
    return engine_runtime.json_response(payload, request_id_value=request_id, status=status)


def _log_chat_event(level: str, event: str, *, request_id: str, **fields):
    engine_runtime.log_chat_event(
        level,
        event,
        request_id_value=request_id,
        logger=logger,
        **fields,
    )


def _extract_bearer_token(request) -> str:
    header = (request.META.get("HTTP_AUTHORIZATION", "") or "").strip()
    if not header.lower().startswith("bearer "):
        return ""
    return header[7:].strip()


def _internal_api_token() -> str:
    return str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip()


def _payload_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _write_class_reset_archive(*, class_id: int, request_id: str, conversations: list[dict]) -> tuple[str, int]:
    archive_dir = (os.getenv("HELPER_CLASS_RESET_ARCHIVE_DIR", "/uploads/helper_reset_exports") or "").strip()
    if not archive_dir:
        raise RuntimeError("archive_directory_not_configured")

    archive_root = Path(archive_dir).expanduser().resolve()
    archive_root.mkdir(mode=0o750, parents=True, exist_ok=True)
    try:
        os.chmod(archive_root, 0o750)
    except Exception:
        pass

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Keep archive paths independent of request payload to avoid path-injection taint.
    filename = f"class_helper_reset_{stamp}_{uuid4().hex[:12]}.json"
    archive_path = (archive_root / filename).resolve()
    if archive_path.parent != archive_root:
        raise RuntimeError("archive_path_outside_root")

    payload = {
        "class_id": int(class_id),
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "conversation_count": len(conversations),
        "conversations": conversations,
        "request_id": str(request_id or ""),
    }
    with archive_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
    try:
        os.chmod(archive_path, 0o640)
    except Exception:
        pass
    return str(archive_path), len(conversations)


@csrf_exempt
@require_POST
def reset_class_conversations(request):
    request_id = _request_id(request)
    configured_token = _internal_api_token()
    if not configured_token:
        _log_chat_event("error", "internal_token_not_configured", request_id=request_id)
        return _json_response({"error": "internal_token_not_configured"}, status=503, request_id=request_id)

    provided_token = _extract_bearer_token(request)
    if not provided_token or not hmac.compare_digest(configured_token, provided_token):
        _log_chat_event("warning", "internal_unauthorized", request_id=request_id)
        return _json_response({"error": "unauthorized"}, status=401, request_id=request_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        _log_chat_event("warning", "internal_bad_json", request_id=request_id)
        return _json_response({"error": "bad_json"}, status=400, request_id=request_id)
    if not isinstance(payload, dict):
        return _json_response({"error": "bad_json"}, status=400, request_id=request_id)

    try:
        class_id = int(payload.get("class_id") or 0)
    except Exception:
        class_id = 0
    if class_id <= 0:
        return _json_response({"error": "invalid_class_id"}, status=400, request_id=request_id)

    max_keys = max(_env_int("HELPER_CLASS_RESET_MAX_KEYS", 4000), 1)
    archive_enabled = _env_bool("HELPER_CLASS_RESET_ARCHIVE_ENABLED", True)
    archive_requested = _payload_bool(payload.get("export_before_reset"))
    archive_before_reset = archive_enabled and archive_requested
    archive_path = ""
    archived_conversations = 0
    if archive_before_reset:
        snapshot = engine_memory.snapshot_class_conversations(
            cache_backend=cache,
            class_id=class_id,
            max_keys=max_keys,
            max_messages=max(_env_int("HELPER_CLASS_RESET_ARCHIVE_MAX_MESSAGES", 120), 1),
        )
        if snapshot:
            try:
                archive_path, archived_conversations = _write_class_reset_archive(
                    class_id=class_id,
                    request_id=request_id,
                    conversations=snapshot,
                )
            except Exception:
                _log_chat_event(
                    "warning",
                    "class_conversations_archive_failed",
                    request_id=request_id,
                    class_id=class_id,
                )

    deleted = engine_memory.clear_class_conversations(
        cache_backend=cache,
        class_id=class_id,
        max_keys=max_keys,
    )
    _log_chat_event(
        "info",
        "class_conversations_reset",
        request_id=request_id,
        class_id=class_id,
        deleted_conversations=deleted,
        archived_conversations=archived_conversations,
        archive_path=archive_path,
    )
    response_payload = {
        "ok": True,
        "class_id": class_id,
        "deleted_conversations": deleted,
        "archived_conversations": archived_conversations,
    }
    if archive_path:
        response_payload["archive_path"] = archive_path
    return _json_response(response_payload, request_id=request_id)


__all__ = ["reset_class_conversations"]
