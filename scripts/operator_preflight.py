#!/usr/bin/env python3
"""Operator preflight for deploy-time env coherence checks."""

from __future__ import annotations

import argparse
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_ENV_FILE = Path("compose/.env")
ALLOWED_CADDY_TEMPLATES = {
    "Caddyfile.local",
    "Caddyfile.domain",
    "Caddyfile.domain.assets",
}
ALLOWED_CADDY_EXTRA_CONFIGS = {
    "Caddyfile.extra.empty",
    "Caddyfile.extra.static-site",
}
REMOTE_COMPUTE_ENABLED_KEYS = (
    "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED",
    "HELPER_REMOTE_COMPUTE_ENABLED",
)
REMOTE_COMPUTE_ACK_KEYS = (
    "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED",
    "HELPER_REMOTE_MODE_ACKNOWLEDGED",
)
INTERNAL_URL_CONTRACTS = {
    "HELPER_INTERNAL_RESET_URL": "/helper/internal/reset-class-conversations",
    "HELPER_INTERNAL_ACTOR_CLEAR_URL": "/helper/internal/clear-actor-conversations",
    "HELPER_INTERNAL_RAG_STATUS_URL": "/helper/internal/rag-status",
    "CLASSHUB_INTERNAL_EVENTS_URL": "/internal/events/helper-chat-access",
}
REMOTE_COMPUTE_INTERNAL_URL_CONTRACTS = {
    "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL": "/helper/internal/remote-compute-status",
    "HELPER_INTERNAL_REMOTE_COMPUTE_CONTROL_URL": "/helper/internal/remote-compute-control",
}

_DNS_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def public_dns_hostname_error(raw: str) -> str:
    hostname = str(raw or "").strip()
    if not hostname:
        return "hostname is required"
    if len(hostname) > 253:
        return "hostname must be at most 253 characters"
    if hostname.lower() == "localhost":
        return "localhost is not a public DNS hostname"
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return "IP literals are not valid for public domain mode"
    if "." not in hostname:
        return "public domain mode requires a dotted DNS hostname"
    labels = hostname.split(".")
    if any(not _DNS_LABEL_RE.fullmatch(label) for label in labels):
        return "hostname contains an invalid DNS label"
    if labels[-1].isdigit():
        return "hostname must not end in a numeric-only DNS label"
    return ""


REMOTE_COMPUTE_PROVIDER_URL_KEYS = (
    "HELPER_REMOTE_COMPUTE_ACTIVATE_URL",
    "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL",
    "HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL",
)
VALID_LLM_BACKENDS = {
    "ollama",
    "openai_compatible",
    "openai",
    "openai_responses",
    "mock",
}


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    detail: str


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"missing env file: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _value(values: dict[str, str], *keys: str) -> str:
    for key in keys:
        raw = (values.get(key) or "").strip()
        if raw:
            return raw
    return ""


