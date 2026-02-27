"""Program-profile aware helper runtime policy defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


PROFILE_ENV_DEFAULTS = {
    "elementary": {
        "HELPER_STRICTNESS": "strict",
        "HELPER_SCOPE_MODE": "strict",
        "HELPER_TOPIC_FILTER_MODE": "strict",
    },
    "secondary": {
        "HELPER_STRICTNESS": "light",
        "HELPER_SCOPE_MODE": "soft",
        "HELPER_TOPIC_FILTER_MODE": "soft",
    },
    "advanced": {
        "HELPER_STRICTNESS": "light",
        "HELPER_SCOPE_MODE": "soft",
        "HELPER_TOPIC_FILTER_MODE": "soft",
    },
}


@dataclass(frozen=True)
class PolicyBundle:
    program_profile: str
    strictness: str
    scope_mode: str
    topic_filter_mode: str


def resolve_program_profile(*, getenv: Callable[[str, str], str] = os.getenv) -> str:
    value = (getenv("CLASSHUB_PROGRAM_PROFILE", "secondary") or "secondary").strip().lower()
    if value in PROFILE_ENV_DEFAULTS:
        return value
    return "secondary"


def env_or_profile_default(
    env_name: str,
    fallback: str,
    *,
    profile: str | None = None,
    getenv: Callable[[str, str], str] = os.getenv,
) -> str:
    explicit = (getenv(env_name, "") or "").strip()
    if explicit:
        return explicit
    program_profile = profile or resolve_program_profile(getenv=getenv)
    profile_defaults = PROFILE_ENV_DEFAULTS.get(program_profile, {})
    return str(profile_defaults.get(env_name, fallback))


def resolve_policy_bundle(*, getenv: Callable[[str, str], str] = os.getenv) -> PolicyBundle:
    program_profile = resolve_program_profile(getenv=getenv)
    return PolicyBundle(
        program_profile=program_profile,
        strictness=env_or_profile_default(
            "HELPER_STRICTNESS",
            "light",
            profile=program_profile,
            getenv=getenv,
        ).lower(),
        scope_mode=env_or_profile_default(
            "HELPER_SCOPE_MODE",
            "soft",
            profile=program_profile,
            getenv=getenv,
        ).lower(),
        topic_filter_mode=env_or_profile_default(
            "HELPER_TOPIC_FILTER_MODE",
            "soft",
            profile=program_profile,
            getenv=getenv,
        ).lower(),
    )


__all__ = [
    "PROFILE_ENV_DEFAULTS",
    "PolicyBundle",
    "env_or_profile_default",
    "resolve_policy_bundle",
    "resolve_program_profile",
]
