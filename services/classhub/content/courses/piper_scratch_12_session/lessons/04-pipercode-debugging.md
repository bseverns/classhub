---
course: piper-scratch-12
session: 4
slug: s04-pipercode-debugging
title: "Obstacles + Lives: The Art of Try Again"
duration_minutes: 75
makes: A tiny block program + a first bug report practice.
needs:
  - Piper computer kit (or any computer)
  - Piper desktop
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V03
    title: PiperCode (open + run + save)
    minutes: 4
    outcome: Create a project, run it, and save it.
  - id: V14
    title: Bug report workflow (how to ask for help)
    minutes: 3
    outcome: Describe a problem in a way that gets fast help.
submission:
  type: file
  accepted:
    - .png
    - .jpg
  naming: S04_pipercode_blocks.png
done_looks_like:
  - You built a small block stack.
  - You wrote one bug report (real or pretend).
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Break one thing on purpose and fix it.
  - Swap the order of two blocks and observe the change.
teacher_panel:
  purpose: Teach that debugging is normal and describable.
  snags:
    - Students don’t know what changed.
    - Screenshots missing blocks—teach zoom/fit.
  assessment:
    - Student can run/stop a block program.
    - Student can write clear reproduction steps.
helper_allowed_topics:
  - "open pipercode."
  - "create a new project."
  - "add 2-5 blocks"
  - "save your project."
  - "screenshot your blocks."
  - "fill out one bug report ."
  - "upload .png"
  - "reboot once if frozen."
---
**Mission:** Add hazards, lives, and a reset that returns the player to a start point.

## Teacher prep (before class)
- Have a reset pattern ready: `broadcast reset` and `go to x/y`.
- Consider marking “start spot” on stage with a visible object.

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
- Create variable `lives`.
- Build live: hazard reduces lives and broadcasts `reset`; player goes to start.
- Teach: `broadcast`, `if touching`, `set lives`, `change lives by`.

**0:12–0:42 Build sprints**
**Sprint A:** Add one hazard + lives system.  
**Reset:** Save + teacher checks “lives decreases once per hit.”  
**Sprint B:** Add a safe “start spot” and reset behavior.  
**Reset:** Stand + save.  
**Sprint C:** Add a simple game over screen when lives = 0.

**0:42–0:52 Playtest rotation**
- Prompt: “Is it fair? Does it feel like you get a second chance?”
- Testers note: too hard / too easy / confusing.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- `lives` variable decreases on hazard.
- `reset` returns player to a start point reliably.

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add invincibility blink for 1 second after hit.
- Add moving hazard (patrol left/right).
- Add health hearts UI (icons).

