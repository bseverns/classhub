"""Localized helper widget content helpers."""

from __future__ import annotations

import json

from django.utils.translation import gettext as _


def build_helper_prompt_sets() -> dict[str, list[dict[str, str]]]:
    return {
        "piper": [
            {
                "label": _("Jump not working"),
                "prompt": _(
                    "In StoryMode, left/right work but jump does not work in Cheeseteroid. Help me troubleshoot one step at a time."
                ),
            },
            {
                "label": _("No buttons respond"),
                "prompt": _(
                    "None of my StoryMode breadboard buttons are responding. Give me one check at a time and ask me to retest."
                ),
            },
            {
                "label": _("One direction fails"),
                "prompt": _(
                    "Only one movement direction fails on my Piper controls. What should I compare first in my jumper wiring path?"
                ),
            },
            {
                "label": _("Mouse-only path"),
                "prompt": _("I only have a mouse right now, no keyboard. What is the mouse-first path for this lesson?"),
            },
            {
                "label": _("Upload .sb3 help"),
                "prompt": _("I finished but cannot find my .sb3 file to upload. Walk me through check -> retest steps."),
            },
        ],
        "scratch": [
            {
                "label": _("Sprite won't move"),
                "prompt": _("My sprite does not move when I click the green flag. Please give me one Scratch block check at a time."),
            },
            {
                "label": _("Backdrop won't change"),
                "prompt": _("My backdrop never changes. What is one specific Scratch block check I should do first?"),
            },
            {
                "label": _("Score not updating"),
                "prompt": _("My score is not updating correctly. Help me debug in small steps and retest after each change."),
            },
            {
                "label": _("Game over missing"),
                "prompt": _("My game over condition does not trigger. Give me one event/broadcast check and then ask me to retest."),
            },
            {
                "label": _("Save and upload"),
                "prompt": _("Please walk me through saving my Scratch project as .sb3 and uploading it privately."),
            },
        ],
        "general": [
            {
                "label": _("What is today's goal?"),
                "prompt": _("What is the goal for this lesson, and what should be done first?"),
            },
            {
                "label": _("I am stuck"),
                "prompt": _("I am stuck. Ask me one clarifying question, then give me one small next step."),
            },
            {
                "label": _("How to ask better"),
                "prompt": _("Help me write a clear help request: what I expected, what happened, and what I already tried."),
            },
        ],
    }


def build_helper_prompt_sets_json() -> str:
    return json.dumps(build_helper_prompt_sets(), ensure_ascii=False)
