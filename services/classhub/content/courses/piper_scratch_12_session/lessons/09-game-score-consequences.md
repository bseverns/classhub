---
course: piper-scratch-12
session: 9
slug: s09-game-score-consequences
title: "Enemy AI: Patrols and Chasers (Simple + Reliable)"
duration_minutes: 75
makes: Score increases and a lose condition ends the round.
needs:
  - Piper computer kit (or any computer)
  - Scratch (web or app)
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V11
    title: Variables + score (game heartbeat)
    minutes: 4
    outcome: Create and update a score variable.
  - id: V12
    title: Collisions + win/lose broadcast
    minutes: 5
    outcome: End the round cleanly via broadcast.
submission:
  type: file
  accepted:
    - .sb3
  naming: S09_score_v1.sb3
done_looks_like:
  - Score updates at least once.
  - A hazard ends the round OR a win triggers at target score.
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Add a timer variable.
  - Add a win condition at score 10.
teacher_panel:
  purpose: Teach state, feedback, and clean endings.
  snags:
    - Score updates too often (multiple hits) — add cooldown.
    - Broadcast handlers missing.
  assessment:
    - Student demonstrates at least one state variable and one outcome.
helper_allowed_topics:
  - "open your session 8 project."
  - "create variable score"
  - "increase score when collecting something."
  - "add a hazard that broadcasts game_over"
  - "show a message on game_over ."
  - "download .sb3"
  - "upload .sb3"
  - "reboot once if frozen."
---
**Mission:** Add enemies with predictable behavior and fair collisions.

## Teacher prep (before class)
- Remind students to separate scripts by purpose: movement vs collision.

## Materials
- Devices with Scratch
- Timer visible
- Handouts (if used)

## Agenda (60 minutes)
**0:00–0:05 Launch**
- “Hands off keys.”
- Say today’s mission.
- Quick preview: what should be working by minute 40.

**0:05–0:12 Micro-lesson (demo)**
- Build a patrol enemy:
  - move steps
  - if touching edge → turn around
- Optionally: chase when close using `distance to` and `point towards`.

**0:12–0:42 Build sprints**
**Sprint A:** Add one enemy and test collisions.  
**Reset:** Save + teacher checks “one hit = one life.”  
**Sprint B:** Add a second enemy or a stronger enemy in Level2.  
**Reset:** Stand + save.  
**Sprint C:** Add fairness: warning movement, slower speed, or safe zones.

**0:42–0:52 Playtest rotation**
- Prompt: “Is it fair? Can you learn the enemy pattern?”
- Testers suggest one fairness change.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- Enemy moves predictably.
- Collision with enemy triggers damage/reset correctly.

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add a boss phase (enemy with 3 hits).
- Add enemy animations (costumes).
- Add enemy sound cues.

