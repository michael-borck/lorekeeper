from pathlib import Path

from lorekeeper.signing import keygen
from lorekeeper.store import build_store
from lorekeeper.verify import verify_store


def make_store(tmp_path: Path):
    private = tmp_path / "private.pem"
    public = tmp_path / "public.txt"
    trusted = tmp_path / "trusted-keys.js"
    keygen(private, public, trusted)
    store = tmp_path / "store"
    build_store(store, key_path=private)
    return store, trusted


def test_verify_store_accepts_a_signed_catalogue(tmp_path: Path):
    store, trusted = make_store(tmp_path)
    assert verify_store(store, trusted) == []


def test_verify_store_rejects_tampered_pack(tmp_path: Path):
    store, trusted = make_store(tmp_path)
    pack = store / "packs" / "pocket-incidents.json"
    pack.write_bytes(pack.read_bytes() + b"\n")
    problems = verify_store(store, trusted)
    assert any("SHA-256" in problem or "size" in problem for problem in problems)


def test_verify_store_rejects_unknown_key(tmp_path: Path):
    store, _trusted = make_store(tmp_path)
    empty = tmp_path / "empty-keys.js"
    empty.write_text("window.LOREKEEPER_TRUSTED_KEYS = {};\n", encoding="utf-8")
    problems = verify_store(store, empty)
    assert any("no trusted public keys" in problem or "unknown signing key" in problem for problem in problems)


def test_keygen_append_keeps_existing_keys(tmp_path: Path):
    first_private = tmp_path / "first.pem"
    second_private = tmp_path / "second.pem"
    trusted = tmp_path / "trusted-keys.js"
    first = keygen(first_private, tmp_path / "first.txt", trusted)
    second = keygen(second_private, tmp_path / "second.txt", trusted, append=True)
    text = trusted.read_text(encoding="utf-8")
    assert first in text
    assert second in text
