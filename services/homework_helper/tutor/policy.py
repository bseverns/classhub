STRICTNESS_LIGHT = "light"
STRICTNESS_STRICT = "strict"
SCOPE_SOFT = "soft"
SCOPE_STRICT = "strict"


def _format_scope(context: str, topics: list[str]) -> str:
    parts = []
    if context:
        parts.append(f"Lesson context: {context}")
    if topics:
        parts.append("Topics: " + ", ".join(topics))
    return " ".join(parts)


def build_instructions(
    strictness: str,
    context: str = "",
    topics: list[str] | None = None,
    scope_mode: str = SCOPE_SOFT,
    reference_text: str = "",
) -> str:
    """Return the tutor stance string based on strictness + lesson scope."""
    base = (
        "You are a calm, encouraging homework helper. "
        "Teach by guiding: ask clarifying questions, give hints, outline steps, "
        "and check understanding. "
        "Keep responses concise."
    )

    topics = topics or []
    scope_text = _format_scope(context, topics)
    if scope_text:
        if scope_mode == SCOPE_STRICT:
            base += (
                " Only answer within this lesson scope. "
                + scope_text
                + " If the question is unrelated, say you can only help with this lesson "
                "and ask the student to rephrase."
            )
        else:
            base += (
                " Prefer answers grounded in this lesson. "
                + scope_text
                + " If the question seems unrelated, gently redirect it back to the lesson."
            )

    if reference_text:
        base += (
            " Use the following reference facts as ground truth for this course. "
            + reference_text.strip()
            + " "
        )

    if strictness == STRICTNESS_STRICT:
        return (
            base
            + " If asked for a final answer to graded work, refuse and instead "
            "provide a learning-oriented approach with hints."
        )

    # light (default): allow direct answers when appropriate, but keep them teach-first
    return (
        base
        + " You may provide direct answers when helpful, but always include reasoning "
        "and a short check-for-understanding question. Refuse clear cheating requests."
    )
