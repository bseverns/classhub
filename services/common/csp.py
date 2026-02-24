"""Shared CSP mode resolution for Class Hub and Homework Helper."""

from __future__ import annotations


VALID_CSP_MODES = {"relaxed", "report-only", "strict"}


def normalize_csp_mode(raw_mode: str | None, *, default: str = "relaxed") -> str:
    """Normalize CSP mode aliases and validate allowed values."""
    mode = (raw_mode or "").strip().lower()
    if not mode:
        mode = default
    if mode in {"report_only", "reportonly"}:
        mode = "report-only"
    if mode not in VALID_CSP_MODES:
        valid = ", ".join(sorted(VALID_CSP_MODES))
        raise ValueError(f"invalid CSP mode '{raw_mode}'; expected one of: {valid}")
    return mode


def resolve_csp_headers(
    *,
    mode: str,
    relaxed_policy: str,
    strict_policy: str,
    explicit_policy: str = "",
    explicit_report_only_policy: str = "",
    mode_defaults_enabled: bool = True,
) -> tuple[str, str]:
    """Resolve effective enforced/report-only CSP header values."""
    if mode_defaults_enabled:
        normalized_mode = normalize_csp_mode(mode)
        relaxed = (relaxed_policy or "").strip()
        strict = (strict_policy or "").strip()
        if normalized_mode == "relaxed":
            enforced, report_only = relaxed, strict
        elif normalized_mode == "report-only":
            enforced, report_only = "", strict
        else:
            enforced, report_only = strict, ""
    else:
        enforced, report_only = "", ""

    explicit_enforced = (explicit_policy or "").strip()
    explicit_report_only = (explicit_report_only_policy or "").strip()
    if explicit_enforced:
        enforced = explicit_enforced
    if explicit_report_only:
        report_only = explicit_report_only
    return enforced, report_only
