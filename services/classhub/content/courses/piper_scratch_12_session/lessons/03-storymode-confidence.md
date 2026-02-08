---
course: piper-scratch-12
session: 3
slug: s03-storymode-confidence
title: "Game Rules: Score + Collectibles"
duration_minutes: 75
makes: One completed guided step in StoryMode and a short reflection.
needs:
  - Piper computer kit (or any computer)
  - Piper desktop
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V02
    title: Piper StoryMode (what it is + when we use it)
    minutes: 4
    outcome: Launch StoryMode and complete one step.
submission:
  type: text
  accepted:

  naming: Reflection
done_looks_like:
  - You launched StoryMode.
  - You completed one step.
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Do one additional step only if you feel good.
  - Write one question you’d like to explore later.
teacher_panel:
  purpose: "A low-stakes on-ramp: success first, complexity later."
  snags:
    - Students get pulled into long sequences—cap time.
    - Audio distraction—offer no-sound path.
  assessment:
    - Student can launch/exit StoryMode.
    - Student reflection shows attention to process.
helper_allowed_topics:
  - "open piper ."
  - "complete one guided step."
  - "exit back to desktop."
  - "write 3 sentences: what you did"
  - "reboot once if frozen."
  - "check downloads"
  - "use the help form to upload"
---
**Mission:** Create a collectible and a score counter that behaves.

## Teacher prep (before class)
- Print **Handout 03** (Score + Collision Recipes).
- Make sure students can find Variables category quickly.

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
- Make a variable `score` and show it on screen.
- Build live: collectible moves to random spot when touched; score increases by 1.
- Teach: variables, `if touching`, `go to random position`, `change score by`.

**0:12–0:42 Build sprints**
**Sprint A:** Add a collectible and make score increase once per touch.  
**Reset:** Save + teacher checks “score doesn’t climb forever.”  
**Sprint B:** Add 2nd collectible type worth 5 points (optional).  
**Reset:** Stand + save.  
**Sprint C:** Add a goal: “Collect 10 to win Level 1” (we’ll finalize next week).

**0:42–0:52 Playtest rotation**
- Prompt: “Does the score match what you did?”
- Testers try to break it: touch repeatedly, hold sprite on coin.

**0:52–1:00 Share + Save**
- 2–3 shares.
- Everyone writes: “Next time I will…”

## Checkpoints (what you must see working)
- `score` variable exists and changes correctly.
- Collectible moves/hides after being collected.

## Common stuck points + fixes
- If it doesn’t start: add a hat block (green flag / key press).
- If it loops forever: add a condition or a reset.

## Extensions (fast finisher menu)
- Add a sparkle animation when collecting.
- Add a sound effect.
- Add a timer bonus (score +1 each second remaining).

