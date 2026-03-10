# Identity SSO Expansion Plan (Teacher + Optional Student School Login)

## Summary

This plan outlines how to add:

- teacher/staff SSO (Google Workspace, Microsoft Entra ID, other OIDC providers), and
- optional student school-account login

while keeping pseudonymous student identity as the default public posture.

Current live posture remains unchanged:

- students: class code + display name (+ return code/device-hint rejoin),
- teachers/admins: Django auth + OTP.

## Goals

- Reduce teacher login/admin overhead with managed identity providers.
- Keep student experience privacy-forward and low-friction by default.
- Add school-account login for students only as an opt-in path.
- Preserve class-bound pseudonymous presentation in teacher and student surfaces.

## Non-goals

- No mandatory student email identity for all deployments.
- No exposure of legal names/emails on public or class-facing pages by default.
- No removal of class-code join flow.

## Constraints

- Keep existing org boundary controls (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`).
- Keep 2FA posture for non-SSO fallbacks and privileged staff paths.
- Keep auditable, reversible rollout gates.

## Recommended Architecture

Use OIDC as the primary protocol seam.

Provider examples:

- Google Workspace (OIDC)
- Microsoft Entra ID (OIDC)
- Generic OIDC (district/partner IdPs)

Data model seam:

- `ExternalIdentityLink` (staff + optional student use)
  - `provider_key` (google, microsoft, oidc_custom)
  - `issuer`
  - `subject`
  - `user_id` (Django user for staff accounts)
  - optional `student_identity_id` (for student school-login link path)
  - `email` (nullable/minimized)
  - `email_verified`
  - `last_login_at`
  - uniqueness on `(issuer, subject)`

Implementation note:

- Store only required claims.
- Avoid storing profile payloads that are not used operationally.

## Teacher SSO Rollout (Phase T)

### T0: Provider abstraction and config

- Add provider config model/settings:
  - enabled providers
  - client id/secret
  - issuer/discovery URL
  - allowed hosted domains / tenant IDs
  - org auto-mapping rules
- Add env guards for missing/invalid provider config.

T0 implementation scaffold (now shipped):

- Django settings parse/normalize:
  - `CLASSHUB_TEACHER_SSO_ENABLED`
  - `CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK`
  - `CLASSHUB_TEACHER_SSO_PROVIDERS`
  - provider-specific keys for `google`, `microsoft`, and `oidc_custom`
- Environment guardrails enforce:
  - provider list is present when SSO is enabled,
  - enabled provider keys are recognized,
  - required client id/secret (and custom issuer/discovery) are present.
- Example env templates include all SSO keys:
  - `compose/.env.example`
  - `compose/.env.example.local`
  - `compose/.env.example.domain`

### T1: Login UX and callback flow

- Extend `/teach/login` with explicit SSO entry buttons (feature-flagged).
- Add OIDC start/callback endpoints for each enabled provider.
- Keep existing username/password route as fallback unless explicitly disabled.

### T2: Provisioning and mapping policy

- Default: invite-first or pre-provisioned staff only (safer).
- Optional controlled JIT for specific org domains/tenants.
- Resolve or create `ExternalIdentityLink` on callback success.
- Enforce org membership checks post-auth before `/teach` access.

### T3: Security controls

- Validate `state` and `nonce` for all OIDC flows.
- Enforce strict redirect URI allowlist.
- Enforce domain/tenant allowlist for accepted identities.
- Log auth events (success/failure/provider/domain mismatch).

### T4: Operational readiness

- Add smoke checks for each enabled staff provider.
- Add runbook playbook:
  - provider outage fallback to password auth
  - emergency disable flag per provider
  - account-link repair flow

### T5: Acceptance criteria

- Staff can sign in via configured provider and land on `/teach`.
- Org boundary still blocks out-of-scope staff.
- Provider outage has a documented fallback path.

## Student School-Account Login (Optional Phase S)

The default remains class code + pseudonym.

Student SSO is additive and opt-in per org/class deployment.

### S0: Product and policy guardrails

- Feature flags:
  - org-level: enable student school login
  - class-level override: enabled/disabled
- Keep class-code join available unless explicitly disabled by policy.

### S1: First-time linking flow (safe binding)

Recommended first-time path:

1. Student authenticates with school account (OIDC).
2. Student still enters class code or valid invite token.
3. System creates/fetches class-bound `StudentIdentity`.
4. Student chooses or accepts pseudonym display name.
5. System creates `ExternalIdentityLink` to that class-bound identity.

Security reason:

- Prevents someone with a school account from auto-binding into wrong classes.

### S2: Returning flow

- Student signs in with school account.
- Resolve `ExternalIdentityLink` to class-bound `StudentIdentity`.
- Reuse existing student session model and permissions.

### S3: Pseudonym-preserving default posture

- Continue showing `StudentIdentity.display_name` in teacher rosters and student-facing pages.
- Do not display school email by default in teacher dashboards.
- Keep legal-name/email exposure off unless explicitly enabled for staff-only views.
- Keep export defaults pseudonymous unless an org policy requires identity fields.

### S4: Data minimization choices

Minimum stored identity attributes:

- provider issuer + subject (required)
- verification state and last login timestamp
- optional email only when required for support/compliance

Avoid by default:

- profile photos
- broad profile claims
- unnecessary directory attributes

### S5: Abuse and edge-case handling

- Shared device logout hardening remains required.
- Prevent automatic cross-class linking unless policy says otherwise.
- Provide unlink/relink staff flow for transferred students.
- Keep return-code/device-hint rejoin path available as fallback where needed.

### S6: Acceptance criteria

- Student can join and return with school auth when enabled.
- Public/classroom-facing identity remains pseudonymous by default.
- Staff can support account-link issues with documented admin tools.

## Trade-offs

Teacher SSO benefits:

- Lower password-reset overhead
- Better lifecycle control via district identity systems
- Cleaner offboarding when district accounts deactivate

Teacher SSO costs:

- Provider setup complexity and outage coupling
- More callback/auth diagnostics to operate
- Additional domain/tenant policy surface to audit

Student school-login benefits:

- Stronger continuity across devices
- Potentially fewer mistaken identity merges than display-name-only joins
- Better fit for districts that require managed student auth

Student school-login costs:

- Higher privacy/compliance surface (student account metadata)
- Support load for identity linking/unlinking issues
- Equity risk where school accounts are unavailable or inconsistently provisioned

## Recommended Sequence

1. Implement teacher SSO first (Google + Microsoft via OIDC seam).
2. Run one release cycle with fallback and outage drills.
3. Pilot optional student school-login in one org with explicit consent/policy.
4. Keep pseudonym-first display semantics as a hard default.

## Runbook Additions Required Before Production Enablement

- Provider incident fallback checklist.
- Identity-link repair procedure.
- Org policy checklist for student school-login enablement.
- Audit queries for linked/unlinked identity coverage by class/org.

## Test Plan Outline

Teacher SSO:

- success callback for each provider
- domain/tenant rejection
- disabled provider rejection
- org boundary enforcement after auth
- fallback password login still works (if enabled)

Student optional school-login:

- first-time link requires class code/invite
- returning school-login resolves correct class-bound student identity
- pseudonym remains display default in roster/export UI
- unlink/relink flow does not expose disallowed identity fields

## Decision Gate Template

Before enabling in production:

- Security review completed (redirect/state/nonce/domain policy).
- Privacy review completed (data minimization + pseudonym defaults verified).
- Operator runbook updates complete.
- Smoke + rollback drills complete.
- Dated decision row added to [DECISIONS.md](DECISIONS.md).
