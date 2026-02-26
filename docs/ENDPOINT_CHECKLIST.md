# Endpoint Checklist

Use this checklist whenever adding or changing an HTTP endpoint in ClassHub or Homework Helper.

## Required protections

- Caching policy:
  - Auth/session-bearing responses must set `Cache-Control: no-store` (or `private, no-store`) and `Pragma: no-cache`.
  - Use shared helpers (`apply_no_store` / runtime helpers) instead of ad-hoc header writes.
- CSP expectations:
  - Do not add inline JS or inline CSS in templates.
  - Keep CSP policy behavior aligned with `CSP_MODE` rollout (`relaxed`, `report-only`, `strict`).
- Download hardening:
  - For file downloads/attachments, apply `X-Content-Type-Options: nosniff` and restrictive CSP sandbox headers.
  - Use `safe_attachment_filename(...)` for user/content-derived filenames.
- Rate limiting:
  - Add cache-backed throttling for public or abuse-prone POST endpoints.
  - Return clear 429 responses with `Retry-After` where applicable.
- Event logging minimization:
  - Log request IDs, status, and coarse metadata only.
  - Avoid full payload logging and avoid unnecessary student identifiers/PII.
- Error handling:
  - Return bounded, user-safe error payloads.
  - Keep internal exception details in server logs only.

## CI guardrails tied to this checklist

- `scripts/check_no_inline_template_js.py`
- `scripts/check_no_inline_template_css.py`
- `scripts/check_view_header_helpers.py`
- `scripts/check_view_size_budgets.py`
- `scripts/check_view_function_budgets.py`
- `scripts/check_no_service_imports_from_views.py`
- `scripts/check_no_dynamic_service_all_exports.py`

If you need to bypass one of these guards for a valid reason, document the exception in `docs/DECISIONS.md` in the same PR.
