"""Google teacher SSO service helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.core.cache import cache

_DISCOVERY_CACHE_TTL_SECONDS = 3600
_GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    hosted_domain: str


def _json_request(
    url: str,
    *,
    method: str = "GET",
    form_data: dict[str, str] | None = None,
    timeout_seconds: int = 8,
) -> dict:
    headers = {"Accept": "application/json"}
    body: bytes | None = None
    if form_data is not None:
        body = urlencode(form_data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload or "{}")
    if isinstance(parsed, dict):
        return parsed
    raise RuntimeError("Unexpected non-object JSON response")


def load_provider_discovery(*, provider_key: str, provider) -> dict:
    if provider is None:
        raise RuntimeError("Provider configuration missing")
    discovery_url = (getattr(provider, "discovery_url", "") or "").strip()
    if not discovery_url:
        raise RuntimeError("Provider discovery URL missing")
    cache_key = f"teacher_sso_discovery:{provider_key}:{discovery_url}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    doc = _json_request(discovery_url, timeout_seconds=8)
    required_keys = ("authorization_endpoint", "token_endpoint")
    for key in required_keys:
        if not str(doc.get(key, "")).strip():
            raise RuntimeError(f"OIDC discovery missing {key}")
    cache.set(cache_key, doc, timeout=_DISCOVERY_CACHE_TTL_SECONDS)
    return doc


def _google_allowed_domain(*, provider, identity: GoogleIdentity) -> bool:
    raw_domains = getattr(provider, "allowed_domains", ()) or ()
    allowed = {str(domain).strip().lower() for domain in raw_domains if str(domain).strip()}
    if not allowed:
        return True
    email_domain = identity.email.split("@", 1)[-1].lower()
    hosted_domain = identity.hosted_domain.lower()
    return email_domain in allowed or (hosted_domain and hosted_domain in allowed)


def exchange_google_code_for_identity(
    *,
    provider,
    code: str,
    redirect_uri: str,
    expected_nonce: str,
) -> GoogleIdentity:
    discovery = load_provider_discovery(provider_key="google", provider=provider)
    token_response = _json_request(
        str(discovery["token_endpoint"]),
        method="POST",
        form_data={
            "code": code,
            "client_id": str(provider.client_id),
            "client_secret": str(provider.client_secret),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout_seconds=10,
    )
    id_token = str(token_response.get("id_token", "")).strip()
    if not id_token:
        raise RuntimeError("Google token response missing id_token")
    tokeninfo = _json_request(
        f"{_GOOGLE_TOKENINFO_ENDPOINT}?{urlencode({'id_token': id_token})}",
        timeout_seconds=8,
    )
    audience = str(tokeninfo.get("aud", "")).strip()
    issuer = str(tokeninfo.get("iss", "")).strip()
    nonce = str(tokeninfo.get("nonce", "")).strip()
    email = str(tokeninfo.get("email", "")).strip()
    email_verified_raw = str(tokeninfo.get("email_verified", "")).strip().lower()
    hosted_domain = str(tokeninfo.get("hd", "")).strip()
    if audience != str(provider.client_id).strip():
        raise RuntimeError("Google token audience mismatch")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise RuntimeError("Google token issuer mismatch")
    if nonce != expected_nonce:
        raise RuntimeError("Google token nonce mismatch")
    if email_verified_raw not in {"1", "true"}:
        raise RuntimeError("Google account email is not verified")
    if "@" not in email:
        raise RuntimeError("Google token missing valid email")
    identity = GoogleIdentity(email=email, hosted_domain=hosted_domain)
    if not _google_allowed_domain(provider=provider, identity=identity):
        raise RuntimeError("Google account domain not allowed")
    return identity


def staff_user_for_email(email: str):
    user_model = get_user_model()
    matches = list(user_model.objects.filter(email__iexact=email, is_active=True, is_staff=True).order_by("id")[:2])
    if len(matches) == 1:
        return matches[0]
    if not matches:
        username_matches = list(
            user_model.objects.filter(username__iexact=email, is_active=True, is_staff=True).order_by("id")[:2]
        )
        if len(username_matches) == 1:
            return username_matches[0]
    return None


__all__ = [
    "GoogleIdentity",
    "exchange_google_code_for_identity",
    "load_provider_discovery",
    "staff_user_for_email",
]
