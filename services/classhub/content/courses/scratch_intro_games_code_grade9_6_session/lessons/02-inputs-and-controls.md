---
course: scratch_intro_games_code_grade9_6_session
session: 2
slug: s02-inputs-and-controls
title: "Inputs and Controls: Make It Feel Better"
duration_minutes: 60
makes: "A remix with intentional key mapping and tuned movement behavior."
needs:
  - Scratch (web)
  - Starter project with keyboard controls
  - Projector
privacy:
  - "Use display names only."
  - "Artifact can be link or screenshot + reflection."
submission:
  type: file
  accepted:
    - .txt
    - .md
    - .png
    - .jpg
    - .pdf
    - .sb3
  naming: "G9_S02_controls_reflection.txt"
done_looks_like:
  - "Movement keys changed intentionally."
  - "Speed or boundary behavior adjusted and explained."
help:
  quick_fixes:
    - "Verify you are editing the player sprite, not backdrop or UI sprite."
    - "Find all movement scripts and keep one source of truth per direction."
    - "Use test loop: key press, observe, adjust, retest."
extend:
  - "Add a dash key with temporary speed boost."
  - "Add boundary rules so player cannot leave stage."
teacher_panel:
  purpose: "Teach agency through input mapping and controlled iteration."
  snags:
    - "Students duplicate movement logic across multiple scripts."
    - "Students set x instead of change x and break smooth movement."
  assessment:
    - "Student can explain what event triggers movement."
    - "Student can describe one tuning decision for feel/fairness."
helper_allowed_topics:
  - "use when key pressed event blocks"
  - "change keyboard mapping to wasd"
  - "difference between set x and change x"
  - "tune movement speed and boundaries"
  - "explain input behavior in plain language"
---
**Theme:** Agency through control mapping

## Objectives
- Identify input events (`when key pressed`).
- Change keyboard controls intentionally.
- Understand `set x` versus `change x`.

## Plan (60 minutes)
0-5 min: Entry routine.  
5-12 min: Mini-lesson on event-driven input mapping.  
12-35 min: Remix build sprint.
- Minimal path:
  - switch controls (for example arrows to WASD)
  - tune movement speed
- Extension path:
  - add dash mechanic
  - add stage boundary rules  
35-48 min: Pair-share code reading.
- Partner explains: "When I press __, it does __."  
48-55 min: Save/submit + two-sentence reflection.  
55-60 min: Exit ticket: identify whether today's main block was Event, Condition, or Variable.

## Reflection prompts
- "I changed controls from ___ to ___."
- "This made the game feel ___ because ___."

## Common pitfalls
- Editing wrong sprite.
- Splitting movement across too many scripts.
- Forgetting to retest after each change.

## Vocabulary focus
- Event
- Input
- Script
- Feedback
