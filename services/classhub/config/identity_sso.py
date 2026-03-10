"""Teacher SSO provider configuration parsing and validation.

T0 scope only:
- parse provider config from environment-backed settings,
- validate required fields when enabled,
- expose normalized provider metadata for later T1/T2 auth flow work.
"""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_TEACHER_SSO_PROVIDERS = ("google", "microsoft", "oidc_custom")


def _normalize_provider_key(raw: str) -> str:
    return (raw or "").strip().lower().replace("-", "_")


def _parse_csv(raw: str) -> tuple[str, ...]:
    items: list[str] = []
    for token in (raw or "").split(","):
        normalized = _normalize_provider_key(token)
        if normalized:
            items.append(normalized)
    # Preserve order while removing duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)


def _parse_csv_preserve_case(raw: str) -> tuple[str, ...]:
    items: list[str] = []
    for token in (raw or "").split(","):
        normalized = token.strip()
        if normalized:
            items.append(normalized)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(item)
    return tuple(ordered)


@dataclass(frozen=True)
class TeacherSSOProviderConfig:
    provider_key: str
    client_id: str
    client_secret: str
    issuer: str
    discovery_url: str
    allowed_domains: tuple[str, ...] = ()
    allowed_tenant_ids: tuple[str, ...] = ()
    org_auto_map_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class TeacherSSOSettings:
    enabled: bool
    allow_password_fallback: bool
    enabled_providers: tuple[str, ...]
    providers: dict[str, TeacherSSOProviderConfig]


def _required(value: str, *, key: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise RuntimeError(f"{key} is required when its SSO provider is enabled")
    return normalized


def _build_google_provider(env) -> TeacherSSOProviderConfig:
    return TeacherSSOProviderConfig(
        provider_key="google",
        client_id=_required(env("CLASSHUB_SSO_GOOGLE_CLIENT_ID", default=""), key="CLASSHUB_SSO_GOOGLE_CLIENT_ID"),
        client_secret=_required(
            env("CLASSHUB_SSO_GOOGLE_CLIENT_SECRET", default=""),
            key="CLASSHUB_SSO_GOOGLE_CLIENT_SECRET",
        ),
        issuer=(env("CLASSHUB_SSO_GOOGLE_ISSUER", default="https://accounts.google.com").strip() or "https://accounts.google.com"),
        discovery_url=(
            env(
                "CLASSHUB_SSO_GOOGLE_DISCOVERY_URL",
                default="https://accounts.google.com/.well-known/openid-configuration",
            ).strip()
            or "https://accounts.google.com/.well-known/openid-configuration"
        ),
        allowed_domains=_parse_csv_preserve_case(env("CLASSHUB_SSO_GOOGLE_HOSTED_DOMAINS", default="")),
        org_auto_map_rules=_parse_csv_preserve_case(env("CLASSHUB_SSO_GOOGLE_ORG_AUTO_MAP", default="")),
    )


def _build_microsoft_provider(env) -> TeacherSSOProviderConfig:
    return TeacherSSOProviderConfig(
        provider_key="microsoft",
        client_id=_required(
            env("CLASSHUB_SSO_MICROSOFT_CLIENT_ID", default=""),
            key="CLASSHUB_SSO_MICROSOFT_CLIENT_ID",
        ),
        client_secret=_required(
            env("CLASSHUB_SSO_MICROSOFT_CLIENT_SECRET", default=""),
            key="CLASSHUB_SSO_MICROSOFT_CLIENT_SECRET",
        ),
        issuer=(
            env("CLASSHUB_SSO_MICROSOFT_ISSUER", default="https://login.microsoftonline.com/common/v2.0").strip()
            or "https://login.microsoftonline.com/common/v2.0"
        ),
        discovery_url=(
            env(
                "CLASSHUB_SSO_MICROSOFT_DISCOVERY_URL",
                default="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
            ).strip()
            or "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
        ),
        allowed_tenant_ids=_parse_csv_preserve_case(env("CLASSHUB_SSO_MICROSOFT_TENANT_IDS", default="")),
        org_auto_map_rules=_parse_csv_preserve_case(env("CLASSHUB_SSO_MICROSOFT_ORG_AUTO_MAP", default="")),
    )


def _build_oidc_custom_provider(env) -> TeacherSSOProviderConfig:
    issuer = _required(env("CLASSHUB_SSO_OIDC_CUSTOM_ISSUER", default=""), key="CLASSHUB_SSO_OIDC_CUSTOM_ISSUER")
    discovery_url = _required(
        env("CLASSHUB_SSO_OIDC_CUSTOM_DISCOVERY_URL", default=""),
        key="CLASSHUB_SSO_OIDC_CUSTOM_DISCOVERY_URL",
    )
    return TeacherSSOProviderConfig(
        provider_key="oidc_custom",
        client_id=_required(
            env("CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_ID", default=""),
            key="CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_ID",
        ),
        client_secret=_required(
            env("CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_SECRET", default=""),
            key="CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_SECRET",
        ),
        issuer=issuer,
        discovery_url=discovery_url,
        allowed_domains=_parse_csv_preserve_case(env("CLASSHUB_SSO_OIDC_CUSTOM_ALLOWED_DOMAINS", default="")),
        allowed_tenant_ids=_parse_csv_preserve_case(env("CLASSHUB_SSO_OIDC_CUSTOM_ALLOWED_TENANT_IDS", default="")),
        org_auto_map_rules=_parse_csv_preserve_case(env("CLASSHUB_SSO_OIDC_CUSTOM_ORG_AUTO_MAP", default="")),
    )


def build_teacher_sso_settings(env) -> TeacherSSOSettings:
    enabled = bool(env.bool("CLASSHUB_TEACHER_SSO_ENABLED", default=False))
    allow_password_fallback = bool(env.bool("CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK", default=True))
    enabled_providers = _parse_csv(env("CLASSHUB_TEACHER_SSO_PROVIDERS", default=""))

    if not enabled:
        return TeacherSSOSettings(
            enabled=False,
            allow_password_fallback=allow_password_fallback,
            enabled_providers=(),
            providers={},
        )

    if not enabled_providers:
        raise RuntimeError("CLASSHUB_TEACHER_SSO_PROVIDERS is required when CLASSHUB_TEACHER_SSO_ENABLED=1")

    unknown = [provider for provider in enabled_providers if provider not in SUPPORTED_TEACHER_SSO_PROVIDERS]
    if unknown:
        supported = ", ".join(SUPPORTED_TEACHER_SSO_PROVIDERS)
        unknown_str = ", ".join(sorted(unknown))
        raise RuntimeError(
            f"CLASSHUB_TEACHER_SSO_PROVIDERS has unsupported provider(s): {unknown_str}. Supported: {supported}"
        )

    provider_configs: dict[str, TeacherSSOProviderConfig] = {}
    for provider in enabled_providers:
        if provider == "google":
            provider_configs[provider] = _build_google_provider(env)
        elif provider == "microsoft":
            provider_configs[provider] = _build_microsoft_provider(env)
        elif provider == "oidc_custom":
            provider_configs[provider] = _build_oidc_custom_provider(env)

    return TeacherSSOSettings(
        enabled=True,
        allow_password_fallback=allow_password_fallback,
        enabled_providers=enabled_providers,
        providers=provider_configs,
    )


__all__ = [
    "SUPPORTED_TEACHER_SSO_PROVIDERS",
    "TeacherSSOProviderConfig",
    "TeacherSSOSettings",
    "build_teacher_sso_settings",
]

