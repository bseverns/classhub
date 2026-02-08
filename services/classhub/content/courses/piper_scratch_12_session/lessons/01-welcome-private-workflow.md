---
course: piper-scratch-12
session: 1
slug: s01-welcome-private-workflow
title: "Welcome to the Studio: Build the Controls (Piper StoryMode)"
duration_minutes: 75
makes: A saved file you own, and a calm routine for saving + submitting.
needs:
  - Piper computer kit (or any computer)
  - Piper desktop
privacy:
  - No camera required; voice optional.
  - Use a chosen name or nickname.
  - Save locally first; upload privately.
videos:
  - id: V01
    title: "Boot + desktop tour (Piper kit)"
    minutes: 4
    outcome: Boot safely, find Scratch, and navigate the desktop.
  - id: V06
    title: "Save privately: Download to your computer"
    minutes: 3
    outcome: Save an `.sb3` locally and find it again.
  - id: V09
    title: Submit `.sb3` to LMS + reopen later
    minutes: 4
    outcome: Upload work privately and reload it next time.
submission:
  type: file
  accepted:
    - .sb3
  naming: S01_test_save_v1.sb3
done_looks_like:
  - You downloaded an `.sb3` file.
  - You uploaded it to the LMS privately.
help:
  quick_fixes:
    - If something is frozen: reboot once.
    - If you can't find a file: open Downloads and sort by newest.
    - If you're stuck: submit a bug report with your `.sb3` or a screenshot.
extend:
  - Create a folder called `ScratchProjects/` and move your file into it.
  - Rename your file to `..._v2` after one change.
teacher_panel:
  purpose: Establish private-first habits and reduce anxiety by making the workflow predictable.
  snags:
    - Students can’t find Downloads.
    - Students confuse ‘share’ with ‘save’.
    - Login anxiety—offer app/offline path.
  assessment:
    - Student can produce a local `.sb3` file.
    - Student can submit without using public sharing.
helper_allowed_topics:
  - "boot and desktop basics"
  - "open scratch"
  - "make a small change"
  - "download .sb3"
  - "upload file"
  - "re-open project"
  - "upload .sb3"
  - "reboot once if frozen."
  - "check downloads"
---
**Mission:** Start from *zero*: build a simple **GPIO movement controller** in Piper StoryMode (Mars → Cheeseteroid), then connect the idea of **inputs → actions** to Scratch.

This session is designed for rooms where students may not start with a physical keyboard.
Students can begin with a mouse, then use **physical buttons** to control movement in a Minecraft-themed StoryMode world.

## Teacher prep (before class)
- Confirm Piper app is installed and **StoryMode** is available.
- Verify students can access **Mars** (Level 1). Cheeseteroid typically unlocks after Mars.
- Stage one wiring kit per station (breadboard + jumpers + buttons/contacts).
- Print:
  - **Handout 00A** (Piper StoryMode: Mars + Cheeseteroid)
  - **Handout 01** (Studio Rules + Controls)
- Optional: have a tiny Scratch demo ready that uses **on-screen buttons** (mouse clicks) to move a sprite.

## Materials
- Devices with Piper app + Scratch access
- Breadboard + jumper wires + buttons/contacts (per station)
- Mouse (per station)
- Timer visible
- Handouts (if used)

## Agenda (60 minutes)

**0:00–0:05 Launch**
- “Eyes on me — hands off controls.”
- Today’s mission: “We build a controller, then we use the same idea in Scratch.”
- Show the end goal (10 seconds): Piperbot moves + jumps, then a Scratch sprite moves with a clickable D‑pad.

**0:05–0:10 Preflight + Roles**
- Assign pairs if possible:
  - **Engineer:** wires + tests
  - **Navigator:** reads on-screen instructions + fetches parts
- Open Piper → StoryMode → Mars.

**0:10–0:30 Mars: Movement Controller**
- Students follow the Mars instructions to wire movement inputs (often Left / Forward / Right).
- Teacher moves station-to-station and checks for:
  - correct pin placement
  - shared ground
  - reliable button action

**0:30–0:45 Cheeseteroid: Add Jump**
- After Mars completion, students open Cheeseteroid and add the jump input.
- Call out the win condition: “Movement still works *and* jump works.”

**0:45–0:55 Scratch bridge: Inputs → Actions**
- Open Scratch (new project or a starter).
- Build a simple on-screen controller:
  - Draw two sprites: **Left** and **Right** (or a D-pad).
  - When Left sprite clicked → broadcast “LEFT”
  - When Right sprite clicked → broadcast “RIGHT”
  - Player sprite listens for broadcasts and moves.
- Emphasize the concept: “A button is just a message.”

**0:55–1:00 Save + Share**
- Save Scratch project with a naming rule.
- Quick share-out: “What was hardest about wiring? What made it work?”

## Notes + options
- If you want a follow-up hardware day later, see **Handout 00** (GPIO Keyboard Build) for a Scratch-focused keyboard interface.
