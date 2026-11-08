"""Quest-mode narrators. The cast and their lines live in player/narrators.json."""

from __future__ import annotations

import json
from functools import lru_cache

from .registry import engine_root


@lru_cache(maxsize=1)
def narrator_ids() -> frozenset[str]:
    path = engine_root() / "player" / "narrators.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    return frozenset((data.get("narrators") or {}).keys())


def check_narrator(value: str, where: str) -> str:
    """Return a valid narrator id or an empty string (meaning: pick by tags)."""
    narrator = str(value or "").strip()
    if not narrator:
        return ""
    known = narrator_ids()
    if known and narrator not in known:
        choices = ", ".join(sorted(known))
        raise ValueError(f"{where}: unknown narrator '{narrator}' (choose one of: {choices})")
    return narrator
