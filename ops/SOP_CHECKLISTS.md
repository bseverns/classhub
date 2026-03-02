# ops/SOP_CHECKLISTS.md

# SOP Checklists (ClassHub LMS)

These checklists are designed so non-technical staff can keep the LMS stable and classes calm.

**Golden rule:** If the website fails, class still runs. Use the offline plan without apology.

---

## 0) Quick roles reminder

- **OPS (Operations Steward):** runs day/week checklists, triages issues, coordinates incidents.
- **SPS (Safety & Privacy Steward):** approves retention/sharing/logging/helper settings; runs trust checks.
- **TM (Technical Maintainer):** deploys, patches, restores, owns infra integrity.
- **PPS (Product & Program Steward):** content quality and program alignment.

---

## 1) Day-of-Class Checklist (5 minutes)

Owner: **OPS**  
Timing: **30–60 minutes before session**

### 1.1 “Can learners get in?”
- [ ] Open the site on a phone **not on office Wi-Fi** (public network if possible).
- [ ] Load the join page.
- [ ] Join a test class with a test code.
- [ ] Confirm join guidance appears (pseudonym-first + “no real name needed,” if enabled).

### 1.2 “Can staff run class?”
- [ ] Teacher login works (OTP/2FA if required).
- [ ] The day’s lesson opens.
- [ ] A small upload test works (image < 1MB).
- [ ] If handouts exist: open the lesson PDF handout (or print link).

### 1.3 “Is plan B ready?”
- [ ] Printed handouts OR a whiteboard-ready step list exists for today.
- [ ] Staff know the offline capture routine: photo + one sentence to upload later.

If anything fails:
- Start **Incident SOP** (Section 6) at the appropriate severity.
- Use offline plan immediately if class is soon.

---

## 2) Weekly Checklist (15–30 minutes)

Owner: **OPS + TM**  
Timing: Same day/time weekly

### 2.1 OPS: Support + stability
- [ ] Review support issues from the week; tag top 5 patterns.
- [ ] Confirm next week’s change window time.
- [ ] Confirm teachers have needed class codes and lessons published.

### 2.2 TM: Health + backups
- [ ] Run smoke check (join/login/lesson page).
- [ ] Check service status (compose ps or equivalent).
- [ ] Verify backups ran (timestamp is recent).
- [ ] Spot-check backup size changed since last week.
- [ ] Check disk usage (DB + media + logs).
- [ ] Review error log summary (last 7 days).

Output:
- A short note added to `ops/INCIDENT_LOG.md` if anything notable happened.
- Any recurring issue becomes a backlog item for PPS.

---

## 3) Monthly Checklist (45–90 minutes)

Owner: **TM + SPS**  
Timing: First week of each month (outside program hours)

### 3.1 Patch cycle (staging first)
- [ ] Update OS packages on staging host (if applicable).
- [ ] Update Python dependencies (as per repo policy), run tests.
- [ ] Run migrations on staging.
- [ ] Run smoke tests on staging (join, submit, teacher dashboard).
- [ ] Review changelog of major deps (Django, auth, storage).

### 3.2 Privacy & data posture
- [ ] SPS reviews any changes impacting:
  - logging
  - retention
  - sharing/gallery defaults
  - helper/AI configuration
- [ ] Confirm retention job ran (if enabled) and deletions match policy.

### 3.3 Production deploy (change window)
- [ ] Two-person rule present (TM + witness).
- [ ] Create a quick rollback point (tag/compose image version).
- [ ] Deploy.
- [ ] Verify key flows.
- [ ] Record change in `ops/DECISIONS.md`.

---

## 4) Quarterly Checklist (60–120 minutes)

Owner: **Circle (PPS + OPS + SPS + TM)**

### 4.1 Restore drill (mandatory)
Goal: Prove we can recover without heroics.

- [ ] Restore database backup into staging.
- [ ] Restore media bucket/files into staging.
- [ ] Log in as teacher; open a lesson; verify a submission loads.
- [ ] Time the drill; note blockers.
- [ ] Record in `ops/DECISIONS.md` or `ops/INCIDENT_LOG.md`.

### 4.2 Permissions and access audit
- [ ] Who has server access? Confirm list is current.
- [ ] Who has domain registrar access?
- [ ] Who has password manager emergency access?
- [ ] Remove access for any departed staff/volunteers.
- [ ] Verify MFA enabled where possible.

### 4.3 Trust review (SPS-led)
- [ ] Re-read “What we store / never store” page for clarity.
- [ ] Confirm retention settings still match program reality.
- [ ] Confirm gallery/publishing defaults remain opt-in.
- [ ] Confirm helper/AI settings match policy (local-only by default if that’s policy).

