# Press Architecture Snapshot

## Summary
This diagram shows the public-facing deployment shape in one page.

## What to do now
1. Use this diagram when explaining stack boundaries.
2. Pair with `docs/ARCHITECTURE.md` for implementation details.
3. Pair with `docs/SECURITY_BASELINE.md` for header/control ownership.

## Verification signal
A reader should be able to identify edge, app services, and stateful dependencies from this page alone.

```mermaid
flowchart LR
  U[Browser] --> C[Caddy Edge]
  C --> CH[Class Hub Django<br/>student, teacher, org, reporting]
  C --> HH[Homework Helper Django]
  CH --> O[Org + class access policy]
  CH --> RPT[Outcomes + certificate exports]
  CH --> PG[(Postgres)]
  CH --> R[(Redis)]
  HH --> PG
  HH --> R
  HH --> LLM[Mock, local LLM, or remote model]
```
