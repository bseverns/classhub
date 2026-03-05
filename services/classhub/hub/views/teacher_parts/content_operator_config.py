"""Operator config snapshot helpers for teacher home."""

import os

from .shared import settings


_HELPER_POLICY_PROFILE_DEFAULTS = {
    "elementary": {"strictness": "strict", "scope_mode": "strict", "topic_filter_mode": "strict"},
    "secondary": {"strictness": "light", "scope_mode": "soft", "topic_filter_mode": "soft"},
    "advanced": {"strictness": "light", "scope_mode": "soft", "topic_filter_mode": "soft"},
}

_OPERATOR_CONFIG_DOCS = [
    "docs/FEATURE_MATURITY.md",
    "docs/START_HERE_EVALUATOR.md",
    "docs/PROGRAM_PROFILES.md",
    "docs/RBAC_GUIDE.md",
    "docs/OPENAI_HELPER.md",
]


def _env_setting(name: str) -> str:
    return str(os.environ.get(name, "") or "").strip()


def _operator_config_source(name: str, *, fallback: str = "default") -> str:
    return "env override" if _env_setting(name) else fallback


def _helper_policy_row(*, label: str, env_name: str, profile_default: str, helper_config_file: str):
    override = _env_setting(env_name)
    if override:
        return {"label": label, "value": override, "source": "env override"}
    source = "profile default (helper YAML may override)" if helper_config_file else "profile default"
    return {"label": label, "value": profile_default, "source": source}


def _operator_config_rows(*, profile: str, helper_config_file: str):
    defaults = _HELPER_POLICY_PROFILE_DEFAULTS[profile]
    return [
        {
            "label": "Program profile",
            "value": profile,
            "source": _operator_config_source("CLASSHUB_PROGRAM_PROFILE"),
        },
        {
            "label": "Require org membership for staff",
            "value": "On" if bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False)) else "Off",
            "source": _operator_config_source("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF"),
        },
        {
            "label": "RBAC scoped grants enforcement",
            "value": "On" if bool(getattr(settings, "CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED", False)) else "Off",
            "source": _operator_config_source("CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED"),
        },
        {
            "label": "RBAC policy approval queue",
            "value": "On" if bool(getattr(settings, "CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED", False)) else "Off",
            "source": _operator_config_source("CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED"),
        },
        {
            "label": "Helper backend",
            "value": str(getattr(settings, "HELPER_LLM_BACKEND", "ollama") or "ollama"),
            "source": _operator_config_source("HELPER_LLM_BACKEND"),
        },
        {
            "label": "Helper YAML config file",
            "value": helper_config_file or "(unset)",
            "source": "env override" if helper_config_file else "none",
        },
        _helper_policy_row(
            label="Helper strictness",
            env_name="HELPER_STRICTNESS",
            profile_default=defaults["strictness"],
            helper_config_file=helper_config_file,
        ),
        _helper_policy_row(
            label="Helper scope mode",
            env_name="HELPER_SCOPE_MODE",
            profile_default=defaults["scope_mode"],
            helper_config_file=helper_config_file,
        ),
        _helper_policy_row(
            label="Helper topic filter mode",
            env_name="HELPER_TOPIC_FILTER_MODE",
            profile_default=defaults["topic_filter_mode"],
            helper_config_file=helper_config_file,
        ),
    ]


def build_operator_config_snapshot(*, user):
    if not user.is_superuser:
        return {
            "show_operator_config_snapshot": False,
            "operator_config_rows": [],
            "operator_config_docs": [],
        }
    profile = str(getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary") or "secondary").strip().lower()
    if profile not in _HELPER_POLICY_PROFILE_DEFAULTS:
        profile = "secondary"
    helper_config_file = _env_setting("HELPER_CONFIG_FILE")
    return {
        "show_operator_config_snapshot": True,
        "operator_config_rows": _operator_config_rows(profile=profile, helper_config_file=helper_config_file),
        "operator_config_docs": _OPERATOR_CONFIG_DOCS,
    }


__all__ = ["build_operator_config_snapshot"]
