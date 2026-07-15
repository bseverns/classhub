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
DEFAULT_STEM_TECHNOLOGY_KEYWORDS = [
    "scratch",
    "sprite",
    "sprites",
    "block",
    "blocks",
    "backdrop",
    "backdrops",
    "costume",
    "costumes",
    "broadcast",
    "variable",
    "variables",
    "loop",
    "loops",
    "animation",
    "game map",
    "score",
    "piper",
    "pipercode",
    "storymode",
    "breadboard",
    "jumper",
    "wire",
    "wiring",
    "gpio",
    "sensor",
    "button",
    "buttons",
]
_LOW_SIGNAL_SCOPE_TOKENS = {
    "about",
    "build",
    "change",
    "changed",
    "changes",
    "control",
    "explain",
    "help",
    "input",
    "inputs",
    "lesson",
    "make",
    "need",
    "output",
    "outputs",
    "part",
    "retest",
    "session",
    "state",
    "thing",
    "today",
    "understand",
    "using",
}
_CONTEXT_DEPENDENT_WORDS = {
    "also",
    "doesnt",
    "don't",
    "dont",
    "it",
    "its",
    "isnt",
    "isn't",
    "no",
    "not",
    "that",
    "there",
    "they",
    "this",
    "those",
    "what",
    "yes",
}

_SAFEGUARDING_PATTERNS = {
    "abuse": (
        re.compile(r"\b(?:being abused|abusing me|hit me at home)\b"),
        re.compile(r"\b(?:my (?:dad|father|mom|mother|parent|guardian)|an? adult|someone|he|she|they)\s+(?:hits?|hit|beats?|beat|hurts?|hurt|abuses?|abused)\s+me\b"),
    ),
    "sexual_harm": (
        re.compile(r"\b(?:an? adult|someone|he|she|they)\s+(?:touched|touches)\s+me\b"),
        re.compile(r"\b(?:someone|he|she|they)\s+(?:raped|sexually assaulted)\s+me\b"),
        re.compile(r"\b(?:i was|i am being|im being)\s+(?:raped|sexually assaulted)\b"),
    ),
    "unsafe": (
        re.compile(r"\bi (?:do not|dont) feel safe at home\b"),
        re.compile(r"\bi(?: am|m)? not safe at home\b"),
        re.compile(r"\bimmediate danger\b"),
    ),
    "weapon": (
        re.compile(r"\bi (?:have|have access to|can get) (?:a )?(?:gun|firearm|weapon)\b"),
        re.compile(r"\b(?:someone|he|she|they) has a gun\b"),
        re.compile(r"\bhas a gun\b"),
    ),
    "self_harm": (
        re.compile(r"\b(?:kill|hurt|cut) myself\b"),
        re.compile(r"\bself harm\b"),
        re.compile(r"\bsuicid(?:e|al)\b"),
        re.compile(r"\b(?:i )?(?:want|wish) to die\b"),
    ),
    "threat": (
        re.compile(r"\b(?:i(?: am|m)? going to|i will|im about to|i am about to)\s+(?:kill|hurt|shoot|stab)\s+(?:someone|him|her|them|you)\b"),
        re.compile(r"\bgoing to hurt someone\b"),
        re.compile(r"\bkill someone\b"),
    ),
}
_IMMINENT_PATTERNS = (
    re.compile(r"\b(?:right now|tonight|about to|immediate danger)\b"),
    re.compile(r"\bi (?:have|have access to|can get) (?:a )?(?:gun|firearm|weapon)\b"),
    re.compile(r"\bhas a gun\b"),
)
_GAME_VIOLENCE_RE = re.compile(
    r"\b(?:kill|hurt|shoot|stab)(?:ing)? someone in (?:my|the|a) (?:video )?game\b"
)


def parse_csv_list(raw: str) -> list[str]:
    return [part.strip().lower() for part in (raw or "").split(",") if part.strip()]


def contains_text_language(message: str, keywords: list[str]) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in keywords)


