# Legal and Partner Notes

## Summary
Use this page when a school, district, funder, or partner wants a cautious explanation of what ClassHub does, what it does not do, and where operational or legal review is still needed.

## What to do now
1. Use the boundary notes below for partner conversations.
2. Pair this page with [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) and [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md) if detailed questions come up.
3. Bring your own counsel or partner compliance lead in when notice, retention, or contract terms matter.

## Verification signal
After reading this page, a leadership or partner audience should be able to state the system's privacy posture, role boundaries, and what still requires local policy review.

## Important note

This page is not legal advice. It is a practical explanation of the shipped system and the questions partners should resolve with their own legal, compliance, or policy teams.

## What this system is

- A self-hosted classroom platform with a separate helper service under `/helper/*`.
- A system designed for low-friction student access: `class code + display name` in the current student flow.
- A teacher/admin workflow built around staff accounts, class assignments, and auditability.

## What this system is not

- It is not an ad-tech platform.
- It is not a student behavior surveillance system.
- It is not a general-purpose AI assistant platform for unrestricted use.
- It is not a promise that every partner requirement is already satisfied without local review.

## Privacy posture in plain language

- Student access does not require student email/password accounts in the current flow.
- The product is designed to minimize routine collection of student identity data.
- Teacher/admin mutations are auditable.
- Helper prompts are not treated as a routine reporting archive.
- Student work artifacts and class materials follow different visibility rules.

Supporting docs:
- [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md)
- [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md)
- [SECURITY.md](SECURITY.md)

## Role boundaries

- Students use class access and lesson/submission flows.
- Teachers use `/teach` for daily class operations.
- Admins/superusers handle higher-risk setup and policy surfaces.
- Operators/self-hosters own deployment, backups, secrets, and incident response.

This matters for partner review because the system is intentionally not "set and forget" SaaS. The host organization keeps meaningful operational responsibility.

## What partners should expect

- Clear statements about what is live, optional, or still deferred.
- A self-hosted deployment posture with local responsibility for backups, secrets, and configuration.
- Documentation that distinguishes shared curriculum management from class-local teacher changes.
- A bounded helper scope tied to lesson/class context rather than open-ended assistant use.

## Questions to resolve locally

Resolve these with your own leadership, partner, or counsel:
- whether students should use pseudonyms or real names in your program context,
- what retention windows are appropriate for your environment,
- what incident notice process applies if a privacy/security event occurs,
- whether partner contracts require additional data processing terms, accessibility review, or hosting controls,
- whether public lesson visibility fits your curriculum and licensing posture.

## Good partner-facing claims

- The system is designed to minimize student identity collection in routine use.
- The organization hosting the system keeps operational control over infrastructure and data.
- Teacher and admin actions are auditable.
- The helper is bounded to classroom/course context.

## Claims to avoid

- "This automatically makes us compliant."
- "No legal review is needed."
- "The helper is a general-purpose school AI platform."
- "Every deployment has the same policy posture regardless of local configuration."

## Related docs

- Public overview: [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md)
- Risk and data posture: [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md)
- Privacy addendum: [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md)
- Security posture: [SECURITY.md](SECURITY.md)
- Tool boundary and ownership: [TOOL_CHARTER.md](TOOL_CHARTER.md)