### 4.4 Program alignment (PPS-led)
- [ ] Which pages confuse students?
- [ ] Which steps stall facilitators?
- [ ] What’s one change that would reduce friction next quarter?

---

## 5) Content Operations SOP (Coursepacks)

Owner: **PPS + OPS** (TM assists when needed)

### 5.1 Publishing new lessons
- [ ] Lesson has:
  - clear goal
  - 3–6 steps
  - “what to submit” checklist
  - offline alternative (if devices/network fail)
- [ ] Language support: plain English; translations if available.
- [ ] Avoid assumptions: no “everyone has a laptop,” no “ask your parents.”

### 5.2 Updating content mid-program
- [ ] If change affects active classes, announce it to facilitators.
- [ ] Keep old versions accessible when possible (avoid breaking links).
- [ ] When in doubt: add, don’t replace.

---

## 6) Incident SOP (non-technical friendly)

Owner: **OPS leads**, TM executes fixes, SPS consulted for privacy/security, PPS informed for program impact.

### 6.1 Severity classification
- **SEV1:** site down, join/login broken during programs, data loss suspected, security incident suspected.
- **SEV2:** major feature broken (uploads failing widely, teacher dashboard broken).
- **SEV3:** minor/cosmetic issues.

### 6.2 Immediate steps (OPS)
1) **Protect the class**
   - If class is within 30 minutes: switch to offline plan now.
2) **Capture the symptom**
   - Screenshot error, note time, note what device/network.
3) **Notify**
   - Message TM with severity + screenshot.
   - If privacy/security: notify SPS immediately.

### 6.3 SEV1 protocol
- OPS:
  - [ ] Start offline plan.
  - [ ] Announce internally “SEV1 in progress” with timestamp.
- TM:
  - [ ] Check service status; restart if safe.
  - [ ] Check reverse proxy / TLS / DNS status.
  - [ ] Check DB connectivity.
  - [ ] Roll back last deploy if likely cause.
- SPS:
  - [ ] If data exposure suspected: instruct “stop using system” until cleared.
  - [ ] Begin minimal incident notes (no learner PII).

### 6.4 SEV2 protocol
- Use offline plan if needed, but class may continue with workaround.
- TM investigates in change window if not urgent.
- Record in incident log; prioritize fix within 7 days.

### 6.5 Post-incident (within 48 hours)
Owner: OPS writes; TM/SPS contribute

- [ ] What happened?
- [ ] Who was impacted?
- [ ] Root cause (best guess).
- [ ] Fix applied.
- [ ] Prevention action (1–3 items).
- [ ] Update runbook/checklists if needed.

---

## 7) Backup & Restore SOP (TM)

### 7.1 Backup requirements
- Database backups: daily minimum (more frequent if feasible).
- Media backups: daily or continuous snapshot depending on storage.
- Retain at least:
  - 7 daily
  - 4 weekly
  - 6 monthly (adjust based on cost and policy)

### 7.2 Restore steps (high level)
- [ ] Provision staging environment.
- [ ] Restore DB backup.
- [ ] Restore media.
- [ ] Verify app boots.
- [ ] Verify join + teacher login.
- [ ] Verify at least one submission artifact.

Document exact commands in `ops/DISASTER_RECOVERY.md`.

---

## 8) Security patching SOP (TM + SPS)

### 8.1 Defaults
- Patch monthly; emergency patch if critical CVE relevant to stack.
- Staging first.
- Record changes.

### 8.2 Review checklist
- [ ] Any changes to auth/session/cookies?
- [ ] Any changes to storage permissions?
- [ ] Any changes to helper/AI networking?
- [ ] Any new outbound connections?
If yes → SPS must approve before production.

---

## 9) Onboarding / Offboarding SOP

### 9.1 New steward onboarding (OPS/SPS/PPS)
- [ ] Read `ops/SYSTEM_OVERVIEW.md` (30 min).
- [ ] Run Day-of-Class checklist with a mentor once.
- [ ] Know where offline plan lives.
- [ ] Know where to log incidents and decisions.

### 9.2 Maintainer onboarding (TM)
- [ ] Full access granted via password manager.
- [ ] Deploy to staging successfully.
- [ ] Restore drill in staging successfully.
- [ ] First production deploy witnessed.

### 9.3 Offboarding
- [ ] Remove access from password manager, server, DNS, GitHub.
- [ ] Rotate secrets if departing person had privileged access.
- [ ] Record in `ops/DECISIONS.md`.

---

## 10) “Class still runs” offline capture routine

If the LMS is down:
1) Students still build.
2) At the end:
   - take a photo/video of the artifact
   - write one sentence: “Today I tried…”
3) Facilitator collects these on a shared device/folder and uploads later.

**We never punish a student for an infrastructure failure.**