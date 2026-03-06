"""Unified telemetry write service for core + telemetry DB modes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent

from ..models import StudentEvent, StudentOutcomeEvent
from .telemetry_split import (
    record_dual_write_attempt,
    record_dual_write_failure,
    record_dual_write_success,
)

logger = logging.getLogger(__name__)

_WRITE_MODE_OFF = "off"
_WRITE_MODE_DUAL = "dual"
_WRITE_MODE_TELEMETRY_ONLY = "telemetry_only"


@dataclass(frozen=True)
class TelemetryWriteResult:
    core_written: bool = False
    telemetry_written: bool = False
    core_error: str = ""
    telemetry_error: str = ""


def _write_mode() -> str:
    value = str(getattr(settings, "CLASSHUB_TELEMETRY_WRITE_MODE", _WRITE_MODE_OFF) or _WRITE_MODE_OFF).strip().lower()
    if value not in {_WRITE_MODE_OFF, _WRITE_MODE_DUAL, _WRITE_MODE_TELEMETRY_ONLY}:
        return _WRITE_MODE_OFF
    return value


def _scalar_id(*, obj=None, explicit_id=None) -> int | None:
    if explicit_id is not None:
        try:
            value = int(explicit_id)
        except Exception:
            return None
        return value if value > 0 else None
    if obj is None:
        return None
    value = getattr(obj, "pk", None)
    try:
        value = int(value)
    except Exception:
        return None
    return value if value > 0 else None


def _relation_kwargs(*, relation_name: str, relation_obj=None, relation_id=None) -> dict:
    if relation_obj is not None:
        return {relation_name: relation_obj}
    resolved_id = _scalar_id(explicit_id=relation_id)
    if resolved_id is None:
        return {}
    return {f"{relation_name}_id": resolved_id}


def _targets_for_mode(mode: str) -> tuple[str, ...]:
    if mode == _WRITE_MODE_TELEMETRY_ONLY:
        return ("telemetry",)
    if mode == _WRITE_MODE_DUAL:
        return ("core", "telemetry")
    return ("core",)


def _record_attempt(*, write_source: str, target: str) -> None:
    record_dual_write_attempt(source=write_source, target=target)


def _record_success(*, write_source: str, target: str) -> None:
    record_dual_write_success(source=write_source, target=target)


def _record_failure(*, write_source: str, target: str, exc: Exception) -> None:
    record_dual_write_failure(
        source=write_source,
        target=target,
        error=exc.__class__.__name__,
    )


def write_student_event(
    *,
    event_type: str,
    source: str,
    details: dict | None = None,
    classroom=None,
    student=None,
    classroom_id=None,
    student_id=None,
    ip_address: str | None = None,
    write_source: str = "student_event",
    raise_on_error: bool = True,
) -> TelemetryWriteResult:
    mode = _write_mode()
    payload_details = details or {}
    core_error = ""
    telemetry_error = ""
    core_written = False
    telemetry_written = False

    core_payload = {
        **_relation_kwargs(relation_name="classroom", relation_obj=classroom, relation_id=classroom_id),
        **_relation_kwargs(relation_name="student", relation_obj=student, relation_id=student_id),
        "event_type": event_type,
        "source": source,
        "details": payload_details,
        "ip_address": ip_address,
    }
    telemetry_payload = {
        "classroom_id": _scalar_id(obj=classroom, explicit_id=classroom_id),
        "student_id": _scalar_id(obj=student, explicit_id=student_id),
        "event_type": event_type,
        "source": source,
        "details": payload_details,
        "ip_address": ip_address,
    }

    for target in _targets_for_mode(mode):
        _record_attempt(write_source=write_source, target=target)
        try:
            if target == "core":
                StudentEvent.objects.create(**core_payload)
                core_written = True
            else:
                TelemetryStudentEvent.objects.create(**telemetry_payload)
                telemetry_written = True
        except Exception as exc:
            _record_failure(write_source=write_source, target=target, exc=exc)
            if target == "core":
                core_error = exc.__class__.__name__
                if raise_on_error:
                    raise
            else:
                telemetry_error = exc.__class__.__name__
                if mode == _WRITE_MODE_TELEMETRY_ONLY and raise_on_error:
                    raise
                logger.warning(
                    "telemetry_student_event_write_failed source=%s mode=%s error=%s",
                    write_source,
                    mode,
                    telemetry_error,
                )
            continue
        _record_success(write_source=write_source, target=target)

    return TelemetryWriteResult(
        core_written=core_written,
        telemetry_written=telemetry_written,
        core_error=core_error,
        telemetry_error=telemetry_error,
    )


def write_student_outcome_event(
    *,
    event_type: str,
    source: str,
    details: dict | None = None,
    classroom=None,
    student=None,
    module=None,
    material=None,
    classroom_id=None,
    student_id=None,
    module_id=None,
    material_id=None,
    write_source: str = "student_outcome_event",
    raise_on_error: bool = True,
) -> TelemetryWriteResult:
    mode = _write_mode()
    payload_details = details or {}
    core_error = ""
    telemetry_error = ""
    core_written = False
    telemetry_written = False

    core_payload = {
        **_relation_kwargs(relation_name="classroom", relation_obj=classroom, relation_id=classroom_id),
        **_relation_kwargs(relation_name="student", relation_obj=student, relation_id=student_id),
        **_relation_kwargs(relation_name="module", relation_obj=module, relation_id=module_id),
        **_relation_kwargs(relation_name="material", relation_obj=material, relation_id=material_id),
        "event_type": event_type,
        "source": source,
        "details": payload_details,
    }
    telemetry_payload = {
        "classroom_id": _scalar_id(obj=classroom, explicit_id=classroom_id),
        "student_id": _scalar_id(obj=student, explicit_id=student_id),
        "module_id": _scalar_id(obj=module, explicit_id=module_id),
        "material_id": _scalar_id(obj=material, explicit_id=material_id),
        "event_type": event_type,
        "source": source,
        "details": payload_details,
    }

    for target in _targets_for_mode(mode):
        _record_attempt(write_source=write_source, target=target)
        try:
            if target == "core":
                StudentOutcomeEvent.objects.create(**core_payload)
                core_written = True
            else:
                TelemetryStudentOutcomeEvent.objects.create(**telemetry_payload)
                telemetry_written = True
        except Exception as exc:
            _record_failure(write_source=write_source, target=target, exc=exc)
            if target == "core":
                core_error = exc.__class__.__name__
                if raise_on_error:
                    raise
            else:
                telemetry_error = exc.__class__.__name__
                if mode == _WRITE_MODE_TELEMETRY_ONLY and raise_on_error:
                    raise
                logger.warning(
                    "telemetry_student_outcome_write_failed source=%s mode=%s error=%s",
                    write_source,
                    mode,
                    telemetry_error,
                )
            continue
        _record_success(write_source=write_source, target=target)

    return TelemetryWriteResult(
        core_written=core_written,
        telemetry_written=telemetry_written,
        core_error=core_error,
        telemetry_error=telemetry_error,
    )


__all__ = [
    "TelemetryWriteResult",
    "write_student_event",
    "write_student_outcome_event",
]

