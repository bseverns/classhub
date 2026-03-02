# LMS Stewardship Charter (createMPLS)

**Purpose:** Keep ClassHub (the LMS) safe, usable, and sustainable—so programs can run calmly even when staff change.

This charter defines *who decides*, *who operates*, *how changes happen*, and *how we protect learners and staff*.

---

## 1) Scope

This charter covers:

- Production hosting of the LMS (ClassHub) and any related services (database, media storage, reverse proxy, helper).
- Course content operations (coursepacks, lesson updates, enrollment flows).
- Privacy, retention, and consent posture.
- Incident response (outages, broken flows, suspected data exposure).
- Change management (patching, upgrades, new features).

Out of scope (but adjacent):

- Classroom pedagogy and facilitation methods (owned by program teams).
- Hardware lab maintenance (devices, printers, robotics kits)—except where it impacts LMS use.

---

## 2) Principles (non-negotiables)

1) **Programs first.** If the LMS wobbles, class still runs (offline plan always ready).
2) **No surprises.** Students and staff should never feel tricked by settings, sharing, or data collection.
3) **Minimum necessary data.** We store only what we need to run the learning environment.
4) **Opt-in spotlight.** Public sharing is optional; private participation is always valid.
5) **Recoverability over cleverness.** A simple system we can restore beats a complex one we can’t.
6) **Two-person rule for critical moves.** No solo changes that can take the system down or expose data.

---

## 3) Roles (“hats”)

A three-person team can cover this by wearing hats. Hats can rotate; responsibilities remain stable.

### 3.1 Product & Program Steward (PPS)
Owns *why* the LMS exists and whether it serves the program.

Responsibilities:
- Defines what success looks like for learners and facilitators.
- Approves feature requests using plain language criteria.
- Owns content standards: accessibility, tone, multilingual/multimodal needs.
- Owns the “offline plan” structure for classes (printables, fallback procedures).
- Maintains a short backlog: “what we should improve next.”

Authority:
- Can approve/decline product changes.
- Can toggle non-critical features (e.g., gallery visibility) per policy.

### 3.2 Operations Steward (OPS)
Owns *whether the LMS is ready for class today*.

Responsibilities:
- Runs the “Day-of-Class” checklist before sessions.
- Triage support issues from staff and students.
- Maintains a small incident log (what happened, impact, resolution).
- Ensures weekly checks happen (backups, basic health signals).
- Coordinates the change window calendar (when updates happen).

Authority:
- Can initiate incident protocol.
- Can execute pre-approved operational scripts (restart services, switch feature flags) **only if documented**.

### 3.3 Safety & Privacy Steward (SPS)
Owns *trust* and the rules of care.

Responsibilities:
- Owns retention presets and deletion policy.
- Approves any change that affects: data collection, logging, sharing defaults, helper/AI configuration.
- Reviews consent language, “what we store,” and staff-facing privacy guidance.
- Runs quarterly “privacy rehearsal” (what’s stored, what’s purged, what can be exported).

Authority:
- Veto power on changes that increase risk without clear benefit.
- Can mandate toggling off high-risk features until reviewed.

### 3.4 Technical Maintainer (TM)
Owns *implementation* and *system integrity*. This may be staff, contractor, volunteer, or partner org.

Responsibilities:
- Maintains infrastructure and deploy pipeline.
- Applies security patches and dependency updates.
- Ensures monitoring/logging is sufficient but not invasive.
- Maintains disaster recovery readiness (restore drills).
- Maintains documentation in `ops/` and runbooks.

Authority:
- Executes changes in change windows.
- Can perform emergency changes during incidents (SEV1) with post-incident writeup.

---

## 4) Decision rights (RACI)

| Topic | PPS | OPS | SPS | TM |
|---|---:|---:|---:|---:|
| Course content changes | A | C | C | C |
| Feature enable/disable (non-risk) | A | R | C | C |
| Privacy/retention defaults | C | C | A | R |
| Deployments / infra changes | C | C | C | A/R |
| Security patching | C | C | C | A/R |
| Incident response | C | A/R | C | R |
| Data export / deletion policy changes | C | C | A | R |
| Adding new external services | C | C | A | R |

