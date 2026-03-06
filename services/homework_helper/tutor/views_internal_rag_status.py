"""Internal helper endpoint for curriculum RAG posture/status."""

import hmac
from datetime import datetime

from django.conf import settings
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .engine import rag as engine_rag
from .engine.config_source import helper_getenv
from .engine import runtime as engine_runtime


def _request_id(request) -> str:
    return engine_runtime.request_id(request)


def _json_response(payload: dict, *, request_id: str, status: int = 200):
    return engine_runtime.json_response(payload, request_id_value=request_id, status=status)


def _extract_bearer_token(request) -> str:
    header = (request.META.get("HTTP_AUTHORIZATION", "") or "").strip()
    if not header.lower().startswith("bearer "):
        return ""
    return header[7:].strip()


def _internal_api_token() -> str:
    return str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip()


def _rag_enabled() -> bool:
    return engine_runtime.env_bool("HELPER_RAG_ENABLED", False, getenv=helper_getenv)


def _iso_or_empty(value: datetime | None) -> str:
    if not value:
        return ""
    try:
        return value.isoformat()
    except Exception:
        return ""


def _configured_reference_keys() -> list[str]:
    reference_dir = (helper_getenv("HELPER_REFERENCE_DIR", "/app/tutor/reference") or "/app/tutor/reference").strip()
    reference_map_raw = (helper_getenv("HELPER_REFERENCE_MAP", "") or "").strip()
    inventory = engine_rag.build_reference_inventory(reference_dir, reference_map_raw)
    return sorted(inventory.keys())


def _table_exists() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", [engine_rag.RAG_TABLE_NAME])
        row = cursor.fetchone()
    return bool(row and row[0])


def _fetch_reference_rows() -> tuple[list[dict], int, str]:
    if connection.vendor != "postgresql":
        return [], 0, ""
    if not _table_exists():
        return [], 0, ""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                reference_key,
                COUNT(*)::int AS chunk_count,
                MAX(updated_at) AS last_indexed_at
            FROM tutor_curriculum_rag_chunks
            GROUP BY reference_key
            ORDER BY reference_key ASC
            """
        )
        rows = list(cursor.fetchall() or [])
    reference_rows: list[dict] = []
    total_chunks = 0
    latest = ""
    for reference_key, chunk_count, last_indexed_at in rows:
        chunks = max(int(chunk_count or 0), 0)
        total_chunks += chunks
        stamp = _iso_or_empty(last_indexed_at)
        if stamp and stamp > latest:
            latest = stamp
        reference_rows.append(
            {
                "reference_key": str(reference_key or "").strip(),
                "chunk_count": chunks,
                "last_indexed_at": stamp,
            }
        )
    return reference_rows, total_chunks, latest


@csrf_exempt
@require_GET
def internal_rag_status(request):
    request_id = _request_id(request)
    configured_token = _internal_api_token()
    if not configured_token:
        return _json_response({"error": "internal_token_not_configured"}, status=503, request_id=request_id)
    provided_token = _extract_bearer_token(request)
    if not provided_token or not hmac.compare_digest(configured_token, provided_token):
        return _json_response({"error": "unauthorized"}, status=401, request_id=request_id)

    reference_rows, total_chunks, last_index_built_at = _fetch_reference_rows()
    configured_keys = _configured_reference_keys()
    payload = {
        "ok": True,
        "rag_enabled": _rag_enabled(),
        "index_ready": bool(reference_rows),
        "index_table": engine_rag.RAG_TABLE_NAME,
        "database_vendor": str(connection.vendor or ""),
        "indexed_chunk_count": int(total_chunks),
        "reference_source_count": len(reference_rows),
        "last_index_built_at": last_index_built_at,
        "configured_reference_keys": configured_keys,
        "reference_sources": reference_rows,
        "student_data_excluded_from_index": True,
    }
    return _json_response(payload, request_id=request_id)


__all__ = ["internal_rag_status"]
