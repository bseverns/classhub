# Decisions (living)

## 2026-01-16 — Student access is class-code + display name

**Why:**
- Minimum friction for classrooms.
- Minimal PII collection.
- Fewer account recovery issues at MVP stage.

**Tradeoffs:**
- If a student clears cookies, they “lose” identity unless we add a return-code.

**Plan:**
- MVP uses session cookie only.
- Add optional “return code” later.

## 2026-01-16 — Homework Helper is a separate service

**Why:**
- Reliability: helper failures do not block class materials.
- Safety: independent rate limits and logs.
- Clarity: prompt policy lives in one place.
