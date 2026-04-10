"""Access guard for helper internal control/status endpoints."""

from __future__ import annotations

import ipaddress

from common.request_safety import client_ip_from_request

from .engine import runtime as engine_runtime
from .engine.config_source import helper_getenv
from .internal_audit import log_internal_audit_event

_DEFAULT_ALLOWED_CIDRS = (
    "127.0.0.0/8",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
)


def _env_bool(name: str, default: bool) -> bool:
    return engine_runtime.env_bool(name, default, getenv=helper_getenv)


def _env_int(name: str, default: int) -> int:
    return engine_runtime.env_int(name, default, getenv=helper_getenv)


def _allowed_networks() -> tuple[ipaddress._BaseNetwork, ...]:
    raw = (helper_getenv("HELPER_INTERNAL_ALLOWED_CIDRS", "") or "").strip()
    values = [item.strip() for item in raw.split(",") if item.strip()] if raw else list(_DEFAULT_ALLOWED_CIDRS)
    networks: list[ipaddress._BaseNetwork] = []
    for value in values:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def authorize_internal_request(*, request, request_id: str, event_prefix: str) -> tuple[bool, str]:
    client_ip = client_ip_from_request(
        request,
        trust_proxy_headers=_env_bool("HELPER_INTERNAL_TRUST_PROXY_HEADERS", False),
        xff_index=max(_env_int("HELPER_INTERNAL_XFF_INDEX", 0), 0),
    )
    try:
        parsed_ip = ipaddress.ip_address(client_ip)
    except ValueError:
        parsed_ip = None

    if parsed_ip is not None and any(parsed_ip in network for network in _allowed_networks()):
        return True, str(parsed_ip)

    log_internal_audit_event(
        "warning",
        f"{event_prefix}_ip_forbidden",
        request=request,
        request_id=request_id,
        caller_ip=client_ip,
    )
    return False, client_ip


__all__ = ["authorize_internal_request"]
