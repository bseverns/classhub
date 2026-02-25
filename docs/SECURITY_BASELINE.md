# Security Baseline

This is the single source of truth for edge-vs-app security ownership.

## Edge-Owned (Caddy)
- Request body size limits:
  - `CADDY_CLASSHUB_MAX_BODY` (default `220MB`)
  - `CADDY_HELPER_MAX_BODY` (default `1MB`)
- Route armor for `/admin*` and `/teach*`:
  - IP allowlists: `CADDY_STAFF_IP_ALLOWLIST_V4`, `CADDY_STAFF_IP_ALLOWLIST_V6`
  - Optional basic auth gate for `/admin*`: `CADDY_ADMIN_BASIC_AUTH_*`
  - Explicit acknowledgement toggle for open staff routes: `CADDY_ALLOW_PUBLIC_STAFF_ROUTES=1`
- TLS redirect/termination (domain templates) and HSTS:
  - `Strict-Transport-Security: max-age=${CADDY_HSTS_MAX_AGE}` (default `31536000`)
- Compression (`encode gzip`)

## App-Owned (Django)
- CSP:
  - Mode selector: `DJANGO_CSP_MODE` (`relaxed`, `report-only`, `strict`)
  - Enforced override: `DJANGO_CSP_POLICY`
  - Report-only override: `DJANGO_CSP_REPORT_ONLY_POLICY`
  - Default mode is `relaxed` (enforced relaxed + strict report-only)
  - Transitional strict-script canary is allowed via `DJANGO_CSP_MODE=strict` + explicit `DJANGO_CSP_POLICY` that keeps `script-src 'self'` while temporarily allowing `style-src 'unsafe-inline'`
- Framing policy:
  - Primary: CSP `frame-ancestors 'self'`
  - Fallback: `X-Frame-Options: SAMEORIGIN` (`DJANGO_X_FRAME_OPTIONS`)
- `Permissions-Policy` from `DJANGO_PERMISSIONS_POLICY`
- `Referrer-Policy` from `DJANGO_SECURE_REFERRER_POLICY`
- Cache policy:
  - Sensitive responses: `Cache-Control: private, no-store` (+ `Pragma: no-cache` where set)
  - Join JSON carrying return codes: `Cache-Control: no-store` (+ `Pragma: no-cache`)
  - Inline authenticated lesson assets: `Cache-Control: private, max-age=60`
- Sensitive download hardening:
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy: default-src 'none'; sandbox`
  - `Referrer-Policy: no-referrer`
- Site mode responses (`read-only`, `join-only`, `maintenance`) return `Cache-Control: no-store`

## Header Inventory (Drift Table)

| Header | Set by (current) | Current value(s) | Intended owner | Final intended value |
|---|---|---|---|---|
| `Content-Security-Policy` | Django middleware + some download views | Default policy includes `frame-ancestors 'self'`; download views use `default-src 'none'; sandbox` | Django | Keep middleware policy; keep stricter per-download override |
| `Content-Security-Policy-Report-Only` | Django middleware | Mirrors configured report-only policy | Django | Keep report-only during rollout, then tune/remove as needed |
| `X-Frame-Options` | Django middleware | `SAMEORIGIN` default (`DJANGO_X_FRAME_OPTIONS`) | Django | `SAMEORIGIN` fallback, compatible with CSP `frame-ancestors 'self'` |
| `Permissions-Policy` | Django middleware | Value from `DJANGO_PERMISSIONS_POLICY` | Django | Keep app-owned |
| `Referrer-Policy` | Django middleware + some download views | Global `strict-origin-when-cross-origin`; downloads `no-referrer` | Django | Keep app-owned with per-download strict override |
| `X-Content-Type-Options` | Django (`SECURE_CONTENT_TYPE_NOSNIFF`) + download views | Global `nosniff` in prod; explicit on sensitive downloads | Django | Keep app-owned; explicit per-download remains |
| `Cache-Control` | View-level + site-mode middleware | Sensitive pages/downloads `private, no-store`; join JSON `no-store`; inline lesson assets `private, max-age=60` | Django/views | Keep category-based values as implemented |
| `Pragma` | Sensitive view responses | `no-cache` on no-store JSON/download responses | Django/views | Keep as compatibility fallback |
| `Strict-Transport-Security` | Caddy domain templates | `max-age=${CADDY_HSTS_MAX_AGE}` | Caddy | Keep edge-owned |

## Conflict Resolution Notes
- Framing conflict resolved: no contradictory `DENY` fallback against CSP `'self'`.
- Caddy no longer sets app-layer policy headers (`CSP`, `Permissions-Policy`, `Referrer-Policy`, `X-Frame-Options`), preventing split ownership drift.
