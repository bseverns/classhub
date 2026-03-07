# ClassHub Repository Evaluation

## 1. "Correct" Decisions Already Made

The ClassHub repository demonstrates a strong, principled approach to building a self-hosted, privacy-forward micro-LMS. Several "correct" decisions are evident in the architecture, security posture, and operational maintainability:

### Architectural Isolation
*   **Service Boundary (`Class Hub` vs. `Homework Helper`):** Separating the core LMS (`Class Hub`) from the AI tutor (`Homework Helper`) into distinct Django services routed by Caddy is highly resilient. It ensures that an AI provider outage or a rate-limit exhaustion in the tutor does not take down core classroom flows (joining classes, uploading materials).
*   **Boring Infrastructure:** Relying on proven, boring infrastructure (Postgres, Redis, Caddy) reduces operational complexity for self-hosters and improves stability.

### Privacy and Security Posture
*   **Data Minimization (Student Auth):** Choosing to authenticate students via class code + display name, rather than collecting emails and passwords in the MVP, significantly reduces the platform's PII surface area and compliance burden.
*   **Explicit Role-Based Access (Staff Auth):** Enforcing explicit Django authentication and OTP-verified 2FA for superusers and teacher workflows (`/admin`, `/teach`) provides a necessary security boundary for administrative and destructive actions.
*   **Append-Only Audit Trails:** Using append-only `AuditEvent` records for staff mutations and `StudentEvent` records for student actions preserves incident traceability without modifying historical records.
*   **Automated Retention Boundaries:** Implementing operator-managed prune commands (`prune_submissions`, `prune_student_events`) with non-zero defaults ensures that data is not stored indefinitely by accident.
*   **Defensive Frontend Delivery:** Implementing strict CSP (`DJANGO_CSP_MODE`), security headers, and attachment-only lesson asset delivery hardens the application against stored XSS and content-sniffing vulnerabilities.

### Reliability and Operations
*   **Offline Upload Queue:** Implementing a browser-local IndexedDB queue for intermittent networks prevents student data loss without requiring complex background telemetry.
*   **Documentation as a First-Class Citizen:** The comprehensive, role-based documentation (`docs/START_HERE.md`, `docs/RUNBOOK.md`, `docs/TROUBLESHOOTING.md`) and the explicit tracking of policies in `docs/DECISIONS.md` prevents tribal knowledge and makes operator handoff survivable.
*   **CI and Linting Guardrails:** The repository heavily utilizes custom CI checks (`scripts/check_view_size_budgets.py`, `scripts/check_test_inventory_coverage.py`) to enforce architectural constraints, prevent view bloat, and ensure test coverage for critical flows.

---

## 2. "Incorrect" Decisions Made Purposely (Technical Debt & Deferred Complexity)

The maintainers have intentionally deferred certain complex or high-risk architectural changes to maintain operational stability and ship velocity, explicitly documenting these tradeoffs in `MAINTENANCE_RISK_REGISTER.md` and `DECISIONS.md`.

### Teacher Portal Complexity Budget
*   **Decision:** The teacher portal (`/teach`) aggregates many staff workflows (roster management, template generation, class configuration) into a few dense view modules (e.g., `teach_home.html`, `roster_class.py`).
*   **Why it's "incorrect":** It violates standard MVC separation of concerns, creating "big file gravity" where small changes risk unrelated regressions, and makes the UI visually overwhelming for new staff.
*   **Why it's purposeful:** The team instituted a 30-day stability freeze on new primitives here to prioritize usability smoothing over a risky, broad refactor.

### Permissive Organizational Boundary Fallback
*   **Decision:** `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` defaults to `False`. Staff without explicit org memberships retain legacy global class access.
*   **Why it's "incorrect":** It creates a risk of access drift where staff can see classes outside their expected organization, potentially violating privacy boundaries as deployments scale.
*   **Why it's purposeful:** It preserves backward compatibility for existing single-tenant deployments, allowing an incremental migration to strict multi-program boundaries rather than a one-shot, breaking data migration.

### Phased Database Workload Split
*   **Decision:** Core transactional data and high-churn telemetry events currently share a single Postgres database, though a phased split is in progress (`TELEMETRY_DB_SPLIT_PLAN.md`). Phase 1 isolates only telemetry, leaving core submissions/metadata together.
*   **Why it's "incorrect":** Spiky event workloads could theoretically impact the performance of core LMS transactional paths.
*   **Why it's purposeful:** A near-zero-downtime, gate-based migration with dual-write toggles is safer than a rushed database split that could corrupt core class data.

### RBAC Phase 2 is Foundational-Only
*   **Decision:** Custom roles and delegated capabilities are persisted (`OrganizationCustomRole`), but the operator-usable workflows and approval UI are hidden behind a feature flag (`CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1`).
*   **Why it's "incorrect":** Complex district-style permissions still rely partially on legacy static role-to-capability mappings or CLI manipulation rather than a complete GUI.
*   **Why it's purposeful:** It supports district-style delegated duties without adding regression risk to the current, stable membership-role behavior during the stability freeze.

---

## 3. Path to Improvement and Expansion

To address the documented maintenance risks and scale the platform, the following path is recommended:

### Phase 1: Harden the Foundation (Addressing the Risk Register)
1.  **Refactor the Teacher Portal (Service-Layer Extraction):** Continue the "Service-layer extraction scaffold" described in `DECISIONS.md`. Systematically migrate business logic (e.g., dashboard assembly, syllabus ingestion) out of dense view files (`hub/views/teacher_parts/`) into isolated, tested service modules (`hub/services/`). Enforce the existing view-size budgets to prevent regression.
2.  **Enforce Strict Organizational Boundaries:** Migrate `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` to `True` for all production deployments. Provide automated tooling or runbooks to map legacy global staff to explicit `OrganizationMembership` records, eliminating the permissive fallback.
3.  **Automate Restore Rehearsals:** As noted in Risk 4, disaster recovery depends heavily on operator rituals. Elevate the `scripts/backup_restore_rehearsal.sh` script into a CI-enforced or scheduled staging deployment to prove recovery viability automatically, rather than relying on manual quarterly drills.

### Phase 2: Complete In-Flight Architectural Migrations
4.  **Execute Phase 2 of the Telemetry DB Split:** With Phase 1 telemetry scaffolding shipped, proceed to isolate the core submission and class metadata workloads. This will fully decouple the append-only event streams from the LMS transactional state, improving performance and restore posture.
5.  **Complete RBAC Phase 2 (Custom Role Workflows):** Stabilize and enable the delegated approval workflow (`RbacPolicyChangeRequest`) and custom role management UI in the teacher portal. This will allow district operators to manage complex capability matrices without relying on CLI tools or manual policy-as-code imports.

### Phase 3: Product Expansion (Post-Freeze)
6.  **Expand 'Homework Helper' RAG Capabilities:** The current local RAG implementation is curriculum-only. Explore safely expanding the RAG context to include explicitly shared, class-scoped artifacts (e.g., teacher-approved gallery items) to provide more contextual peer-to-peer inspiration, while maintaining the strict anti-surveillance privacy posture.
7.  **Decentralized Coursepack Registry:** Advance the `docs/COURSEPACK_REGISTRY_RFC.md` to allow schools to share and import curriculum bundles directly via the LMS, moving beyond the current ZIP-upload ingest path to a more robust, network-aware content distribution model.