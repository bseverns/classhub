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
    allowed_topics: list[str] | None = None,
    reference_text: str = "",
    reference_citations: str = "",
) -> str:
    """Return the tutor stance string based on strictness + lesson scope."""
    base = (
        "You are a calm, encouraging homework helper. "
        "Teach by guiding: ask clarifying questions, give hints, outline steps, "
        "and check understanding. "
        "Keep responses concise."
    )

    topics = topics or []
    allowed_topics = allowed_topics or []
    scope_text = _format_scope(context, topics)
    scratch_signal = (
        "scratch" in (context or "").lower()
        or any("scratch" in t.lower() for t in topics)
        or "scratch" in (reference_text or "").lower()
    )
    if scratch_signal:
        base += (
            " This course uses Scratch (blocks-based). "
            "Do not answer in text programming languages (e.g., Pascal, Python, Java, C++). "
            "If asked about those, redirect to Scratch blocks and the current lesson."
        )
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
    if allowed_topics:
        base += (
            " Allowed topics for this lesson: "
            + ", ".join(allowed_topics)
            + ". If asked about something else, redirect to these topics."
        )

    if reference_text:
        base += (
            " Use the following reference facts as ground truth for this course. "
            + reference_text.strip()
            + " "
        )
    if reference_citations:
        base += (
            "Ground your answer in the lesson excerpts below when relevant. "
            "Quote short phrases and cite the excerpt id in brackets (example: [L1]). "
            "If the excerpts do not cover the question, say that briefly. "
            + reference_citations.strip()
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
