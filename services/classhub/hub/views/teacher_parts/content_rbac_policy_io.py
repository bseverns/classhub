"""Policy-as-code import/export endpoints for RBAC tools."""

from __future__ import annotations

import json

from ...services.rbac_policy_bundle import (
    POLICY_SCHEMA_VERSION,
    RbacPolicyImportResult,
    apply_rbac_policy_payload,
    build_rbac_policy_export_payload,
)
from .shared import (
    HttpResponse,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    apply_download_safety,
    apply_no_store,
    require_POST,
    safe_attachment_filename,
    staff_can_export_syllabi,
    staff_member_required,
    timezone,
)

_MAX_POLICY_BYTES = 2 * 1024 * 1024


def _rbac_redirect(request, *, notice: str = "", error: str = ""):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra={"rbac_tools": "1"}),
        fallback="/teach",
    )


def _require_rbac_tools_access(request):
    if staff_can_export_syllabi(request.user):
        return None
    return _rbac_redirect(request, error="RBAC tools require owner/admin role.")


def _load_policy_json(request):
    upload = request.FILES.get("rbac_policy_file")
    if upload is None:
        raw_text = (request.POST.get("rbac_policy_json") or "").strip()
        if not raw_text:
            return None, "", "Upload a policy JSON file."
        raw_bytes = raw_text.encode("utf-8")
        if len(raw_bytes) > _MAX_POLICY_BYTES:
            return None, "", "Policy JSON exceeds 2MB limit."
        try:
            return json.loads(raw_text), "inline", ""
        except json.JSONDecodeError as exc:
            return None, "", f"Invalid JSON: {exc.msg}."
    if upload.size and int(upload.size) > _MAX_POLICY_BYTES:
        return None, "", "Policy JSON exceeds 2MB limit."
    raw = upload.read()
    if not raw:
        return None, "", "Policy file is empty."
    if len(raw) > _MAX_POLICY_BYTES:
        return None, "", "Policy JSON exceeds 2MB limit."
    try:
        return json.loads(raw.decode("utf-8")), (upload.name or "upload"), ""
    except UnicodeDecodeError:
        return None, "", "Policy file must be UTF-8 encoded JSON."
    except json.JSONDecodeError as exc:
        return None, "", f"Invalid JSON: {exc.msg}."


@staff_member_required
def teach_export_rbac_policy(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    exported_at = timezone.now().isoformat()
    result = build_rbac_policy_export_payload(request.user, exported_at=exported_at)
    _audit(
        request,
        action="rbac.policy.export",
        summary="Exported RBAC policy-as-code bundle",
        metadata={
            "schema_version": POLICY_SCHEMA_VERSION,
            "organization_count": result.organization_count,
            "scoped_grant_count": result.scoped_grant_count,
        },
    )
    body = json.dumps(result.payload, indent=2, sort_keys=True) + "\n"
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    filename = safe_attachment_filename(
        f"classhub-rbac-policy-{timezone.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_no_store(response, private=True, pragma=True)
    apply_download_safety(response)
    return response


def _import_notice(result: RbacPolicyImportResult) -> str:
    return (
        "Imported RBAC policy "
        f"(org new:{result.org_created} updated:{result.org_updated}; "
        f"grants new:{result.grant_created} updated:{result.grant_updated})."
    )


@staff_member_required
@require_POST
def teach_import_rbac_policy(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    payload, source_label, parse_error = _load_policy_json(request)
    if parse_error:
        return _rbac_redirect(request, error=parse_error)
    try:
        result = apply_rbac_policy_payload(
            actor_user=request.user,
            payload=payload,
            source_label=source_label,
        )
    except ValueError as exc:
        return _rbac_redirect(request, error=str(exc))
    _audit(
        request,
        action="rbac.policy.import",
        summary="Imported RBAC policy-as-code bundle",
        metadata={
            "schema_version": POLICY_SCHEMA_VERSION,
            "source": result.source_label,
            "organization_role_capability_rows": result.org_rows,
            "scoped_grant_rows": result.grant_rows,
            "organization_created": result.org_created,
            "organization_updated": result.org_updated,
            "scope_grant_created": result.grant_created,
            "scope_grant_updated": result.grant_updated,
        },
    )
    return _rbac_redirect(request, notice=_import_notice(result))


__all__ = [
    "teach_export_rbac_policy",
    "teach_import_rbac_policy",
]
