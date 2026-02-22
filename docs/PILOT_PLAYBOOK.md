# Pilot Playbook (18-student run)

## Summary
This page is the “how we ran it” guide for a small pilot (≈18 students) of ClassHub.

It exists to:
- keep the operator calm
- keep the teacher unblocked
- keep student data minimal and deletable
- generate a shareable story others can replicate

If you are deploying for the first time, do [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) first.
If you are teaching tomorrow, do [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md) + [TEACHER_PORTAL.md](TEACHER_PORTAL.md).

## What to do now
1. Copy the “Pilot config profile” section into `compose/.env` as deltas (do not overwrite secrets).
2. Run a full dry run with `bash scripts/system_doctor.sh --smoke-mode strict`.
3. Teach one “empty-room rehearsal” class: join → lesson → helper → upload → `/student/my-data` delete/end-session.
4. Decide the retention window for this pilot and enable the retention timer after you are comfortable.

## Verification signal
On class day, you can answer “are we healthy?” in under 60 seconds:
- `/healthz` returns 200
- `/helper/healthz` returns 200
- smoke check passes: join + helper chat + teacher portal

---

## Pilot framing: what this run is (and isn’t)

### Goals
- Run a classroom loop with low friction:
  - join by class code
  - lesson delivery
  - submissions
  - optional helper hints
- Practice “kid gloves + armor”:
  - explicit data controls (`/student/my-data`)
  - no ad-tech posture
  - safe downloads
  - minimal event payloads
- Build a replicable playbook for other teachers/operators.

### Non-goals (for this pilot)
- No remote LLM backend.
- No large-scale roster/account systems for students.
- No complex analytics beyond operational safety logs.
- No “perfect” retention automation on day 1 (we phase it in).

---

## Pilot config profile (recommended defaults)

These are deltas for `compose/.env`. Keep your secrets and host values intact.

```dotenv
# Keep the site usable under classroom conditions.
CLASSHUB_SITE_MODE=normal

# Student privacy posture (pilot-safe defaults).
CLASSHUB_PORTFOLIO_FILENAME_MODE=generic
CLASSHUB_STUDENT_EVENT_IP_MODE=truncate
CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=180
CLASSHUB_SUBMISSION_RETENTION_DAYS=90

# Keep uploads within expected classroom reality.
CLASSHUB_UPLOAD_MAX_MB=200
CADDY_CLASSHUB_MAX_BODY=220MB

# Helper stays local for this pilot.
HELPER_LLM_BACKEND=ollama
HELPER_REMOTE_MODE_ACKNOWLEDGED=0
HELPER_STRICTNESS=light
HELPER_SCOPE_MODE=strict
HELPER_TOPIC_FILTER_MODE=strict
HELPER_MAX_CONCURRENCY=2

# Join rate limit (protect against accidental hammering / refresh storms).
CLASSHUB_JOIN_RATE_LIMIT_PER_MINUTE=20

# Retention maintenance script defaults (safe starting point).
RETENTION_SUBMISSION_DAYS=90
RETENTION_EVENT_DAYS=180
RETENTION_SCAVENGE_MODE=report