def _split_csv(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def _bool_value(raw: str, *, default: bool = False) -> bool:
    token = (raw or "").strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _is_placeholder_host(host: str) -> bool:
    token = host.strip().lower()
    if not token:
        return True
    if token in {"lms.example.org", "assets.example.org", "hs.creatempls.org"}:
        return True
    if token.endswith(".example.org") or token.endswith(".example.com") or token.endswith(".example.net"):
        return True
    if "<your-domain>" in token or "<your-base-domain>" in token:
        return True
    return False


def _parsed_url(raw: str):
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed


def _url_host(raw: str) -> str:
    parsed = _parsed_url(raw)
    return (parsed.hostname or "").strip().lower() if parsed else ""


def _is_local_host(host: str) -> bool:
    return host in {"", "localhost", "127.0.0.1", "ollama", "classhub_ollama", "helper_web", "classhub_web"}


def _add_issue(issues: list[Issue], level: str, code: str, detail: str) -> None:
    issues.append(Issue(level=level, code=code, detail=detail))


def _check_required_exact_url(
    *,
    values: dict[str, str],
    key: str,
    expected_path: str,
    issues: list[Issue],
) -> None:
    raw = _value(values, key)
    if not raw:
        _add_issue(issues, "FAIL", "missing_url", f"{key} must be set")
        return
    parsed = _parsed_url(raw)
    if not parsed:
        _add_issue(issues, "FAIL", "invalid_url", f"{key} must be an absolute http(s) URL")
        return
    if parsed.path != expected_path:
        _add_issue(issues, "FAIL", "wrong_path", f"{key} must use path {expected_path}")


def _check_domain_mode(values: dict[str, str], issues: list[Issue], *, template_mode: bool, assets_mode: bool) -> None:
    domain = _value(values, "DOMAIN").lower()
    if not domain:
        _add_issue(issues, "FAIL", "missing_domain", "DOMAIN must be set for domain/TLS Caddy modes")
    elif _is_placeholder_host(domain):
        level = "WARN" if template_mode else "FAIL"
        _add_issue(level == "WARN" and issues or issues, level, "placeholder_domain", "DOMAIN still looks like a placeholder")
    elif hostname_error := public_dns_hostname_error(domain):
        _add_issue(issues, "FAIL", "invalid_public_domain", hostname_error)

    allowed_hosts = _split_csv(_value(values, "DJANGO_ALLOWED_HOSTS"))
    if domain and domain not in allowed_hosts:
        level = "WARN" if template_mode else "FAIL"
        _add_issue(issues, level, "missing_allowed_host", f"DJANGO_ALLOWED_HOSTS should include {domain}")

    csrf_origins = _split_csv(_value(values, "CSRF_TRUSTED_ORIGINS"))
    expected_origin = f"https://{domain}" if domain else ""
    if expected_origin and expected_origin.lower() not in csrf_origins:
        level = "WARN" if template_mode else "FAIL"
        _add_issue(issues, level, "missing_csrf_origin", f"CSRF_TRUSTED_ORIGINS should include {expected_origin}")

    if _value(values, "DJANGO_SESSION_COOKIE_SECURE") != "1":
        _add_issue(issues, "FAIL", "cookie_secure", "DJANGO_SESSION_COOKIE_SECURE must be 1 in domain/TLS mode")
    if _value(values, "DJANGO_CSRF_COOKIE_SECURE") != "1":
        _add_issue(issues, "FAIL", "csrf_cookie_secure", "DJANGO_CSRF_COOKIE_SECURE must be 1 in domain/TLS mode")
    if _value(values, "REQUEST_SAFETY_TRUST_PROXY_HEADERS") != "1":
        _add_issue(issues, "FAIL", "proxy_headers", "REQUEST_SAFETY_TRUST_PROXY_HEADERS must be 1 in domain/TLS mode")

    if not assets_mode:
        asset_base_url = _value(values, "CLASSHUB_ASSET_BASE_URL")
        if asset_base_url:
            _add_issue(
                issues,
                "WARN",
                "unused_asset_base_url",
                "CLASSHUB_ASSET_BASE_URL is set while CADDYFILE_TEMPLATE is not Caddyfile.domain.assets",
            )
        return

    asset_domain = _value(values, "ASSET_DOMAIN").lower()
    if not asset_domain:
        _add_issue(issues, "FAIL", "missing_asset_domain", "ASSET_DOMAIN must be set in asset-host mode")
    elif _is_placeholder_host(asset_domain):
        level = "WARN" if template_mode else "FAIL"
        _add_issue(issues, level, "placeholder_asset_domain", "ASSET_DOMAIN still looks like a placeholder")
    elif hostname_error := public_dns_hostname_error(asset_domain):
        _add_issue(issues, "FAIL", "invalid_public_asset_domain", hostname_error)

    if asset_domain and asset_domain not in allowed_hosts:
        level = "WARN" if template_mode else "FAIL"
        _add_issue(issues, level, "missing_asset_allowed_host", f"DJANGO_ALLOWED_HOSTS should include {asset_domain}")

    asset_base_url = _value(values, "CLASSHUB_ASSET_BASE_URL")
    expected_asset_base = f"https://{asset_domain}" if asset_domain else ""
    if not asset_base_url:
        level = "WARN" if template_mode else "FAIL"
        _add_issue(
            issues,
            level,
            "missing_asset_base_url",
            "CLASSHUB_ASSET_BASE_URL must be set when using Caddyfile.domain.assets",
        )
    elif expected_asset_base and asset_base_url.rstrip("/") != expected_asset_base:
        level = "WARN" if template_mode else "FAIL"
        _add_issue(
            issues,
            level,
            "asset_base_url_mismatch",
            f"CLASSHUB_ASSET_BASE_URL should be {expected_asset_base}",
        )


def _check_local_mode(values: dict[str, str], issues: list[Issue]) -> None:
    allowed_hosts = _split_csv(_value(values, "DJANGO_ALLOWED_HOSTS"))
    for host in ("localhost", "127.0.0.1"):
        if host not in allowed_hosts:
            _add_issue(issues, "FAIL", "missing_local_allowed_host", f"DJANGO_ALLOWED_HOSTS should include {host}")
    csrf_origins = _split_csv(_value(values, "CSRF_TRUSTED_ORIGINS"))
    if "http://localhost" not in csrf_origins:
        _add_issue(issues, "FAIL", "missing_local_csrf_origin", "CSRF_TRUSTED_ORIGINS should include http://localhost")
    if _value(values, "DJANGO_SESSION_COOKIE_SECURE") != "0":
        _add_issue(issues, "FAIL", "local_cookie_secure", "DJANGO_SESSION_COOKIE_SECURE must be 0 in local HTTP mode")
    if _value(values, "DJANGO_CSRF_COOKIE_SECURE") != "0":
        _add_issue(issues, "FAIL", "local_csrf_cookie_secure", "DJANGO_CSRF_COOKIE_SECURE must be 0 in local HTTP mode")


def _check_caddy_extra(values: dict[str, str], issues: list[Issue], *, caddy_template: str) -> None:
    extra_template = _value(values, "CADDY_EXTRA_CONFIG_TEMPLATE") or "Caddyfile.extra.empty"
    if extra_template not in ALLOWED_CADDY_EXTRA_CONFIGS:
        _add_issue(
            issues,
            "FAIL",
            "invalid_caddy_extra_config",
            "CADDY_EXTRA_CONFIG_TEMPLATE must be Caddyfile.extra.empty or Caddyfile.extra.static-site",
        )
        return
    if extra_template != "Caddyfile.extra.static-site":
        return

    if caddy_template == "Caddyfile.local":
        _add_issue(
            issues,
            "FAIL",
            "static_site_requires_domain_mode",
            "Caddyfile.extra.static-site requires a domain/TLS Caddyfile template",
        )

    root_path = _value(values, "CADDY_STATIC_SITE_ROOT_HOST")
    if not root_path:
        _add_issue(issues, "FAIL", "missing_static_site_root", "CADDY_STATIC_SITE_ROOT_HOST must be set")
    elif root_path in {"/", ".", "~"}:
        _add_issue(
            issues,
            "FAIL",
            "unsafe_static_site_root",
            "CADDY_STATIC_SITE_ROOT_HOST must identify a dedicated site directory",
        )

    static_domains = _split_csv(_value(values, "CADDY_STATIC_SITE_DOMAINS"))
    if not static_domains:
        _add_issue(issues, "FAIL", "missing_static_site_domains", "CADDY_STATIC_SITE_DOMAINS must be set")
        return

    reserved_domains = {_value(values, "DOMAIN").lower(), _value(values, "ASSET_DOMAIN").lower()} - {""}
    for hostname in static_domains:
        if _is_placeholder_host(hostname):
            _add_issue(
                issues,
                "FAIL",
                "placeholder_static_site_domain",
                f"static site hostname is a placeholder: {hostname}",
            )
        elif hostname_error := public_dns_hostname_error(hostname):
            _add_issue(issues, "FAIL", "invalid_static_site_domain", f"{hostname}: {hostname_error}")
        if hostname in reserved_domains:
            _add_issue(
                issues,
                "FAIL",
                "conflicting_static_site_domain",
                f"static site hostname conflicts with an LMS or asset hostname: {hostname}",
            )


def _check_llm_contract(
    values: dict[str, str],
    issues: list[Issue],
    *,
    template_mode: bool,
    domain_mode: bool,
) -> None:
    if not _bool_value(_value(values, "LLM_ENABLED"), default=True):
        return

    backend = _value(values, "LLM_BACKEND", "HELPER_LLM_BACKEND").lower() or "ollama"
    if backend not in VALID_LLM_BACKENDS:
        _add_issue(issues, "FAIL", "invalid_llm_backend", f"LLM_BACKEND/HELPER_LLM_BACKEND '{backend}' is not supported")
        return
    if backend in {"mock", "openai", "openai_responses"}:
        return

    base_url = _value(values, "LLM_BASE_URL", "OLLAMA_BASE_URL")
    if not base_url:
        _add_issue(issues, "FAIL", "missing_llm_base_url", "LLM_BASE_URL/OLLAMA_BASE_URL must be set when LLM is enabled")
        return
    parsed = _parsed_url(base_url)
    if not parsed:
        _add_issue(issues, "FAIL", "invalid_llm_base_url", "LLM_BASE_URL/OLLAMA_BASE_URL must be an absolute http(s) URL")
        return

    model = _value(values, "LLM_MODEL", "OLLAMA_MODEL")
    if not model:
        _add_issue(issues, "FAIL", "missing_llm_model", "LLM_MODEL/OLLAMA_MODEL must be set when LLM is enabled")

    remote_backend = not _is_local_host((parsed.hostname or "").lower())
    if backend == "openai_compatible" and not _value(values, "LLM_API_KEY"):
        _add_issue(issues, "FAIL", "missing_llm_api_key", "LLM_API_KEY must be set for LLM_BACKEND=openai_compatible")
    if domain_mode and remote_backend and parsed.scheme != "https":
        _add_issue(issues, "FAIL", "remote_llm_https", "Remote/private LLM_BASE_URL must use HTTPS in domain/TLS mode")

    public_domain = _value(values, "DOMAIN").lower()
    if public_domain and (parsed.hostname or "").lower() == public_domain:
        _add_issue(
            issues,
            "WARN",
            "llm_host_matches_public_domain",
            "LLM_BASE_URL points at the public LMS domain; private helper backends should stay on a separate host",
        )

    if remote_backend and _value(values, *REMOTE_COMPUTE_ACK_KEYS) != "1":
        level = "WARN" if template_mode else "FAIL"
        _add_issue(
            issues,
            level,
            "remote_llm_not_acknowledged",
            "Remote/private helper backend is configured but remote helper acknowledgement is not set to 1",
        )


def _check_remote_compute(
    values: dict[str, str],
    issues: list[Issue],
    *,
    template_mode: bool,
) -> None:
    if not _bool_value(_value(values, *REMOTE_COMPUTE_ENABLED_KEYS), default=False):
        return

    if _value(values, *REMOTE_COMPUTE_ACK_KEYS) != "1":
        _add_issue(
            issues,
            "FAIL",
            "remote_compute_not_acknowledged",
            "Remote helper compute is enabled but the paid-usage acknowledgement is not set to 1",
        )

    if not _value(values, "HELPER_INTERNAL_API_TOKEN"):
        _add_issue(issues, "FAIL", "missing_internal_api_token", "HELPER_INTERNAL_API_TOKEN is required for remote compute")

    for key, expected_path in REMOTE_COMPUTE_INTERNAL_URL_CONTRACTS.items():
        _check_required_exact_url(values=values, key=key, expected_path=expected_path, issues=issues)

    for key in REMOTE_COMPUTE_PROVIDER_URL_KEYS:
        raw = _value(values, key)
        if not raw:
            _add_issue(issues, "FAIL", "missing_provider_url", f"{key} must be set when remote compute is enabled")
            continue
        parsed = _parsed_url(raw)
        if not parsed:
            _add_issue(issues, "FAIL", "invalid_provider_url", f"{key} must be an absolute http(s) URL")
            continue
        if parsed.scheme != "https":
            level = "WARN" if template_mode else "FAIL"
            _add_issue(issues, level, "provider_url_https", f"{key} should use HTTPS")

    remote_llm_base_url = _value(values, "REMOTE_LLM_BASE_URL")
    if not remote_llm_base_url:
        _add_issue(issues, "FAIL", "missing_remote_llm_base_url", "REMOTE_LLM_BASE_URL must be set when remote compute is enabled")
    else:
        parsed = _parsed_url(remote_llm_base_url)
        if not parsed:
            _add_issue(issues, "FAIL", "invalid_remote_llm_base_url", "REMOTE_LLM_BASE_URL must be an absolute http(s) URL")
        elif parsed.scheme != "https":
            level = "WARN" if template_mode else "FAIL"
            _add_issue(issues, level, "remote_llm_https", "REMOTE_LLM_BASE_URL should use HTTPS")
    if not _value(values, "REMOTE_LLM_API_KEY"):
        _add_issue(issues, "FAIL", "missing_remote_llm_api_key", "REMOTE_LLM_API_KEY must be set when remote compute is enabled")
    if not _value(values, "REMOTE_LLM_MODEL"):
        _add_issue(issues, "FAIL", "missing_remote_llm_model", "REMOTE_LLM_MODEL must be set when remote compute is enabled")
    if not _value(values, "HELPER_REMOTE_COMPUTE_CONTROL_API_KEY"):
        _add_issue(
            issues,
            "FAIL",
            "missing_remote_compute_control_api_key",
            "HELPER_REMOTE_COMPUTE_CONTROL_API_KEY must be set when remote compute is enabled",
        )


def _check_internal_url_contracts(values: dict[str, str], issues: list[Issue]) -> None:
    for key, expected_path in INTERNAL_URL_CONTRACTS.items():
        _check_required_exact_url(values=values, key=key, expected_path=expected_path, issues=issues)


def run_preflight(env_path: Path) -> tuple[list[Issue], list[Issue]]:
    values = _parse_env_file(env_path)
    template_mode = ".env.example" in env_path.name

    issues: list[Issue] = []

    caddy_template = _value(values, "CADDYFILE_TEMPLATE")
    if caddy_template not in ALLOWED_CADDY_TEMPLATES:
        _add_issue(
            issues,
            "FAIL",
            "invalid_caddy_template",
            "CADDYFILE_TEMPLATE must be one of Caddyfile.local, Caddyfile.domain, or Caddyfile.domain.assets",
        )
    else:
        if caddy_template == "Caddyfile.local":
            _check_local_mode(values, issues)
        else:
            _check_domain_mode(
                values,
                issues,
                template_mode=template_mode,
                assets_mode=(caddy_template == "Caddyfile.domain.assets"),
            )

    _check_caddy_extra(values, issues, caddy_template=caddy_template)

    _check_internal_url_contracts(values, issues)
    _check_llm_contract(
        values,
        issues,
        template_mode=template_mode,
        domain_mode=(caddy_template != "Caddyfile.local"),
    )
    _check_remote_compute(values, issues, template_mode=template_mode)

    if _bool_value(_value(values, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF"), default=False):
        _add_issue(
            issues,
            "WARN",
            "organization_assignment_required",
            "Strict multi-org mode is enabled: verify every class has an organization before release; legacy organization-less classes are not visible to scoped staff.",
        )
    if not _bool_value(_value(values, "CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN"), default=False):
        _add_issue(
            issues,
            "WARN",
            "display_name_rejoin_single_instructor_risk",
            "Display-name rejoin is suitable only for the current single-instructor workflow; when multiple instructors are introduced, set CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1.",
        )

    failures = [issue for issue in issues if issue.level == "FAIL"]
    warnings = [issue for issue in issues if issue.level == "WARN"]
    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deploy-time operator env coherence.")
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to env file (default: compose/.env)",
    )
    parser.add_argument(
        "--validate-public-hostname",
        help="Validate one hostname for public domain mode and exit.",
    )
    args = parser.parse_args()

    if args.validate_public_hostname is not None:
        if hostname_error := public_dns_hostname_error(args.validate_public_hostname):
            print(f"[operator-preflight] FAIL: {hostname_error}")
            return 1
        print(f"[operator-preflight] OK (public hostname: {args.validate_public_hostname})")
        return 0

    env_path = Path(args.env_file)
    try:
        failures, warnings = run_preflight(env_path)
    except FileNotFoundError as exc:
        print(f"[operator-preflight] FAIL: {exc}")
        return 1

    if warnings:
        print(f"[operator-preflight] WARN ({len(warnings)})")
        for warning in warnings:
            print(f"  - [{warning.code}] {warning.detail}")

    if failures:
        print(f"[operator-preflight] FAIL ({len(failures)})")
        for failure in failures:
            print(f"  - [{failure.code}] {failure.detail}")
        return 1

    print(f"[operator-preflight] OK ({env_path.as_posix()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
