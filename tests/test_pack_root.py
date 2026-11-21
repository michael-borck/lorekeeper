from pathlib import Path

from lorekeeper.pack import build_pack, unit_from_root
from lorekeeper.registry import get_unit


def test_pack_from_an_unregistered_unit_folder(tmp_path: Path):
    root = get_unit("field-kit").root
    unit = unit_from_root(
        root,
        unit_id="demo-pack",
        title="Demo Pack",
        theme="pixel",
        tags=["demo", "practice"],
        level="beginner",
        pitch="A test pack.",
        start="01-01",
    )
    assert unit.slug == "demo-pack"
    assert unit.title == "Demo Pack"
    pack = build_pack(unit, tmp_path)
    assert pack["id"] == "demo-pack"
    assert pack["courses"][0]["slug"] == "demo-pack"
    assert pack["courses"][0]["title"] == "Demo Pack"
    assert pack["courses"][0]["course"]["unit"]["slug"] == "demo-pack"
    assert pack["courses"][0]["course"]["unit"]["tags"] == ["demo", "practice"]