def contains_any_phrase(text: str, phrases: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(phrase and phrase in lowered for phrase in phrases)


def safeguarding_risk(message: str) -> str:
    lowered = (message or "").lower().replace("'", "").replace("’", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    if not normalized:
        return ""
    matched_categories = {
        category
        for category, patterns in _SAFEGUARDING_PATTERNS.items()
        if any(pattern.search(normalized) for pattern in patterns)
    }
    if matched_categories == {"threat"} and _GAME_VIOLENCE_RE.search(normalized):
        return ""
    if not matched_categories:
        return ""
    if "weapon" in matched_categories or any(pattern.search(normalized) for pattern in _IMMINENT_PATTERNS):
        return "imminent"
    return "disclosure"


def build_safeguarding_response(risk: str) -> str:
    base = (
        "I'm pausing tutoring because your safety matters more than the lesson. "
        "I can't promise to keep danger or abuse secret. Please tell a trusted adult, teacher, or facilitator now. "
        "You do not need to share names, an address, or more private details with me."
    )
    if risk == "imminent":
        return base + " If you or anyone else may be in immediate danger, move to a safer place and call local emergency services now."
    return base + " If the danger becomes immediate, call local emergency services."


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


def is_stem_technology_question(
    message: str,
    *,
    context_value: str = "",
    topics: list[str] | None = None,
    reference_text: str = "",
    keywords: list[str] | None = None,
) -> bool:
    lowered = (message or "").lower()
    keyword_list = keywords or DEFAULT_STEM_TECHNOLOGY_KEYWORDS
    if contains_any_phrase(lowered, keyword_list):
        return True
    if is_piper_hardware_question(message, keywords=DEFAULT_PIPER_HARDWARE_KEYWORDS):
        return True
    if not is_scratch_context(context_value, topics or [], reference_text):
        return False
    scratch_signals = (
        "animation",
        "backdrop",
        "broadcast",
        "costume",
        "game",
        "loop",
        "motion",
        "score",
        "sprite",
        "variable",
    )
    return any(signal in lowered for signal in scratch_signals)


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


def is_class_reentry_privacy_question(message: str) -> bool:
    lowered = (message or "").lower()
    has_identity_signal = any(token in lowered for token in ("full name", "real name", "name card"))
    has_return_signal = any(token in lowered for token in ("return code", "class code", "back into class", "get back into class"))
    return has_identity_signal and has_return_signal


def build_class_reentry_privacy_text() -> str:
    return (
        "You can rejoin without using your real name.\n"
        "In this Piper/Scratch class workflow, use your class code and your display name (pseudonym is okay).\n"
        "If your return code is missing, ask your teacher to reset or confirm your class code before you continue."
    )


def is_publish_privacy_question(message: str) -> bool:
    lowered = (message or "").lower()
    has_publish = any(token in lowered for token in ("publish", "share", "post"))
    has_name_privacy = any(token in lowered for token in ("full name", "real name", "name shown"))
    return has_publish and has_name_privacy


def build_publish_privacy_text() -> str:
    return (
        "Yes, you can publish without showing your full name.\n"
        "Use your display name for the share/post identity in class.\n"
        "If you want confirmation before you publish, ask your teacher to review the visibility settings first."
    )


def is_score_condition_debug_question(message: str) -> bool:
    lowered = (message or "").lower()
    has_score = "score" in lowered
    has_wrong_hit = any(token in lowered for token in ("wrong object", "wrong sprite", "even when i hit", "hit the wrong"))
    return has_score and has_wrong_hit


def build_score_condition_debug_text() -> str:
    return (
        "Use one debugging check first: find the score change block and add an if condition so score updates only on the correct target.\n"
        "Then check that the condition compares against the right sprite/object name.\n"
        "Run one test after that single check and tell me what changed."
    )


def is_wellbeing_reset_question(message: str) -> bool:
    lowered = (message or "").lower()
    has_overwhelm = any(token in lowered for token in ("nothing works", "i want to quit", "feel dumb", "i'm dumb", "im dumb"))
    return has_overwhelm


def build_wellbeing_reset_text() -> str:
    return (
        "You are not dumb. This happens to everyone when a build gets noisy.\n"
        "Take one small next step: test one input/block only, then stop and check the result.\n"
        "After that next step, tell me exactly what changed so we can pick the next tiny fix."
    )


def tokenize(text: str) -> set[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    return {p for p in parts if len(p) >= 4}


def _meaningful_scope_tokens(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in _LOW_SIGNAL_SCOPE_TOKENS}


def is_context_dependent_follow_up(message: str) -> bool:
    lowered = " ".join(str(message or "").strip().lower().split())
    if not lowered:
        return False
    if lowered in {
        "yes",
        "no",
        "maybe",
        "not sure",
        "i dont know",
        "i don't know",
        "there is",
        "there isn't",
        "there isnt",
        "it is",
        "it isn't",
        "it isnt",
    }:
        return True
    raw_words = [part for part in re.split(r"[^a-z0-9']+", lowered) if part]
    meaningful = _meaningful_scope_tokens(lowered)
    if len(raw_words) <= 6 and len(meaningful) <= 1:
        return True
    if len(raw_words) <= 8 and any(word in _CONTEXT_DEPENDENT_WORDS for word in raw_words) and len(meaningful) <= 2:
        return True
    return False


def allowed_topic_overlap(
    message: str,
    allowed_topics: list[str],
    *,
    context: str = "",
    topics: list[str] | None = None,
    reference_text: str = "",
) -> bool:
    if not allowed_topics:
        return True
    msg_tokens = _meaningful_scope_tokens(message)
    if not msg_tokens:
        return False
    topic_tokens: set[str] = set()
    for topic in allowed_topics:
        topic_tokens |= _meaningful_scope_tokens(topic)
    if msg_tokens & topic_tokens:
        return True

    scope_tokens: set[str] = set()
    if context:
        scope_tokens |= _meaningful_scope_tokens(context)
    for topic in topics or []:
        scope_tokens |= _meaningful_scope_tokens(topic)
    if reference_text:
        scope_tokens |= _meaningful_scope_tokens(reference_text)
    return bool(msg_tokens & scope_tokens)


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
