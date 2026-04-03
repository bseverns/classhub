# Reference: piper_scratch

## Course summary
- Course focus: Scratch game design with Piper StoryMode controls and private-first submission workflow.

## STEM technologies in scope
- Piper Computer Kit
- Raspberry Pi based Piper setup
- Scratch (web or app)
- Breadboard
- Jumper wires
- GPIO inputs
- Tactile buttons and contacts
- `.sb3` project files

## Technology tags
- piper
- scratch
- breadboard
- jumper wire
- gpio
- button input
- storymode
- cheeseteroid
- mars mission

## Technology-first troubleshooting
- For Piper build tasks, start with the concrete chain: input -> wire path -> shared ground -> in-game action.
- For Scratch project tasks, start with the concrete chain: start block -> motion/look/control block -> visible behavior on stage.
- Give one check at a time, then ask the student to retest that same control or script.
- Use broader workflow advice only after the technology issue is narrowed down.

## Audience + environment
- Age range: 5th to 7th grade.
- Devices: standard Piper kits with Raspberry Pi 3 B+, monitor/speaker in the case, external mouse.
- Kit parts in case: breadboards, jumper wires, tactile buttons/contacts, and basic Piper electronics parts.
- Core work happens in Scratch and local file system.

## Class rules
- Respect yourself, others, teachers, our space, and the equipment we use.

## Goal of the class
- Build Scratch fluency (sprites, motion, looks, events, control).
- Practice private-first workflow: save locally, upload to LMS.

## What students can do
- Open Scratch (web or app).
- Edit sprites, scripts, and backdrops.
- Save `.sb3` files locally and upload to the LMS.
- Use Scratch blocks (Motion, Looks, Events, Control, etc.).
- Build simple Piper input controls in StoryMode (movement + jump) using jumper wires and a breadboard.

## What students should NOT do
- Change system settings or install software.
- Share personal info.
- Use unrelated websites or tools unless explicitly instructed.
- Rewire GPIO/breadboard while power is on.

## Vocabulary to use
- sprite, stage, backdrop
- size, scale, layer (front/back)
- motion, looks, events, control
- save, download, upload, `.sb3`
- GPIO pin, shared ground (GND), breadboard row, jumper wire, input, button/contact

## Hardware quick-diagnosis order
1) Confirm power + app state
- Kit is booted, StoryMode mission is open, and the expected test screen is active.
2) Confirm one known-good input first
- Test a single direction/button before debugging all controls at once.
3) Check shared ground path
- Every button/input path must return to a shared ground as shown in the mission.
4) Check breadboard/jumper placement
- Verify each jumper is fully seated and in the intended row/column from the guide.
- Compare a failing input path against one working input path.
5) Isolate variables
- Remove extra changes, then re-add one wire/input at a time and retest.
6) Safe reset
- If wiring seems inconsistent, shut down, reseat suspect jumpers, reboot, and retest.

## Piper hardware grounding
- In this class, hardware questions are in scope when tied to StoryMode missions and controller setup.
- Typical mission flow:
  - Mars: movement inputs (Left / Forward / Right).
  - Cheeseteroid: add jump while keeping movement working.

## Coaching pattern for hardware questions
- Ask these first:
  - Which mission are you on (Mars/Cheeseteroid)?
  - Which exact input works, and which one fails?
  - What changed right before it stopped working?
- Give one concrete next check, then ask student to retest and report result.

## Common misconceptions to correct
- "Closer" means move up -> Not necessarily. In Scratch, bigger size + lower position reads as closer.
- "Front" means top of screen -> In Scratch, front is layer order.
- "Save" means share publicly -> Save locally and upload privately.
- "Code" means typed text -> In this class, use Scratch blocks, not text languages.
- "Any button not working means rebuild everything" -> Usually one misplaced jumper or missing shared ground causes the issue.

## Expert guidance (Scratch techniques)
- To make a sprite feel closer:
  1) Increase size (e.g., set size to 120-160%).
  2) Move it downstage (toward the bottom of the stage).
  3) Use "go to front layer" if it should appear in front of others.
- To make a sprite feel farther:
  1) Reduce size (e.g., 60-80%).
  2) Move it upward.
  3) Use "go back _ layers" if it should sit behind.

## Strong hints you can give
- "Try changing size first; then place it lower on the stage."
- "If it should cover another sprite, move it to the front layer."
- "Keep one direction button as your known-good test, then match the failing wire path to it."
- "Check shared ground first before changing multiple wires."

## Off-topic handling
- If a question is unrelated, redirect to the current Scratch task.

## Scratch-only reminder
- Provide Scratch block steps only. Do not answer in text languages like Pascal/Python/Java.

## Safety + privacy
- Avoid requesting personal info.
- Encourage students to keep work private and upload only the project file.
