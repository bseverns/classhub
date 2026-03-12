"""State token lifecycle helpers for teacher SSO flows."""

from __future__ import annotations

import secrets

from .auth_sso_core_providers import normalize_provider_key


def state_cache_key(*, state_cache_prefix: str, provider_key: str, state_id: str) -> str:
    return f"{state_cache_prefix}:{provider_key}:{state_id}"


def new_sso_state(
    *,
    signing,
    cache,
    provider_key: str,
    next_path: str,
    state_signing_salt: str,
    state_cache_prefix: str,
    state_ttl_seconds: int,
) -> tuple[str, str]:
    state_id = secrets.token_urlsafe(18)
    nonce = secrets.token_urlsafe(18)
    payload = {
        "provider": provider_key,
        "next": next_path,
        "sid": state_id,
        "nonce": nonce,
    }
    state_token = signing.dumps(payload, salt=state_signing_salt, compress=True)
    cache.set(
        state_cache_key(state_cache_prefix=state_cache_prefix, provider_key=provider_key, state_id=state_id),
        "1",
        timeout=state_ttl_seconds,
    )
    return state_token, nonce


def consume_sso_state(
    *,
    signing,
    cache,
    provider_key: str,
    state_token: str,
    state_signing_salt: str,
    state_cache_prefix: str,
    state_ttl_seconds: int,
):
    try:
        payload = signing.loads(state_token, salt=state_signing_salt, max_age=state_ttl_seconds)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None
    if normalize_provider_key(str(payload.get("provider", ""))) != provider_key:
        return None
    state_id = str(payload.get("sid", "")).strip()
    if not state_id:
        return None
    cache_key = state_cache_key(state_cache_prefix=state_cache_prefix, provider_key=provider_key, state_id=state_id)
    if cache.get(cache_key) is None:
        return None
    cache.delete(cache_key)
    return payload


__all__ = [
    "consume_sso_state",
    "new_sso_state",
]
