"""Read-only operator dashboard for retention/lifecycle visibility."""

import csv
from io import StringIO

from django.conf import settings
from django.http import JsonResponse

from ...services.data_lifespan import (
    build_data_lifespan_snapshot,
    build_data_lifespan_snapshot_csv,
    build_data_lifespan_snapshot_export,
)
from ...services.helper_control import fetch_rag_status
from ...services.remote_compute_operator_snapshot import build_remote_compute_operator_snapshot
from .shared import (
    HttpResponse,
    _audit,
    apply_download_safety,
    apply_no_store,
    render,
    safe_attachment_filename,
    staff_can_export_syllabi,
    staff_member_required,
    timezone,
)


def _load_rag_status() -> dict:
    result = fetch_rag_status(
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_RAG_STATUS_URL", "") or "").strip(),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(
            getattr(settings, "HELPER_INTERNAL_RAG_STATUS_TIMEOUT_SECONDS", 1.2) or 1.2
        ),
    )
    if result.ok:
        return {
            "status": "ok",
            "rag_enabled": bool(result.rag_enabled),
            "index_ready": bool(result.index_ready),
            "indexed_chunk_count": int(result.indexed_chunk_count),
            "reference_source_count": int(result.reference_source_count),
            "last_index_built_at": str(result.last_index_built_at or ""),
            "reference_sources": list(result.reference_sources or []),
            "configured_reference_keys": list(result.configured_reference_keys or []),
            "student_data_excluded_from_index": bool(result.student_data_excluded_from_index),
        }
    if result.error_code in {"helper_endpoint_not_configured", "helper_token_not_configured"}:
        return {"status": "not_configured", "error_code": str(result.error_code)}
    return {"status": "error", "error_code": str(result.error_code or "helper_status_failed")}


def _load_remote_compute_operator_snapshot() -> dict:
    return build_remote_compute_operator_snapshot(
        endpoint_url=(
            str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_OPERATOR_SNAPSHOT_URL", "") or "").strip()
        ),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
    )


def _build_snapshot_context() -> dict:
    snapshot = build_data_lifespan_snapshot()
    return {
        "snapshot": snapshot,
        "rag_status": _load_rag_status(),
        "remote_compute_operator_snapshot": _load_remote_compute_operator_snapshot(),
    }


def _snapshot_export_filename(extension: str) -> str:
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    return safe_attachment_filename(f"classhub_data_lifespan_snapshot_{stamp}.{extension}")


def _audit_snapshot_export(request, *, export_format: str, filename: str) -> None:
    _audit(
        request,
        action="data_lifespan.snapshot_export",
        target_type="DataLifespanSnapshot",
        target_id=export_format,
        summary=f"Exported data lifespan snapshot ({export_format})",
        metadata={"format": export_format, "filename": filename},
    )


def _write_rag_status_csv(writer, *, rag_status: dict) -> None:
    writer.writerow(["rag_status"])
    writer.writerow(["field", "value"])
    writer.writerow(["status", str(rag_status.get("status") or "")])
    writer.writerow(["rag_enabled", bool(rag_status.get("rag_enabled"))])
    writer.writerow(["index_ready", bool(rag_status.get("index_ready"))])
    writer.writerow(["indexed_chunk_count", int(rag_status.get("indexed_chunk_count") or 0)])
    writer.writerow(["reference_source_count", int(rag_status.get("reference_source_count") or 0)])
    writer.writerow(["last_index_built_at", str(rag_status.get("last_index_built_at") or "")])
    writer.writerow(
        [
            "student_data_excluded_from_index",
            bool(rag_status.get("student_data_excluded_from_index", True)),
        ]
    )
    writer.writerow(["error_code", str(rag_status.get("error_code") or "")])
    writer.writerow([])
    writer.writerow(["rag_reference_sources"])
    writer.writerow(["reference_key", "chunk_count", "last_indexed_at"])
    for row in rag_status.get("reference_sources") or []:
        writer.writerow(
            [
                str(row.get("reference_key") or ""),
                int(row.get("chunk_count") or 0),
                str(row.get("last_indexed_at") or ""),
            ]
        )


