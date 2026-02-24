"""Policy/heuristic helpers for helper chat behavior."""

from __future__ import annotations

import re

DEFAULT_TEXT_LANGUAGE_KEYWORDS = [
    "pascal",
    "python",
    "java",
    "javascript",
    "typescript",
    "c++",
    "c#",
    "csharp",
    "ruby",
    "php",
    "go",
    "golang",
    "rust",
    "swift",
    "kotlin",
]
DEFAULT_PIPER_CONTEXT_KEYWORDS = [
    "piper",
    "storymode",
    "pipercode",
    "mars",
    "cheeseteroid",
    "gpio",
    "breadboard",
]
DEFAULT_PIPER_HARDWARE_KEYWORDS = [
    "storymode",
    "mars",
    "cheeseteroid",
    "breadboard",
    "jumper",
    "wire",
    "wiring",
    "gpio",
    "button",
    "buttons",
    "physical controls",
    "controls not working",
]


def parse_csv_list(raw: str) -> list[str]:
    return [part.strip().lower() for part in (raw or "").split(",") if part.strip()]


def contains_text_language(message: str, keywords: list[str]) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in keywords)


def contains_any_phrase(text: str, phrases: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(phrase and phrase in lowered for phrase in phrases)


def is_scratch_context(context_value: str, topics: list[str], reference_text: str) -> bool:
    if "scratch" in (context_value or "").lower():
        return True
    if any("scratch" in t.lower() for t in topics):
        return True
    if "scratch" in (reference_text or "").lower():
        return True
    return False


def is_piper_context(
    context_value: str,
    topics: list[str],
    reference_text: str,
    *,
    reference_key: str = "",
    keywords: list[str],
) -> bool:
    combined = " ".join(
        [
            context_value or "",
            " ".join(topics or []),
            reference_text or "",
            reference_key or "",
        ]
    )
    return contains_any_phrase(combined, keywords)


def is_piper_hardware_question(message: str, *, keywords: list[str]) -> bool:
    return contains_any_phrase(message, keywords)


def select_piper_hardware_check(message: str) -> str:
    lowered = (message or "").lower()
    if any(token in lowered for token in ("jump", "cheeseteroid")):
        return "Check only the jump input path: confirm jumper seating and shared ground for that jump control."
    if any(token in lowered for token in ("none", "all", "every", "nothing")) and any(
        token in lowered for token in ("button", "buttons", "control", "controls", "wire", "wiring")
    ):
        return "Check shared ground first, then reseat one suspect jumper wire and retest before changing anything else."
    if any(token in lowered for token in ("left", "right", "forward", "back", "direction", "one direction")):
        return "Compare the failing direction wire path to a known-good direction and change only one mismatch."
    if any(token in lowered for token in ("storymode", "mars", "step", "level")):
        return "Confirm you are on the exact StoryMode test step where controls are evaluated before rewiring."
    return "Pick one input, verify its jumper path and shared ground, then retest only that single input."


def build_piper_hardware_triage_text(message: str) -> str:
    one_check = select_piper_hardware_check(message)
    return (
        "Let's triage this in one pass.\n"
        "1) Which StoryMode mission + step are you on (Mars or Cheeseteroid), and which single input fails?\n"
        f"2) Do this one check now: {one_check}\n"
        "3) Retest only that same input and tell me: works now, still fails, or changed behavior."
    )


def tokenize(text: str) -> set[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    return {p for p in parts if len(p) >= 4}


def allowed_topic_overlap(message: str, allowed_topics: list[str]) -> bool:
    if not allowed_topics:
        return True
    msg_tokens = tokenize(message)
    if not msg_tokens:
        return False
    topic_tokens: set[str] = set()
    for topic in allowed_topics:
        topic_tokens |= tokenize(topic)
    return bool(msg_tokens & topic_tokens)


def truncate_response_text(text: str, *, max_chars: int) -> tuple[str, bool]:
    limit = max(int(max_chars), 200)
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip(), True

