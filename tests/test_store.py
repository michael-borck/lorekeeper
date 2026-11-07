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
    assert len(catalog["packs"]) == 29
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
    speak = by_id["speak-software"]
    assert speak["title"] == "Speak Software: Programming at the Natural-Language Layer"
    assert speak["lessons"] == 22
    assert speak["licence"] == "CC BY 4.0 International"
    web = by_id["build-web-guide-ai"]
    assert web["title"] == "Build Web, Guide AI: Business Web Development with AI"
    assert web["lessons"] == 27
    assert web["licence"] == "CC BY 4.0 International"
    sad = by_id["systems-analysis-and-design"]
    assert sad["title"] == "Frame the System, Guide the AI: Systems Analysis and Design in the AI Era"
    assert sad["lessons"] == 14
    assert sad["theme"] == "storybook"
    assert sad["licence"] == "CC BY 4.0 International"
    forensics = by_id["follow-the-trace"]
    assert forensics["title"] == "Follow the Trace, Prove the Case: Digital Forensics in Practice"
    assert forensics["lessons"] == 11
    assert forensics["licence"] == "CC BY 4.0 International"
    edge = by_id["the-human-edge"]
    assert edge["title"] == "The Human Edge: Using AI with Judgement"
    assert edge["lessons"] == 15
    assert edge["theme"] == "storybook"
    assert edge["licence"] == "CC BY 4.0 International"
    workbook = by_id["test-the-claim"]
    assert workbook["title"] == "Test the Claim, Rate the Control: A Tessera Audit Workbook"
    assert workbook["lessons"] == 11
    assert workbook["theme"] == "storybook"
    assert workbook["licence"] == "CC BY 4.0 International"
    substantiate = by_id["substantiate-dont-assume"]
    assert substantiate["lessons"] == 16
    assert substantiate["theme"] == "storybook"
    assert substantiate["licence"] == "CC BY 4.0 International"
    conversation = by_id["conversation-not-delegation"]
    assert conversation["lessons"] == 19
    assert conversation["theme"] == "storybook"
    assert conversation["licence"] == "CC BY 4.0 International"
    prove = by_id["prove-dont-persuade"]
    assert prove["lessons"] == 16
    assert prove["theme"] == "storybook"
    assert prove["licence"] == "CC BY 4.0 International"
    build_ai = by_id["build-ai-understand-ai"]
    assert build_ai["lessons"] == 22
    assert build_ai["theme"] == "pixel"
    assert build_ai["licence"] == "CC BY 4.0 International"
    hacking = by_id["break-with-permission"]
    assert hacking["lessons"] == 14
    assert hacking["theme"] == "pixel"
    assert hacking["licence"] == "CC BY 4.0 International"
    network = by_id["follow-the-packet"]
    assert network["lessons"] == 12
    assert network["theme"] == "pixel"
    assert network["licence"] == "CC BY 4.0 International"
    simplebot = by_id["simplebot"]
    assert simplebot["lessons"] == 12
    assert simplebot["theme"] == "pixel"
    assert simplebot["licence"] == "CC BY 4.0 International"
    build_it = by_id["build-it-teach-it"]
    assert build_it["lessons"] == 16
    assert build_it["theme"] == "storybook"
    assert build_it["licence"] == "CC BY 4.0 International"
    expected = {
        "think-python-direct-ai": 29,
        "code-python-consult-ai": 21,
        "ship-python-orchestrate-ai": 11,
        "converse-python-partner-ai": 18,
        "partner-dont-police": 17,
        "the-absolute-minimum-you-must-know": 31,
        "the-great-silence": 9,
        "programming-paradigms": 6,
        "simulate-it": 8,
        "ai-toys": 7,
        "security-toys": 7,
    }
    for pack_id, lessons in expected.items():
        assert by_id[pack_id]["lessons"] == lessons
        assert by_id[pack_id]["theme"] in {"pixel", "storybook"}
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
