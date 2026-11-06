import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from lorekeeper.signing import key_id, public_bytes
from lorekeeper.store import build_store


def test_store_builds_catalog_and_pack(tmp_path: Path):
    catalog = build_store(tmp_path / "store")
    assert catalog["format"] == "lorekeeper.catalog"
    assert catalog["version"] == 1
    assert len(catalog["packs"]) == 4
    by_id = {entry["id"]: entry for entry in catalog["packs"]}
    entry = by_id["pocket-incidents"]
    assert entry["url"] == "packs/pocket-incidents.json"
    assert entry["lessons"] == 3
    info = by_id["information-security"]
    assert info["title"] == "Information Security: A Field Guide"
    assert info["lessons"] == 24
    audit = by_id["audit-and-control"]
    assert audit["title"] == "Audit and Control: A Field Guide"
    assert audit["lessons"] == 24
    assert audit["theme"] == "storybook"
    assume = by_id["assume-breach"]
    assert assume["title"] == "Assume Breach: A First Course in Defensive Security"
    assert assume["lessons"] == 18
    assert assume["licence"] == "CC BY 4.0 International"
    pack_path = tmp_path / "store" / "packs" / "pocket-incidents.json"
    assert pack_path.is_file()
    digest = hashlib.sha256(pack_path.read_bytes()).hexdigest()
    assert entry["sha256"] == digest
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack["format"] == "lorekeeper.pack"
    assert pack["courses"][0]["slug"] == "pocket-incidents"
    assert "stories/the-3am-page.json" in pack["courses"][0]["stories"]


def test_store_pack_is_signed(tmp_path: Path):
    key_path = tmp_path / "signing.pem"
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    catalog = build_store(tmp_path / "store", key_path=key_path)
    entry = next(item for item in catalog["packs"] if item["id"] == "pocket-incidents")
    assert entry["keyId"] == key_id(key)
    assert entry["signature"]
    pack_bytes = (tmp_path / "store" / "packs" / "pocket-incidents.json").read_bytes()
    key.public_key().verify(
        base64.b64decode(entry["signature"]),
        pack_bytes,
    )
    assert public_bytes(key)  # public key is derivable
