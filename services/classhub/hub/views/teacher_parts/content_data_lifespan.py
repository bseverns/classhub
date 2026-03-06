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


def _build_snapshot_context() -> dict:
    snapshot = build_data_lifespan_snapshot()
    return {
        "snapshot": snapshot,
        "rag_status": _load_rag_status(),
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


def _build_csv_export_body(*, snapshot: dict, rag_status: dict) -> str:
    out = StringIO()
    out.write(build_data_lifespan_snapshot_csv(snapshot).rstrip("\n"))
    out.write("\n\n")
    writer = csv.writer(out)
    writer.writerow(["rag_status"])
    writer.writerow(["field", "value"])
    writer.writerow(["status", str(rag_status.get("status") or "")])
    writer.writerow(["rag_enabled", bool(rag_status.get("rag_enabled"))])
    writer.writerow(["index_ready", bool(rag_status.get("index_ready"))])
    writer.writerow(
        ["indexed_chunk_count", int(rag_status.get("indexed_chunk_count") or 0)]
    )
    writer.writerow(
        ["reference_source_count", int(rag_status.get("reference_source_count") or 0)]
    )
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
            {"snapshot": snapshot_payload, "rag_status": context["rag_status"]}
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
        _audit_snapshot_export(request, export_format=export_format, filename=filename)
        return response
    if export_format == "csv":
        filename = _snapshot_export_filename("csv")
        response = HttpResponse(
            _build_csv_export_body(snapshot=context["snapshot"], rag_status=context["rag_status"]),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
        _audit_snapshot_export(request, export_format=export_format, filename=filename)
        return response
    return HttpResponse("Invalid export format.", status=400)


__all__ = ["teach_data_lifespan", "teach_data_lifespan_export"]
