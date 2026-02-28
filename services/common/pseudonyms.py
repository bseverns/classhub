"""Pseudonym generator for privacy-forward student display names.

Generates friendly, deterministic-but-random display names in the format
"Adjective Noun NN" (e.g., "Curious Otter 17").  All output is ASCII-safe,
length-bounded (3–32 characters), and screened against a small denylist.

Usage:
    from common.pseudonyms import generate_pseudonym
    name = generate_pseudonym()   # "Brave Comet 42"
"""

from __future__ import annotations

import random

# ── Word lists ────────────────────────────────────────────────────────
# Kept intentionally short and friendly.  All lowercase for composition;
# the generator title-cases them.

ADJECTIVES: list[str] = [
    "brave", "bright", "calm", "clever", "cosmic", "curious", "daring",
    "eager", "fair", "fast", "fearless", "friendly", "gentle", "glad",
    "happy", "jolly", "keen", "kind", "lively", "lucky", "merry",
    "mighty", "neat", "noble", "plucky", "proud", "quick", "quiet",
    "ready", "sharp", "shiny", "smart", "snappy", "speedy", "steady",
    "sunny", "swift", "warm", "wise", "witty", "zappy", "zen",
    "zippy", "bold", "cool", "epic", "fresh", "grand", "vivid",
]

NOUNS: list[str] = [
    "badger", "bear", "comet", "condor", "coyote", "crane", "dolphin",
    "dragon", "eagle", "falcon", "finch", "fox", "gecko", "hawk",
    "heron", "husky", "ibis", "jaguar", "kite", "koala", "lemur",
    "lynx", "marten", "moose", "newt", "orca", "osprey", "otter",
    "owl", "panda", "parrot", "penguin", "phoenix", "pixel", "puma",
    "quail", "raven", "robin", "rover", "seal", "spark", "squid",
    "starling", "tiger", "toucan", "turtle", "viper", "wombat", "wren",
]

# ── Denylist ──────────────────────────────────────────────────────────
# Minimal set of terms that should never appear in generated pseudonyms.
# Checked against the combined lowercase output.  Extend conservatively –
# the generator only uses the word lists above, so only add terms that
# could emerge from *combinations* of those words.

DENYLIST: frozenset[str] = frozenset({
    "dead",
    "die",
    "drug",
    "drunk",
    "dumb",
    "fat",
    "gun",
    "hate",
    "hell",
    "kill",
    "nazi",
    "nude",
    "rape",
    "sex",
    "slut",
    "stupid",
    "ugly",
})


def generate_pseudonym(*, _rng: random.Random | None = None) -> str:
    """Return a friendly pseudonym like ``"Curious Otter 17"``.

    Parameters
    ----------
    _rng : random.Random, optional
        Injectable RNG for deterministic testing.  Production callers
        should omit this (uses module-level ``random``).

    Returns
    -------
    str
        ASCII-safe display name, 3–32 characters.
    """
    choose = (_rng or random).choice
    for _ in range(50):
        adj = choose(ADJECTIVES).title()
        noun = choose(NOUNS).title()
        num = (_rng or random).randint(10, 99)
        candidate = f"{adj} {noun} {num}"

        # Length guard (should always pass with current word lists).
        if not (3 <= len(candidate) <= 32):
            continue  # pragma: no cover

        # Denylist screen on the full lowercase string.
        lower = candidate.lower()
        if any(term in lower for term in DENYLIST):
            continue  # pragma: no cover

        return candidate

    # Fallback (essentially unreachable with current word lists).
    return "Student " + str(random.randint(10, 99))  # pragma: no cover


__all__ = [
    "ADJECTIVES",
    "DENYLIST",
    "NOUNS",
    "generate_pseudonym",
]
