"""Scope/context resolution for helper requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ContextEnvelope:
    scope_token: str
    context: str
    topics: list[str]
    allowed_topics: list[str]
    reference_key: str
    scope_verified: bool
    ignored_unsigned_scope_fields: bool = False


class ScopeResolutionError(ValueError):
    """Raised when signed scope requirements fail."""

    def __init__(self, *, response_error: str, log_event: str, log_level: str = "warning"):
        super().__init__(response_error)
        self.response_error = response_error
        self.log_event = log_event
        self.log_level = log_level


def resolve_context_envelope(
    *,
    payload: dict,
    actor_type: str,
    require_scope_for_staff: bool,
    max_scope_token_age_seconds: int,
    load_scope_from_token: Callable[..., dict],
    signature_expired_exc: type[Exception],
    bad_signature_exc: type[Exception],
) -> ContextEnvelope:
    scope_token = str(payload.get("scope_token") or "").strip()
    if scope_token:
        try:
            scope = load_scope_from_token(
                scope_token,
                max_age_seconds=max(max_scope_token_age_seconds, 60),
            )
        except signature_expired_exc as exc:
            raise ScopeResolutionError(
                response_error="invalid_scope_token",
                log_event="scope_token_expired",
            ) from exc
        except (bad_signature_exc, ValueError) as exc:
            raise ScopeResolutionError(
                response_error="invalid_scope_token",
                log_event="scope_token_invalid",
            ) from exc
        return ContextEnvelope(
            scope_token=scope_token,
            context=str(scope.get("context", "") or ""),
            topics=list(scope.get("topics", []) or []),
            allowed_topics=list(scope.get("allowed_topics", []) or []),
            reference_key=str(scope.get("reference", "") or ""),
            scope_verified=True,
        )

    if actor_type == "student" or (actor_type == "staff" and require_scope_for_staff):
        raise ScopeResolutionError(
            response_error="missing_scope_token",
            log_event="scope_token_missing",
        )

    ignored_unsigned_scope_fields = any(payload.get(k) for k in ("context", "topics", "allowed_topics", "reference"))
    return ContextEnvelope(
        scope_token="",
        context="",
        topics=[],
        allowed_topics=[],
        reference_key="",
        scope_verified=False,
        ignored_unsigned_scope_fields=ignored_unsigned_scope_fields,
    )


__all__ = ["ContextEnvelope", "ScopeResolutionError", "resolve_context_envelope"]
