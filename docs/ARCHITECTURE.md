# Architecture

This system is a small self-hosted LMS stack with a split web surface:

- `Class Hub` (main LMS)
- `Homework Helper` (AI tutor under `/helper/*`)

## Runtime topology (current)

```mermaid
flowchart TD
  U[Students / Teachers / Admins] -->|HTTP/HTTPS| C[Caddy]
  C -->|/helper/*| H[Homework Helper Django]
  C -->|everything else| W[Class Hub Django]

  W --> P[(Postgres)]
  H --> P
  W --> R[(Redis db0)]
  H --> R[(Redis db1)]

  W --> F[(Local upload volume<br/>/uploads)]
  H --> O[Ollama]
  H -. optional .-> A[OpenAI Responses API]

  M[(MinIO)] -. reserved / optional .- W
```

## Trust boundaries (Map A)

```mermaid
flowchart TB
  subgraph Z0["Internet / Browsers"]
    S[Student Browser]
    T[Teacher Browser]
    A[Admin / Operator Browser]
  end

  subgraph Z1["Edge / Reverse Proxy (Caddy)"]
    C[Caddy<br/>TLS • routing • body limits<br/>security headers (optional)]
  end

  subgraph Z2["Application Network (Docker / host LAN)"]
    CH[ClassHub (Django)<br/>classhub_web<br/>student + teacher UI]
    HH[Homework Helper (Django)<br/>helper_web<br/>hint engine + policies]
    R[(Redis / cache)<br/>rate limits • sessions • throttles]
    PG[(Postgres)<br/>core data store]
    FS[(File storage / MEDIA)<br/>submissions • exports]
  end

  subgraph Z3["Optional External Services"]
    YT[YouTube-nocookie embeds]
    REM[Remote LLM provider<br/>(only if enabled)]
  end

  S -->|HTTPS| C
  T -->|HTTPS| C
  A -->|HTTPS| C

  C -->|/ + /teach + media/download routes| CH
  C -->|/helper/*| HH

  CH <-->|cache calls| R
  CH <-->|SQL| PG
  CH <-->|read/write| FS

  HH <-->|cache calls| R
  HH -->|best-effort internal event POST (token-gated)| CH

  CH -.->|embeds| YT
  HH -. optional .->|prompt/response| REM
```

## What routes where

- Caddy handles edge traffic.
- `/helper/*` goes to Homework Helper.
- All other paths go to Class Hub.

This means helper outages are less likely to take down core LMS pages.

```mermaid
flowchart LR
  S[Student session<br/>class code + display name] --> W[Class Hub]
  T[Teacher/Admin Django auth + OTP] --> W
  W -->|signed scope token| H[Homework Helper]
  H -->|metadata-only event| W
```

## Data boundaries

### Class Hub

- Owns classroom, student, module/material, submission, and teacher portal flows.
- Uses Postgres + Redis.
- Stores uploads on local mounted storage (`/uploads`), not public media routes.

### Homework Helper

- Owns helper chat policy, prompt shaping, and model backends.
- Uses Postgres + Redis for auth/session/rate-limit integration.
- Uses Ollama by default; OpenAI is optional by environment config.

## Why two Django services

1. Availability isolation: core classroom flows can remain usable when AI degrades.
2. Security boundaries: helper policy/rate-limit logic is isolated from core LMS pages.
3. Operational flexibility: helper can evolve independently (model/backend changes).

## Deployment model

- Production images bake service code and curriculum content from repo.
- Gunicorn serves Django in containers.
- Local dev uses compose override + bind mounts for fast iteration.

See:

- `docs/DEVELOPMENT.md` for local workflow
- `docs/RUNBOOK.md` for operations
- `compose/docker-compose.yml` for source-of-truth wiring

## ClassHub module graph (Map C)

```mermaid
flowchart TB
  subgraph URL["URLs / Routing"]
    U[config/urls.py<br/>route table]
  end

  subgraph MW["Middleware layer"]
    M1[SecurityHeadersMiddleware]
    M2[SiteModeMiddleware]
    M3[TeacherOTPRequiredMiddleware]
    M4[StudentSessionMiddleware]
  end

  subgraph V["Views"]
    V1[hub/views/student.py<br/>join • lesson • upload • my-data • exports]
    V2[hub/views/teacher.py<br/>teacher portal • roster • materials]
    V3[hub/views/content.py<br/>content rendering helpers]
    V4[hub/views/internal.py<br/>token-gated internal events]
    V5[hub/views/media.py<br/>asset/video download + stream]
  end

  subgraph S["Services"]
    S1[hub/services/content_links.py]
    S2[hub/services/upload_validation.py]
    S3[hub/services/filenames.py]
    S4[hub/services/ip_privacy.py]
    S5[hub/services/audit.py]
    S6[hub/services/upload_scan.py]
    S7[hub/services/release_state.py]
  end

  subgraph T["Templates"]
    TT[hub/templatetags/hub_extras.py]
    TP[templates/student_* + teach_* + includes/helper_widget]
  end

  subgraph D["Data layer"]
    MD[hub/models.py]
    DB[(Postgres)]
    RC[(Redis/cache)]
    FS[(MEDIA storage)]
  end

  subgraph H["Homework Helper service"]
    H1[tutor/views.py<br/>/helper/chat]
    H2[tutor/policy.py]
    H3[tutor/classhub_events.py]
    H4[common/request_safety]
  end

  U --> M1 --> M2 --> M3 --> M4 --> V1
  M4 --> V2
  M4 --> V3
  M4 --> V4
  M4 --> V5

  V1 --> S1
  V1 --> S2
  V1 --> S3
  V1 --> S4
  V1 --> S5
  V1 --> S6

  V2 --> S1
  V2 --> S3
  V2 --> S5
  V2 --> S7

  V4 --> S4

  V1 --> MD
  V2 --> MD
  V3 --> MD
  V4 --> MD
  V5 --> MD
  MD --> DB

  V1 --> RC
  V2 --> RC
  V1 --> FS
  V2 --> FS
  V5 --> FS

  V1 --> TP
  V2 --> TP
  TP --> TT

  H1 --> H2
  H1 --> H4
  H1 --> H3
  H3 -->|token-gated internal POST| V4
  H4 --> RC
```
