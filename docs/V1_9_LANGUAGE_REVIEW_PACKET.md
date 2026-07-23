# v1.9 Language Review Packet

Purpose: collect the human-reviewed language needed to close F2 and F3 without treating generated copy as safety or instructional evidence.

Status: **F2 and F3 remain open until the reviewer fields and target-language rows below are complete.**

## Reviewer requirements

- Use a proficient speaker of each target language who understands youth-facing classroom language.
- For safeguarding text, the reviewer must check directness, urgency, and whether a learner would understand the next action.
- Record the reviewer, review date, dialect/locale, and outcome. Do not paste learner disclosures or other personal information into this document.

## F2 — S'gaw Karen deterministic safeguarding

Target locale: S'gaw Karen (`ksw`).

Runtime integration points after approval:

- detection phrases: `services/homework_helper/tutor/engine/heuristics.py`
- fixed response copy: `build_safeguarding_response()` in the same module
- endpoint and false-positive checks: `services/homework_helper/tutor/tests/test_engine.py` and `test_chat_endpoint.py`

### Detection phrase review

Supply ordinary first-person phrases a learner would naturally use. Add more than one phrase where wording varies materially.

| Category | English meaning to cover | Reviewed S'gaw Karen phrase(s) | Reviewer notes |
|---|---|---|---|
| Abuse | My parent/caregiver hits or hurts me. |  |  |
| Sexual harm | An adult/teacher is touching me or made me undress. |  |  |
| Unsafe home | I do not feel safe at home. |  |  |
| Self-harm | I want to die / hurt or kill myself. |  |  |
| Threat to others | I am going to hurt or kill someone. |  |  |
| Weapon | I have or can get a gun/weapon. |  |  |
| Immediate danger | This is happening now / tonight / I am about to act. |  |  |
| Negative classroom example | A character says one of these phrases in a lesson/story; this should not be treated as a learner disclosure. |  |  |

### Fixed response review

**Disclosure source**

> I'm pausing tutoring because your safety matters more than the lesson. I can't promise to keep danger or abuse secret. Please tell a trusted adult, teacher, or facilitator now. You do not need to share names, an address, or more private details with me. If the danger becomes immediate, call local emergency services.

Reviewed S'gaw Karen:

>

**Immediate-danger source**

> I'm pausing tutoring because your safety matters more than the lesson. I can't promise to keep danger or abuse secret. Please tell a trusted adult, teacher, or facilitator now. You do not need to share names, an address, or more private details with me. If you or anyone else may be in immediate danger, move to a safer place and call local emergency services now.

Reviewed S'gaw Karen:

>

### F2 sign-off

- Reviewer:
- Dialect/locale:
- Review date:
- Outcome: `approved` / `changes requested`
- Notes:

F2 closes only after the approved phrases are implemented at the shared deterministic boundary, fixed response copy is selected by the active language, and focused tests prove the model backend is skipped without logging the disclosure.

## F3 — substantive translated handout

Source lesson:

- Course: `scratch_intro_games_code_grade9_6_session`
- Lesson: `s01-what-is-a-game-what-is-scratch`
- Source file: `services/classhub/content/courses/scratch_intro_games_code_grade9_6_session/lessons/01-what-is-a-game-what-is-scratch.md`

The approved text will be added as explicit `offline_handout.localized.es`, `.so`, and `.ksw` variants. The handout switcher will not advertise a language until its complete reviewed variant exists.

### English source handout

| Field | Source text |
|---|---|
| Title | What Is a Game? What Is Scratch? |
| Goal | Remix a starter game and explain one intentional gameplay change. |
| Do now 1 | Open the Scratch starter project. |
| Do now 2 | Rename your remix using the class naming pattern. |
| Do now 3 | Choose one visible change to test first. |
| Submit | Submit your `.sb3` file or a screenshot, plus two sentences: “I changed ___.” and “It made the game ___.” |
| Privacy/safety | Use your class display name. Do not put personal information in the file name or reflection. |

### Spanish (`es`)

- Reviewer:
- Review date:
- Locale/dialect:
- Title:
- Goal:
- Do now 1:
- Do now 2:
- Do now 3:
- Submit:
- Privacy/safety:
- Outcome: `approved` / `changes requested`

### Somali (`so`)

- Reviewer:
- Review date:
- Locale/dialect:
- Title:
- Goal:
- Do now 1:
- Do now 2:
- Do now 3:
- Submit:
- Privacy/safety:
- Outcome: `approved` / `changes requested`

### S'gaw Karen (`ksw`)

- Reviewer:
- Review date:
- Locale/dialect:
- Title:
- Goal:
- Do now 1:
- Do now 2:
- Do now 3:
- Submit:
- Privacy/safety:
- Outcome: `approved` / `changes requested`

F3 closes when all three approved variants are authored in the lesson, rendered-route tests prove the translated instructional handout is selected, and the reviewer/date provenance remains in this packet.
