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


def is_mouse_only_access_question(message: str) -> bool:
    lowered = (message or "").lower()
    if "mouse" not in lowered:
        return False
    keyboard_signals = ("no keyboard", "without keyboard", "only have a mouse", "just a mouse")
    can_i_signals = ("can i", "still do", "session", "lesson")
    return any(signal in lowered for signal in keyboard_signals) or any(signal in lowered for signal in can_i_signals)


def build_mouse_only_adaptation_text() -> str:
    return (
        "Yes, you can still do this session with a mouse.\n"
        "Use a mouse-first path in StoryMode: click through prompts, then test one input/button at a time.\n"
        "If one control fails, check that button wire path and shared ground, then test again.\n"
        "Tell me which mission (Mars or Cheeseteroid) you are on and what changed after you test again."
    )


def is_teamwork_decision_question(message: str) -> bool:
    lowered = (message or "").lower()
    has_partner = any(token in lowered for token in ("partner", "teammate", "team member"))
    has_conflict = any(token in lowered for token in ("disagree", "argument", "argue", "whose code", "which code", "decide"))
    return has_partner and has_conflict


def build_teamwork_decision_text() -> str:
    return (
        "Decide together using evidence, not volume.\n"
        "1) Test your version together on the same scenario.\n"
        "2) Test your partner's version together on that same scenario.\n"
        "3) Decide which version is clearer and more reliable for class goals.\n"
        "4) Merge the best ideas and keep a backup copy of both versions."
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


def classify_intent(message: str) -> str:
    lowered = (message or "").strip().lower()
    if not lowered:
        return "general"
    if any(token in lowered for token in ("error", "not working", "doesn't", "doesnt", "can't", "cant", "stuck", "broken", "fail")):
        return "debug"
    if any(token in lowered for token in ("what is", "why", "explain", "define", "mean", "difference")):
        return "concept"
    if any(token in lowered for token in ("next step", "what should i do", "how do i start", "plan", "first step", "sequence")):
        return "strategy"
    if any(token in lowered for token in ("is this right", "check my", "did i do", "review this", "how did i do")):
        return "reflection"
    if any(token in lowered for token in ("done", "finished", "submitted", "complete", "completed")):
        return "status"
    return "general"


def build_follow_up_suggestions(
    *,
    intent: str,
    context: str,
    topics: list[str],
    allowed_topics: list[str],
    history_summary: str = "",
    max_items: int = 3,
) -> list[str]:
    limit = max(int(max_items), 1)
    topic_hint = _pick_topic_hint(allowed_topics=allowed_topics, topics=topics, context=context, history_summary=history_summary)
    rows = _follow_up_templates(intent=intent, topic_hint=topic_hint)
    unique: list[str] = []
    for row in rows:
        suggestion = _normalize_suggestion(row)
        if not suggestion:
            continue
        if suggestion in unique:
            continue
        unique.append(suggestion)
        if len(unique) >= limit:
            break
    return unique


def _pick_topic_hint(*, allowed_topics: list[str], topics: list[str], context: str, history_summary: str) -> str:
    for candidate in [*(allowed_topics or []), *(topics or []), context or "", history_summary or ""]:
        cleaned = _normalize_topic(candidate)
        if cleaned:
            return cleaned
    return "this lesson"


def _normalize_topic(raw: str) -> str:
    value = " ".join(str(raw or "").strip().split())
    if not value:
        return ""
    return value[:48]


def _normalize_suggestion(raw: str) -> str:
    value = " ".join(str(raw or "").strip().split())
    if not value:
        return ""
    if value[-1] not in ".?!":
        value = value + "?"
    return value[:140]


def _follow_up_templates(*, intent: str, topic_hint: str) -> list[str]:
    key = str(intent or "").strip().lower()
    if key == "debug":
        return [
            "What did you try right before the issue happened",
            f"Which one test can you run next for {topic_hint}",
            "What changed after your last test",
        ]
    if key == "concept":
        return [
            "Can you explain this idea in your own words",
            f"Where do you see {topic_hint} in your project",
            "Want a quick concrete example",
        ]
    if key == "strategy":
        return [
            "What is the smallest next step you can do now",
            "What result will tell you that step worked",
            f"Want a 3-step plan for {topic_hint}",
        ]
    if key == "reflection":
        return [
            "What part feels strongest so far",
            "What part still needs one improvement",
            "Want feedback on one specific section first",
        ]
    if key == "status":
        return [
            "Which requirement is still incomplete",
            f"Want a quick submit checklist for {topic_hint}",
            "Do you want to verify one final detail before submitting",
        ]
    return [
        "What have you already tried",
        "What did you expect to happen",
        "Want one small next step",
    ]


def truncate_response_text(text: str, *, max_chars: int) -> tuple[str, bool]:
    limit = max(int(max_chars), 200)
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip(), True
