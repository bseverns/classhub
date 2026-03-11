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

_TELEMETRY_ROLLOUT_DOCS = [
    "docs/TELEMETRY_DB_SPLIT_PLAN.md",
    "docs/RUNBOOK.md",
    "docs/DECISIONS.md",
]

_TELEMETRY_ROLLOUT_COMMANDS = [
    "bash scripts/telemetry_stabilization_evidence.sh --window-days 7 --perform-rollback-drill",
    "cd /srv/lms/app/compose && docker compose exec -T classhub_web python manage.py check_telemetry_parity --window-days 7",
]

_RUNTIME_POLICY_LOCK_DOCS = [
    "docs/RUNBOOK.md",
    "docs/30_DAY_STABILITY_PLAN.md",
    "docs/TELEMETRY_DB_SPLIT_PLAN.md",
    "docs/ORG_BOUNDARY_POLICY_AUDIT.md",
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


def _rbac_config_rows():
    return [
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
    ]


def _telemetry_config_rows():
    telemetry_url = str(getattr(settings, "CLASSHUB_TELEMETRY_DATABASE_URL", "") or "").strip()
    return [
        {
            "label": "Telemetry database URL",
            "value": "(configured)" if telemetry_url else "(unset)",
            "source": "env override" if _env_setting("CLASSHUB_TELEMETRY_DATABASE_URL") else "disabled",
        },
        {
            "label": "Telemetry write mode",
            "value": str(getattr(settings, "CLASSHUB_TELEMETRY_WRITE_MODE", "off") or "off"),
            "source": _operator_config_source("CLASSHUB_TELEMETRY_WRITE_MODE", fallback="default"),
        },
        {
            "label": "Telemetry read mode",
            "value": str(getattr(settings, "CLASSHUB_TELEMETRY_READ_MODE", "core") or "core"),
            "source": _operator_config_source("CLASSHUB_TELEMETRY_READ_MODE", fallback="default"),
        },
    ]


def _telemetry_rollout_checks():
    telemetry_url = str(getattr(settings, "CLASSHUB_TELEMETRY_DATABASE_URL", "") or "").strip()
    write_mode = str(getattr(settings, "CLASSHUB_TELEMETRY_WRITE_MODE", "off") or "off").strip().lower()
    read_mode = str(getattr(settings, "CLASSHUB_TELEMETRY_READ_MODE", "core") or "core").strip().lower()
    stabilization_runtime_ready = bool(telemetry_url and write_mode == "dual" and read_mode == "telemetry")
    return [
        {
            "label": "Telemetry database configured",
            "done": bool(telemetry_url),
            "detail": "CLASSHUB_TELEMETRY_DATABASE_URL must be set on this node.",
        },
        {
            "label": "Slice 7 runtime mode active (WRITE_MODE=dual, READ_MODE=telemetry)",
            "done": stabilization_runtime_ready,
            "detail": f"Current modes: write={write_mode}, read={read_mode}.",
        },
        {
            "label": "Parity + rollback evidence captured",
            "done": None,
            "detail": "Manual gate: archive parity/smoke/rollback artifacts for one full release cycle.",
        },
        {
            "label": "Gate D sign-off recorded (steady-state write mode decision)",
            "done": None,
            "detail": "Manual gate: document final decision (dual vs telemetry_only) in DECISIONS.md.",
        },
    ]


def _telemetry_rollout_summary(checks: list[dict]) -> str:
    runtime_checks = [row for row in checks if row.get("done") is not None]
    runtime_complete = all(bool(row.get("done")) for row in runtime_checks)
    if runtime_complete:
        return "Runtime gates are ready; manual evidence/sign-off items remain."
    return "Telemetry split is still in rollout gating; complete pending runtime checks first."


def _runtime_policy_lock_checks():
    require_org_membership = bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False))
    write_mode = str(getattr(settings, "CLASSHUB_TELEMETRY_WRITE_MODE", "off") or "off").strip().lower()
    read_mode = str(getattr(settings, "CLASSHUB_TELEMETRY_READ_MODE", "core") or "core").strip().lower()
    certificate_min_sessions = int(getattr(settings, "CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8) or 8)
    certificate_min_artifacts = int(getattr(settings, "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6) or 6)
    certificate_min_sessions_env = _env_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS")
    certificate_min_artifacts_env = _env_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS")
    return [
        {
            "label": "Org boundary strict mode",
            "expected": "On (1)",
            "value": "On" if require_org_membership else "Off",
            "source": _operator_config_source("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF"),
            "done": require_org_membership,
            "detail": "Expected production lock: REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1.",
        },
        {
            "label": "Telemetry write mode",
            "expected": "dual",
            "value": write_mode,
            "source": _operator_config_source("CLASSHUB_TELEMETRY_WRITE_MODE", fallback="default"),
            "done": write_mode == "dual",
            "detail": f"Current mode: {write_mode}.",
        },
        {
            "label": "Telemetry read mode",
            "expected": "telemetry",
            "value": read_mode,
            "source": _operator_config_source("CLASSHUB_TELEMETRY_READ_MODE", fallback="default"),
            "done": read_mode == "telemetry",
            "detail": f"Current mode: {read_mode}.",
        },
        {
            "label": "Certificate min sessions env",
            "expected": "env override >= 1",
            "value": str(certificate_min_sessions),
            "source": _operator_config_source("CLASSHUB_CERTIFICATE_MIN_SESSIONS", fallback="default"),
            "done": bool(certificate_min_sessions_env) and certificate_min_sessions >= 1,
            "detail": "Set CLASSHUB_CERTIFICATE_MIN_SESSIONS explicitly in runtime env.",
        },
        {
            "label": "Certificate min artifacts env",
            "expected": "env override >= 1",
            "value": str(certificate_min_artifacts),
            "source": _operator_config_source("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", fallback="default"),
            "done": bool(certificate_min_artifacts_env) and certificate_min_artifacts >= 1,
            "detail": "Set CLASSHUB_CERTIFICATE_MIN_ARTIFACTS explicitly in runtime env.",
        },
    ]


def _runtime_policy_lock_summary(checks: list[dict]) -> str:
    runtime_checks = [row for row in checks if row.get("done") is not None]
    if all(bool(row.get("done")) for row in runtime_checks):
        return "All runtime lock checks pass for this node."
    return "Runtime lock mismatch detected; align runtime values before release sign-off."


def _helper_config_rows(*, defaults: dict, helper_config_file: str):
    return [
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


def _operator_config_rows(*, profile: str, helper_config_file: str):
    defaults = _HELPER_POLICY_PROFILE_DEFAULTS[profile]
    rows = [
        {
            "label": "Program profile",
            "value": profile,
            "source": _operator_config_source("CLASSHUB_PROGRAM_PROFILE"),
        },
    ]
    rows.extend(_rbac_config_rows())
    rows.extend(_telemetry_config_rows())
    rows.extend(_helper_config_rows(defaults=defaults, helper_config_file=helper_config_file))
    return rows


def build_operator_config_snapshot(*, user):
    if not user.is_superuser:
        return {
            "show_operator_config_snapshot": False,
            "operator_config_rows": [],
            "operator_config_docs": [],
            "show_runtime_policy_lock": False,
            "runtime_policy_lock_summary": "",
            "runtime_policy_lock_checks": [],
            "runtime_policy_lock_docs": [],
            "show_telemetry_rollout_status": False,
            "telemetry_rollout_summary": "",
            "telemetry_rollout_checks": [],
            "telemetry_rollout_docs": [],
            "telemetry_rollout_commands": [],
        }
    profile = str(getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary") or "secondary").strip().lower()
    if profile not in _HELPER_POLICY_PROFILE_DEFAULTS:
        profile = "secondary"
    helper_config_file = _env_setting("HELPER_CONFIG_FILE")
    rollout_checks = _telemetry_rollout_checks()
    runtime_policy_lock_checks = _runtime_policy_lock_checks()
    return {
        "show_operator_config_snapshot": True,
        "operator_config_rows": _operator_config_rows(profile=profile, helper_config_file=helper_config_file),
        "operator_config_docs": _OPERATOR_CONFIG_DOCS,
        "show_runtime_policy_lock": True,
        "runtime_policy_lock_summary": _runtime_policy_lock_summary(runtime_policy_lock_checks),
        "runtime_policy_lock_checks": runtime_policy_lock_checks,
        "runtime_policy_lock_docs": _RUNTIME_POLICY_LOCK_DOCS,
        "show_telemetry_rollout_status": True,
        "telemetry_rollout_summary": _telemetry_rollout_summary(rollout_checks),
        "telemetry_rollout_checks": rollout_checks,
        "telemetry_rollout_docs": _TELEMETRY_ROLLOUT_DOCS,
        "telemetry_rollout_commands": _TELEMETRY_ROLLOUT_COMMANDS,
    }


__all__ = ["build_operator_config_snapshot"]
