---
course: piper-scratch-12
session: 8
slug: s08-game-controls-boundaries
title: "Level 2: New Mechanic, New Mood"
duration_minutes: 75
makes: A controllable character that stays on screen.
needs:
  - Piper computer kit (or any computer)
  - Scratch (web or app)
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V12
    title: Collisions + win/lose broadcast (intro)
    minutes: 4
    outcome: Detect contact and respond.
  - id: V06
    title: "Save privately: Download to your computer"
    minutes: 3
    outcome: Save an `.sb3` locally every time.
submission:
  type: file
  accepted:
    - .sb3
  naming: S08_game_controls_v1.sb3
done_looks_like:
  - Arrow keys (or WASD) move the character.
  - Character can’t leave the stage (or wraps intentionally).
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Add a sprint key (shift) that increases speed.
  - Add a ‘slow mode’ for accessibility.
teacher_panel:
  purpose: Establish player control and readable game space.
  snags:
    - Movement too fast/slow.
    - Boundary logic confusing—use simple edge checks.
  assessment:
    - Student maps input to motion reliably.
helper_allowed_topics:
  - "start a new scratch project ."
  - "add controls: arrow keys move sprite."
  - "add boundaries ."
  - "add one collectible or one obstacle."
  - "download .sb3"
  - "upload .sb3"
  - "reboot once if frozen."
  - "check downloads"
---
**Mission:** Build Level 2 with one new mechanic that changes the game.

## Teacher prep (before class)
- Have 2–3 “mechanic recipes” ready on the board (patrol enemy, key/door, moving platform).

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
- Show examples of a “new mechanic”:
  - moving platforms
  - key + locked door
  - faster hazards
  - enemy that chases when close
- Teach: keep Level 2 *different*, not just harder.

**0:12–0:42 Build sprints**
**Sprint A:** Choose a new mechanic and prototype it in Level2.  
**Reset:** Save + teacher checks that the mechanic works once.  
**Sprint B:** Integrate the mechanic into the goal (door, score, survive).  
**Reset:** Stand + save.  
**Sprint C:** Add balancing (make it fair) and communicate with text/hints.

**0:42–0:52 Playtest rotation**
- Prompt: “What’s new in Level 2? How did you learn it?”
- Testers note if the rule was unclear.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- Level 2 exists and is reachable.
- A new mechanic is present and functional.

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add an optional secret room.
- Add a second cutscene (very short) triggered by a mid-level event.
- Add a countdown timer for Level 2.

