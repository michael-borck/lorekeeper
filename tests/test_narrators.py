import json
import re
from pathlib import Path

import pytest

from lorekeeper.compile import _lesson_from_spec
from lorekeeper.narrators import check_narrator, narrator_ids
from lorekeeper.pack import build_pack, unit_from_root
from lorekeeper.registry import Unit, engine_root

ROOT = Path(__file__).resolve().parents[1]
KINDS = [
    "reading", "checkpoint", "exercise", "order", "fill", "hotspot", "review",
    "scenario", "calibration", "viva", "api", "sql", "terminal", "story",
]


def data() -> dict:
    return json.loads((ROOT / "player" / "narrators.json").read_text(encoding="utf-8"))


def all_lines(payload: dict):
    for kind, lines in payload["standard"].items():
        for line in lines:
            yield f"standard.{kind}", line
    for narrator, info in payload["narrators"].items():
        for group in ("kinds", "moments"):
            for name, lines in info[group].items():
                for line in lines:
                    yield f"{narrator}.{name}", line


def test_every_narrator_covers_every_kind_and_moment():
    payload = data()
    assert payload["format"] == "lorekeeper.narrators"
    for kind in KINDS:
        assert len(payload["standard"][kind]) >= 2, kind
    for narrator, info in payload["narrators"].items():
        assert (ROOT / "player" / info["src"]).is_file(), narrator
        for kind in KINDS:
            assert len(info["kinds"][kind]) >= 2, f"{narrator}.{kind}"
        for moment in payload["moments"]:
            assert len(info["moments"][moment]) >= 2, f"{narrator}.{moment}"


def test_lines_are_short_plain_and_use_known_placeholders():
    for where, line in all_lines(data()):
        assert 8 <= len(line) <= 120, where
        assert "\u2014" not in line and "\u2013" not in line, where
        assert set(re.findall(r"\{(\w+)\}", line)) <= {"chapter", "course"}, where


def test_player_cast_matches_data_file():
    quest = (ROOT / "player" / "quest.js").read_text(encoding="utf-8")
    block = quest.split("const NARRATORS = {", 1)[1].split("};", 1)[0]
    in_player = set(re.findall(r"^\s*(\w+): \{ name:", block, re.MULTILINE))
    assert in_player == set(data()["narrators"]) == set(narrator_ids())


def test_unknown_narrator_is_rejected():
    assert check_narrator("", "x") == ""
    assert check_narrator("oracle", "x") == "oracle"
    with pytest.raises(ValueError, match="unknown narrator"):
        check_narrator("wizard", "x")


def test_lesson_narration_is_compiled_and_bounded():
    unit = Unit(key="t", code="T", slug="t", title="T", root=engine_root())
    module = {"number": 1, "slug": "01-t", "title": "T", "dir": engine_root()}
    spec = {"id": "01-01", "kind": "order", "title": "Order", "items": ["A", "B"],
            "explanation": "Why.", "narration": "  A custom line.  "}
    assert _lesson_from_spec(unit, module, spec, "01-01")["narration"] == "A custom line."
    with pytest.raises(ValueError, match="narration"):
        _lesson_from_spec(unit, module, {**spec, "narration": "x" * 401}, "01-01")


def test_pack_carries_author_narrator(tmp_path: Path):
    unit = unit_from_root(engine_root() / "demo-course", unit_id="demo-pack", title="Demo", narrator="mentor")
    pack = build_pack(unit, tmp_path)
    entry = pack["courses"][0]
    assert entry["narrator"] == "mentor"
    assert entry["course"]["unit"]["narrator"] == "mentor"


def test_every_store_pack_has_a_valid_narrator():
    from lorekeeper.store import PACK_NARRATOR

    catalog = json.loads((ROOT / "store" / "catalog.json").read_text(encoding="utf-8"))
    assert {pack["id"] for pack in catalog["packs"]} == set(PACK_NARRATOR)
    assert set(PACK_NARRATOR.values()) <= narrator_ids()