Legend: **A** = accountable, **R** = responsible, **C** = consulted.

---

## 5) Change management

### 5.1 Change windows
- **Default:** One weekly change window (e.g., Fridays after programs).
- **Rule:** No routine changes during program hours.
- **Emergency:** SEV1 fixes can happen anytime, with postmortem within 48 hours.

### 5.2 Two-person rule (critical changes)
The following require **TM + one Steward witness** (OPS or SPS), even if the witness only follows the checklist:

- Production deploys
- DNS / TLS / domain registrar changes
- Database migrations on production
- Secret rotations / credential changes
- Backup/restore operations
- Retention policy changes
- Enabling remote helper/AI backends or new external services

### 5.3 Change record (lightweight)
Every change that touches production gets an entry in `ops/DECISIONS.md`:

- Date + who
- What changed (1–3 bullets)
- Why (1–2 sentences)
- Risk level (low/med/high)
- Rollback plan (one sentence)
- Verification checklist used

---

## 6) Access & credentials

### 6.1 Password manager
All shared credentials must live in a password manager (1Password/Bitwarden/etc.).

Store references for:
- VPS account + console access
- SSH keys/backup codes (where appropriate)
- Domain registrar + DNS
- Email provider used for notifications
- GitHub org/repo access
- Object storage/MinIO credentials (if used)
- Any monitoring accounts

### 6.2 Least privilege
- Each person has their own account where possible (no shared logins).
- Access is granted per hat:
  - OPS does not need root server access if checklists suffice.
  - SPS needs policy + visibility, not shell access.
  - TM needs technical access; avoid granting admin rights elsewhere.

### 6.3 Offboarding / emergency transfer
- Maintain an “Emergency Access” note: where backups are, how to access server, how to contact TM/contractor.
- Quarterly: verify that at least two people can access the password manager and domain registrar.

---

## 7) Documentation requirements (the “continuity binder”)

The `ops/` folder is the continuity binder. It must contain:

- `SYSTEM_OVERVIEW.md` (architecture, where things run, dependencies)
- `DEPLOYMENT.md` (how to deploy + rollback)
- `DISASTER_RECOVERY.md` (how to restore DB/media)
- `ACCESS.md` (what accounts exist + where credentials live)
- `VENDOR_AND_COSTS.md` (who we pay, how much, renewals)
- `SOP_CHECKLISTS.md` (day/week/month/quarterly routines)
- `INCIDENT_LOG.md` (brief entries; no sensitive learner details)

Minimum bar: A competent contractor should be able to take over using only these docs.

---

## 8) Meeting cadence (small and steady)

### Weekly (15–30 minutes): “LMS Stewardship Standup”
Attendees: PPS, OPS, SPS, TM (as available)

Agenda:
1) What did students struggle with?
2) What did facilitators struggle with?
3) What broke / nearly broke?
4) Review upcoming changes (patches, content releases)
5) Choose the *one* most valuable improvement for the next week

### Quarterly (45–60 minutes): “Trust & Recovery Review”
1) Restore drill in staging
2) Permissions + credential audit
3) Retention + privacy review
4) Accessibility/language review
5) Budget check (contractor safety net, hosting costs)

---

## 9) Exit / succession plan (when TM changes)

When the Technical Maintainer role changes hands:

1) **Handoff meeting** (60–90 min) with PPS/OPS/SPS.
2) **Access transfer** completed (password manager, repo, server, DNS).
3) **Restore drill** performed by new maintainer in staging.
4) **First patch cycle** completed with supervision.
5) **Document gaps** logged and scheduled for closure.

---

## 10) Appendices

### A) Severity definitions
- **SEV1:** Site down during programs; join/login broken; data loss suspected; security incident suspected.
- **SEV2:** Major feature broken (uploads failing, teacher dashboard unusable); widespread impact.
- **SEV3:** Minor bug; cosmetic issues; small number of users affected.

### B) Offline continuity pledge (for programs)
Every session must have a fallback plan that does not require the LMS:
- printed step cards or whiteboard steps
- device-local work
- a simple end-of-class “capture” routine (photo + note) to upload later

**The LMS is a studio tool, not the studio itself.**