def _write_remote_compute_operator_csv(writer, *, remote_compute_operator_snapshot: dict) -> None:
    summary = remote_compute_operator_snapshot.get("summary") or {}
    active_lease = remote_compute_operator_snapshot.get("active_lease") or {}
    aggregate_signal = remote_compute_operator_snapshot.get("aggregate_signal") or {}
    writer.writerow(["remote_compute_operator_snapshot"])
    writer.writerow(["field", "value"])
    writer.writerow(["status", str(remote_compute_operator_snapshot.get("status") or "")])
    writer.writerow(["error_code", str(remote_compute_operator_snapshot.get("error_code") or "")])
    writer.writerow(["class_count_with_activity", int(summary.get("class_count_with_activity") or 0)])
    writer.writerow(["activation_count", int(summary.get("activation_count") or 0)])
    writer.writerow(["avg_ready_seconds", int(summary.get("avg_ready_seconds") or 0)])
    writer.writerow(["remote_route_count", int(summary.get("remote_route_count") or 0)])
    writer.writerow(["fallback_local_count", int(summary.get("fallback_local_count") or 0)])
    writer.writerow(["leased_minutes_total", int(summary.get("leased_minutes_total") or 0)])
    writer.writerow(["approximate_cost_usd_total", str(summary.get("approximate_cost_usd_total") or "")])
    writer.writerow(["aggregate_signal_summary", str(aggregate_signal.get("summary") or "")])
    writer.writerow(["aggregate_signal_detail", str(aggregate_signal.get("detail") or "")])
    writer.writerow(["active_lease_class_id", int(active_lease.get("class_id") or 0)])
    writer.writerow(["active_lease_class_name", str(active_lease.get("class_name") or "")])
    writer.writerow(["active_lease_state", str(active_lease.get("state") or "")])
    writer.writerow([])
    writer.writerow(["remote_compute_recent_classes"])
    writer.writerow(
        [
            "class_id",
            "class_name",
            "activation_count",
            "avg_ready_seconds",
            "remote_route_count",
            "fallback_local_count",
            "signal_summary",
        ]
    )
    for row in remote_compute_operator_snapshot.get("recent_classes") or []:
        writer.writerow(
            [
                int(row.get("class_id") or 0),
                str(row.get("class_name") or ""),
                int(row.get("activation_count") or 0),
                int(row.get("avg_ready_seconds") or 0),
                int(row.get("remote_route_count") or 0),
                int(row.get("fallback_local_count") or 0),
                str((row.get("signal") or {}).get("summary") or ""),
            ]
        )


def _build_csv_export_body(*, snapshot: dict, rag_status: dict, remote_compute_operator_snapshot: dict) -> str:
    out = StringIO()
    out.write(build_data_lifespan_snapshot_csv(snapshot).rstrip("\n"))
    out.write("\n\n")
    writer = csv.writer(out)
    _write_rag_status_csv(writer, rag_status=rag_status)
    out.write("\n\n")
    _write_remote_compute_operator_csv(writer, remote_compute_operator_snapshot=remote_compute_operator_snapshot)
    return out.getvalue()


@staff_member_required
def teach_data_lifespan(request):
    can_export_syllabus = bool(staff_can_export_syllabi(request.user))
    if not (request.user.is_superuser or can_export_syllabus):
        return HttpResponse("Forbidden", status=403)

    context = _build_snapshot_context()
    response = render(
        request,
        "teach_data_lifespan.html",
        context,
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_data_lifespan_export(request):
    can_export_syllabus = bool(staff_can_export_syllabi(request.user))
    if not (request.user.is_superuser or can_export_syllabus):
        return HttpResponse("Forbidden", status=403)
    export_format = (request.GET.get("format") or "json").strip().lower()
    context = _build_snapshot_context()
    snapshot_payload = build_data_lifespan_snapshot_export(context["snapshot"])
    if export_format == "json":
        filename = _snapshot_export_filename("json")
        response = JsonResponse(
            {
                "snapshot": snapshot_payload,
                "rag_status": context["rag_status"],
                "remote_compute_operator_snapshot": context["remote_compute_operator_snapshot"],
            }
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
        _audit_snapshot_export(request, export_format=export_format, filename=filename)
        return response
    if export_format == "csv":
        filename = _snapshot_export_filename("csv")
        response = HttpResponse(
            _build_csv_export_body(
                snapshot=context["snapshot"],
                rag_status=context["rag_status"],
                remote_compute_operator_snapshot=context["remote_compute_operator_snapshot"],
            ),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
        _audit_snapshot_export(request, export_format=export_format, filename=filename)
        return response
    return HttpResponse("Invalid export format.", status=400)


__all__ = ["teach_data_lifespan", "teach_data_lifespan_export"]
