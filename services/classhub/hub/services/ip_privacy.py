"""Helpers for minimizing stored IP precision in student events."""

from __future__ import annotations

import ipaddress

from django.conf import settings


def minimize_student_event_ip(ip_address_value: str) -> str:
    raw = str(ip_address_value or "").strip()
    if not raw:
        return ""
    try:
        parsed = ipaddress.ip_address(raw)
    except ValueError:
        return ""

    mode = str(getattr(settings, "CLASSHUB_STUDENT_EVENT_IP_MODE", "truncate") or "truncate").strip().lower()
    if mode == "full":
        return str(parsed)
    if mode in {"none", "drop", "off", "disabled"}:
        return ""

    if parsed.version == 4:
        return str(ipaddress.ip_network(f"{parsed}/24", strict=False).network_address)
    return str(ipaddress.ip_network(f"{parsed}/56", strict=False).network_address)

