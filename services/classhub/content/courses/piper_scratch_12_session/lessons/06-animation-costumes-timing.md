---
course: piper-scratch-12
session: 6
slug: s06-animation-costumes-timing
title: "Scene Switching: Backdrops as Rooms (Menu → Level 1)"
duration_minutes: 75
makes: A short looping animation using costume changes.
needs:
  - Piper computer kit (or any computer)
  - Scratch (web or app)
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V10
    title: Costumes + timing (animation loop)
    minutes: 4
    outcome: Animate with 2+ costumes and a wait.
  - id: V06
    title: "Save privately: Download to your computer"
    minutes: 3
    outcome: Save an `.sb3` locally every time.
submission:
  type: file
  accepted:
    - .sb3
  naming: S06_animation_v1.sb3
done_looks_like:
  - Sprite changes costumes in a loop.
  - Timing feels intentional.
  - Project downloaded and submitted.
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Animate a second sprite with a different tempo.
  - Add a backdrop change every 8 costume switches.
teacher_panel:
  purpose: Teach time as a design material (pacing).
  snags:
    - Animation too fast/slow.
    - Students stuck in costume editor—timebox.
  assessment:
    - Student can use costumes and waits to create motion.
helper_allowed_topics:
  - "open your session 5 project or"
  - "create or import 2 costumes for"
  - "code: forever → next costume →"
  - "adjust wait to feel right."
  - "download .sb3"
  - "upload file"
  - "upload .sb3"
  - "reboot once if frozen."
---
**Mission:** Build clean transitions using backdrops and broadcasts.

## Teacher prep (before class)
- Consider creating a “Backdrops checklist” on the board:
  Menu, Level1, Cutscene1, Level2, Win, GameOver.

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
- Teach the doorway pattern:
  - touching door → `broadcast [level complete] and wait`
  - switch backdrop to Level1 / Cutscene / Level2
- Teach: `switch backdrop`, `when backdrop switches to`.

**0:12–0:42 Build sprints**
**Sprint A:** Create backdrops: Menu + Level1.  
**Reset:** Save + teacher checks “start button works.”  
**Sprint B:** Add a start button that broadcasts `start game` and switches to Level1.  
**Reset:** Stand + save.  
**Sprint C:** Make sure the right sprites show/hide on each backdrop.

**0:42–0:52 Playtest rotation**
- Prompt: “Can you start the game without help?”
- Testers write down the controls they discovered.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- Menu exists and leads to Level1.
- Sprites appear in the correct scene (no random leftovers).

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add an instructions screen from the menu.
- Add a settings toggle (sound on/off).
- Add a title animation on the menu.
