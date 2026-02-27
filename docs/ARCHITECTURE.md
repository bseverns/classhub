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
  H --> L[LLM backend<br/>mock, local, or remote]

  M[(MinIO)] -. reserved / optional .- W
```

## Trust boundaries (Map A)

```mermaid
flowchart TB
  subgraph Z0["Internet and Browsers"]
    S["Student browser"]
    T["Teacher browser"]
    A["Admin browser"]
  end

  subgraph Z1["Edge Proxy (Caddy)"]
    C["Caddy: TLS, routing, request limits"]
  end

  subgraph Z2["Application Network"]
    CH["ClassHub (Django)"]
    HH["Homework Helper (Django)"]
    R["Redis cache"]
    PG["Postgres database"]
    FS["File storage (/uploads)"]
  end

  subgraph Z3["Optional External Services"]
    YT["YouTube-nocookie embeds"]
    REM["Remote LLM provider (optional)"]
  end

  S -->|HTTPS| C
  T -->|HTTPS| C
  A -->|HTTPS| C

  C -->|/, /teach, downloads| CH
  C -->|/helper/*| HH

  CH <--> R
  CH <--> PG
  CH <--> FS

  HH <--> R
  HH -->|metadata event POST| CH

  CH -.-> YT
  HH -. optional .-> REM
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
- Runtime behavior is resolved through explicit contracts:
  - scope/context envelope (`engine/context_envelope.py`)
  - policy bundle (`engine/runtime_config.py`)
  - execution config (`engine/execution_config.py`)

## Why two Django services

1. Availability isolation: core classroom flows can remain usable when AI degrades.
2. Security boundaries: helper policy/rate-limit logic is isolated from core LMS pages.
3. Operational flexibility: helper can evolve independently (model/backend changes).

## Deployment model

- Production images bake service code and curriculum content from repo.
- Gunicorn serves Django in containers.
- Local dev uses compose override + bind mounts for fast iteration.

See:

- [DEVELOPMENT.md](DEVELOPMENT.md) for local workflow
- [RUNBOOK.md](RUNBOOK.md) for operations
- `compose/docker-compose.yml` for source-of-truth wiring

## ClassHub module graph (Map C)

```mermaid
%%{init: {"themeVariables": {"fontSize": "11px"}, "flowchart": {"nodeSpacing": 24, "rankSpacing": 22, "defaultRenderer": "elk"}}}%%
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
    direction TB
    V1[hub/views/student_join.py<br/>join + invite bridge + join/index]
    V2[hub/views/student.py<br/>session/home + upload + my-data + exports]
    V3[hub/views/student_materials.py<br/>checklist + reflection + rubric]
    V4[hub/views/content.py<br/>course + lesson render]
    V5[hub/views/teacher.py<br/>portal + roster + materials]
    V6[hub/views/internal.py<br/>token-gated internal events]
    V7[hub/views/media.py<br/>asset/video download + stream]
    VALL{{ClassHub view layer}}
  end

  subgraph D["Data layer"]
    MD[hub/models.py]
    DB[(Postgres)]
    RC[(Redis/cache)]
    FS[(MEDIA storage)]
  end

  subgraph H["Homework Helper service"]
    direction TB
    H1[tutor/views.py<br/>/helper/chat]
    H2[tutor/views_chat_request.py<br/>request shaping]
    H3[tutor/views_chat_deps.py<br/>dependency wiring]
    H4[tutor/views_chat_runtime.py<br/>runtime wrappers]
    H5[tutor/views_chat_helpers.py<br/>helper adapters]
    H6[tutor/engine/service.py<br/>chat orchestration]
    H7[tutor/engine/context_envelope.py<br/>scope contract]
    H8[tutor/engine/runtime_config.py<br/>policy contract]
    H9[tutor/engine/execution_config.py<br/>execution contract]
    H10[tutor/policy.py]
    H11[tutor/classhub_events.py]
    H12[common/request_safety]
    HALL{{Helper endpoint layer}}
  end

  subgraph B["Support layers (below)"]
    direction TB
    BSUP{{Support layer}}

    subgraph S["Services"]
      SALL[hub/services/*<br/>content_links + upload_validation + filenames<br/>ip_privacy + audit + upload_scan + release_state]
    end

    subgraph T["Templates"]
      TP[templates/student_* + teach_* + includes/helper_widget]
      TT[hub/templatetags/hub_extras.py]
    end
  end

  U --> M1 --> M2 --> M3 --> M4 --> VALL

  VALL --> V1
  VALL --> V2
  VALL --> V3
  VALL --> V4
  VALL --> V5
  VALL --> V6
  VALL --> V7

  VALL --> BSUP
  BSUP --> SALL
  BSUP -.-> TP

  VALL ==> MD
  MD ==> DB
  VALL ==> RC
  VALL ==> FS

  TP -.-> TT

  H1 --> HALL
  HALL --> H2
  HALL --> H3
  HALL --> H4
  HALL --> H5
  HALL --> H6
  H6 --> H7
  H6 --> H8
  H6 --> H9
  H6 --> H10
  HALL --> H11
  H2 --> H12
  H11 -. token-gated internal POST .-> V6
  H12 ==> RC
```

How to read connection styles:

| Connection style | Meaning in this map |
| --- | --- |
| `A --> B` | Request/control flow between app layers |
| `A -.-> B` | Render path or token-gated internal event flow |
| `A ==> B` | Data/cache/file access |
