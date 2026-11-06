"""Verify a static pack catalogue without the private signing key."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

TRUSTED_RE = re.compile(r'"([0-9a-f]{16})"\s*:\s*"([A-Za-z0-9+/=]+)"')


def load_trusted_keys(path: Path) -> dict[str, str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return {key_id: value for key_id, value in TRUSTED_RE.findall(text)}


def verify_store(store: Path, trusted: Path) -> list[str]:
    store = Path(store).resolve()
    problems: list[str] = []
    try:
        catalog = json.loads((store / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"catalog.json: {exc}"]
    if catalog.get("format") != "lorekeeper.catalog" or int(catalog.get("version", 0)) != 1:
        return ["catalog.json: wrong format or version"]

    keys = load_trusted_keys(trusted)
    if not keys:
        problems.append(f"{trusted}: no trusted public keys found")

    for entry in catalog.get("packs", []):
        pack_id = entry.get("id", "?")
        url = str(entry.get("url", ""))
        path = (store / url).resolve()
        if not url or not path.is_relative_to(store):
            problems.append(f"{pack_id}: pack path escapes the store")
            continue
        if not path.is_file():
            problems.append(f"{pack_id}: missing {url}")
            continue
        data = path.read_bytes()
        if entry.get("size") is not None and int(entry["size"]) != len(data):
            problems.append(f"{pack_id}: size does not match the catalogue")
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") != digest:
            problems.append(f"{pack_id}: SHA-256 does not match the catalogue")
        key_id = entry.get("keyId")
        signature = entry.get("signature")
        if not key_id or not signature:
            problems.append(f"{pack_id}: missing keyId or signature")
            continue
        public = keys.get(str(key_id))
        if not public:
            problems.append(f"{pack_id}: unknown signing key {key_id}")
            continue
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(public)).verify(
                base64.b64decode(signature), data
            )
        except (InvalidSignature, ValueError):
            problems.append(f"{pack_id}: signature is invalid")
    return problems
