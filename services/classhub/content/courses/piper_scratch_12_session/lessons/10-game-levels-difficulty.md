---
course: piper-scratch-12
session: 10
slug: s10-game-levels-difficulty
title: "Polish Pass: Instructions, Win/Lose Screens, Game Feel"
duration_minutes: 75
makes: Difficulty ramps over time or across levels.
needs:
  - Piper computer kit (or any computer)
  - Scratch (web or app)
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V11
    title: Variables + score (reuse)
    minutes: 3
    outcome: Use variables to control difficulty.
  - id: V13
    title: Start screen + instructions (preview)
    minutes: 4
    outcome: Gate gameplay behind a start.
submission:
  type: file
  accepted:
    - .sb3
  naming: S10_levels_v1.sb3
done_looks_like:
  - Difficulty changes (speed, spawn, timer, etc.).
  - Player understands the goal from on-screen instructions.
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Add an ‘easy mode’ toggle.
  - Add a ‘practice mode’ with no hazards.
teacher_panel:
  purpose: "Introduce pacing and tuning: games are systems that evolve."
  snags:
    - Difficulty jumps too sharply—smooth with smaller increments.
    - Instructions too long—keep short.
  assessment:
    - Student uses variables to alter behavior over time.
helper_allowed_topics:
  - "open session 9 project."
  - "add level variable ."
  - "increase difficulty when score reaches a"
  - "make something change: speed, spawn rate,"
  - "add a simple instruction text ."
  - "download .sb3"
  - "upload .sb3"
  - "reboot once if frozen."
---
**Mission:** Make the game readable and satisfying: instructions, feedback, endings.

## Teacher prep (before class)
- Consider an “arcade rotation” setup: chairs rotate every 2 minutes during playtest.

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
- Show examples of polish:
  - instruction text on menu
  - sound for collect/hit
  - win screen + game over screen
  - screen shake illusion (small quick moves)
- Teach: UI sprites can live on top of the game.

**0:12–0:42 Build sprints**
**Sprint A:** Add instructions (menu or first 5 seconds of Level1).  
**Reset:** Save + teacher checks instructions are visible.  
**Sprint B:** Add win screen and game over screen.  
**Reset:** Stand + save.  
**Sprint C:** Add at least 2 sound or animation feedback moments.

**0:42–0:52 Playtest rotation**
- Prompt: “Can you understand the game without the creator explaining it?”
- Testers try silently; if confused, they note where.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- Instructions exist.
- Win and/or GameOver screen exists and triggers correctly.

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add sound toggle in menu.
- Add a score summary on win screen.
- Add a “play again” button.
