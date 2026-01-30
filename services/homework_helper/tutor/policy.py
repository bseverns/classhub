STRICTNESS_LIGHT = "light"
STRICTNESS_STRICT = "strict"


def build_instructions(strictness: str) -> str:
    """Return the tutor stance string based on strictness.

    The strictness switch is intentionally simple so teachers can flip it
    without changing code.
    """
    base = (
        "You are a calm, encouraging homework helper. "
        "Teach by guiding: ask clarifying questions, give hints, outline steps, "
        "and check understanding. "
        "Keep responses concise."
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
