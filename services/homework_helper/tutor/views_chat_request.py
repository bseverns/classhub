import json


def resolve_actor_and_client(*, request, actor_key_fn, settings, client_ip_from_request_fn):
    actor = actor_key_fn(request)
    actor_type = actor.split(":", 1)[0] if actor else "anonymous"
    client_ip = client_ip_from_request_fn(
        request,
        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
    )
    return actor, actor_type, client_ip


def load_session_ids(request) -> tuple[int, int]:
    try:
        classroom_id = int(request.session.get("class_id") or 0)
    except Exception:
        classroom_id = 0
    try:
        student_id = int(request.session.get("student_id") or 0)
    except Exception:
        student_id = 0
    return classroom_id, student_id


def enforce_rate_limits(
    *,
    actor: str,
    actor_type: str,
    client_ip: str,
    request_id: str,
    actor_limit: int,
    ip_limit: int,
    fixed_window_allow_fn,
    cache_backend,
    log_chat_event_fn,
    json_response_fn,
):
    if not fixed_window_allow_fn(
        f"rl:actor:{actor}:m",
        limit=actor_limit,
        window_seconds=60,
        cache_backend=cache_backend,
        request_id=request_id,
    ):
        log_chat_event_fn("warning", "rate_limited_actor", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return json_response_fn({"error": "rate_limited"}, status=429, request_id=request_id)
    if not fixed_window_allow_fn(
        f"rl:ip:{client_ip}:m",
        limit=ip_limit,
        window_seconds=60,
        cache_backend=cache_backend,
        request_id=request_id,
    ):
        log_chat_event_fn("warning", "rate_limited_ip", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return json_response_fn({"error": "rate_limited"}, status=429, request_id=request_id)
    return None


def parse_chat_payload(
    *,
    request_body: bytes,
    request_id: str,
    actor_type: str,
    client_ip: str,
    log_chat_event_fn,
    json_response_fn,
):
    try:
        payload = json.loads(request_body.decode("utf-8"))
    except Exception:
        log_chat_event_fn("warning", "bad_json", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return None, json_response_fn({"error": "bad_json"}, status=400, request_id=request_id)
    if not isinstance(payload, dict):
        log_chat_event_fn("warning", "bad_json", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return None, json_response_fn({"error": "bad_json"}, status=400, request_id=request_id)
    return payload, None


__all__ = [
    "enforce_rate_limits",
    "load_session_ids",
    "parse_chat_payload",
    "resolve_actor_and_client",
]
