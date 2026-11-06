import json
from pathlib import Path

from lorekeeper.pack import PACK_FORMAT, build_pack, write_pack
from lorekeeper.registry import get_unit


def test_pack_builds_with_course_and_stories():
    pack = build_pack(get_unit("ISYS3004"))
    assert pack["format"] == PACK_FORMAT
    assert pack["version"] == 1
    assert pack["id"] == "ship-it"
    assert len(pack["courses"]) == 1
    course = pack["courses"][0]
    assert course["slug"] == "ship-it"
    assert course["course"]["unit"]["slug"] == "ship-it"
    assert "stories/launch-week.json" in course["stories"]
    assert "inkVersion" in course["stories"]["stories/launch-week.json"]
    assert course["start"] == "01-01"
    assert "web" in course["tags"]


def test_pack_writes_json(tmp_path: Path):
    out = write_pack(build_pack(get_unit("DEMO")), tmp_path / "field-kit.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["courses"][0]["slug"] == "field-kit"
    assert out.stat().st_size > 0
