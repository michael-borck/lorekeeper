import hashlib
import json
from pathlib import Path

from lorekeeper.store import build_store


def test_store_builds_catalog_and_pack(tmp_path: Path):
    catalog = build_store(tmp_path / "store")
    assert catalog["format"] == "lorekeeper.catalog"
    assert catalog["version"] == 1
    assert len(catalog["packs"]) == 1
    entry = catalog["packs"][0]
    assert entry["id"] == "pocket-incidents"
    assert entry["url"] == "packs/pocket-incidents.json"
    assert entry["lessons"] == 3
    pack_path = tmp_path / "store" / "packs" / "pocket-incidents.json"
    assert pack_path.is_file()
    digest = hashlib.sha256(pack_path.read_bytes()).hexdigest()
    assert entry["sha256"] == digest
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["format"] == "lorekeeper.pack"
    assert pack["courses"][0]["slug"] == "pocket-incidents"
    assert "stories/the-3am-page.json" in pack["courses"][0]["stories"]
