"""Build the static pack catalogue and the sample store pack."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .book import build_book_pack
from .compile import compile_unit
from .pack import build_pack, unit_from_root
from .registry import engine_root, get_unit
from .signing import key_id, load_private_key, sign_bytes

CATALOG_FORMAT = "lorekeeper.catalog"
CATALOG_VERSION = 1
STORE_PACK = "pocket-incidents"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pocket_incidents(build_root: Path) -> dict:
    unit = get_unit("ISYS2008")
    source = compile_unit(unit, build_root)
    module = next(
        module for module in source["modules"] if module.get("number") == 11
    )
    module = copy.deepcopy(module)
    module["number"] = 1
    module["slug"] = "incident"
    for lesson in module["lessons"]:
        if str(lesson.get("id", "")).startswith("11-"):
            lesson["id"] = "01-" + str(lesson["id"])[3:]

    story_src = "stories/the-3am-page.json"
    story_path = build_root / "signal-and-noise" / story_src
    if not story_path.is_file():
        raise FileNotFoundError(f"story not found: {story_path}")

    course = {
        "schema": 1,
        "generated_at": _now(),
        "unit": {
            "slug": STORE_PACK,
            "title": "Pocket Incidents: The 3AM Page",
            "theme": "pixel",
            "tags": ["incident", "security", "systems", "story"],
            "level": "beginner",
            "pitch": "A short incident-response pack: evidence, containment and the record.",
            "start": "01-01",
        },
        "modules": [module],
    }

    return {
        "format": "lorekeeper.pack",
        "version": 1,
        "id": STORE_PACK,
        "title": "Pocket Incidents: The 3AM Page",
        "author": "Lorekeeper",
        "licence": "Course content",
        "createdAt": _now(),
        "courses": [
            {
                "slug": STORE_PACK,
                "title": "Pocket Incidents: The 3AM Page",
                "theme": "pixel",
                "level": "beginner",
                "tags": ["incident", "security", "systems", "story"],
                "pitch": "A short incident-response pack: evidence, containment and the record.",
                "start": "01-01",
                "course": course,
                "stories": {
                    story_src: json.loads(story_path.read_text(encoding="utf-8"))
                },
            }
        ],
    }


def _information_security(build_root: Path) -> dict:
    root = engine_root().parent / "isys2012-information-security"
    if not root.is_dir():
        raise FileNotFoundError(f"information security source not found: {root}")
    unit = unit_from_root(
        root,
        unit_id="information-security",
        title="Information Security: A Field Guide",
        theme="pixel",
        tags=["security", "risk", "operations", "incident"],
        level="beginner",
        pitch="A field guide to software security, malware, cryptography and incident planning.",
        start="01-01",
    )
    pack = build_pack(unit, build_root)
    pack["licence"] = "Course content"
    return pack


def _audit_and_control(build_root: Path) -> dict:
    root = engine_root().parent / "isys6018-information-security-audit-and-control"
    if not root.is_dir():
        raise FileNotFoundError(f"audit and control source not found: {root}")
    unit = unit_from_root(
        root,
        unit_id="audit-and-control",
        title="Audit and Control: A Field Guide",
        theme="storybook",
        tags=["audit", "risk", "controls", "compliance", "security"],
        level="intermediate",
        pitch="A field guide to audit evidence, risk, controls and professional judgement.",
        start="01-01",
    )
    pack = build_pack(unit, build_root)
    pack["licence"] = "Course content"
    return pack


def _assume_breach() -> dict:
    root = engine_root().parents[2] / "books" / "assume-breach"
    if not root.is_dir():
        raise FileNotFoundError(f"assume breach source not found: {root}")
    return build_book_pack(
        root,
        unit_id="assume-breach",
        title="Assume Breach: A First Course in Defensive Security",
        theme="pixel",
        tags=["security", "risk", "incident", "foundations"],
        level="beginner",
        pitch="A first course in defensive security: what to protect, where to spend, and how to respond.",
    )


def _speak_software() -> dict:
    root = engine_root().parents[2] / "books" / "speak-software"
    if not root.is_dir():
        raise FileNotFoundError(f"speak software source not found: {root}")
    return build_book_pack(
        root,
        unit_id="speak-software",
        title="Speak Software: Programming at the Natural-Language Layer",
        theme="pixel",
        tags=["ai", "programming", "agents", "testing"],
        level="beginner",
        pitch="Program at the natural-language layer: specify, verify, decompose and ship software with an AI agent.",
    )


def _build_web_guide_ai() -> dict:
    root = engine_root().parents[2] / "books" / "build-web-guide-ai"
    if not root.is_dir():
        raise FileNotFoundError(f"build web guide ai source not found: {root}")
    return build_book_pack(
        root,
        unit_id="build-web-guide-ai",
        title="Build Web, Guide AI: Business Web Development with AI",
        theme="pixel",
        tags=["web", "html", "css", "javascript", "cms", "react"],
        level="beginner",
        pitch="Build business websites with an AI partner: specify, check, structure, connect and hand over.",
        parts="1-6",
    )


def _systems_analysis_and_design() -> dict:
    root = engine_root().parents[2] / "books" / "systems-analysis-and-design"
    if not root.is_dir():
        raise FileNotFoundError(f"systems analysis source not found: {root}")
    return build_book_pack(
        root,
        unit_id="systems-analysis-and-design",
        title="Frame the System, Guide the AI: Systems Analysis and Design in the AI Era",
        theme="storybook",
        tags=["analysis", "design", "requirements", "systems", "ai", "governance"],
        level="beginner",
        pitch="Frame the problem, make requirements checkable, model the decisions and hand over a system that may contain AI.",
        parts="1-4",
    )


def _write_pack(out: Path, pack: dict, key) -> dict:
    packs_dir = out / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    pack_path = packs_dir / f"{pack['id']}.json"
    pack_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pack_bytes = pack_path.read_bytes()
    entry = pack["courses"][0]
    return {
        "id": pack["id"],
        "title": pack["title"],
        "description": entry["pitch"],
        "version": "1.0.0",
        "author": pack["author"],
        "licence": pack["licence"],
        "theme": entry["theme"],
        "tags": entry["tags"],
        "level": entry["level"],
        "courses": len(pack["courses"]),
        "lessons": sum(len(module["lessons"]) for module in entry["course"]["modules"]),
        "size": pack_path.stat().st_size,
        "sha256": hashlib.sha256(pack_bytes).hexdigest(),
        "keyId": key_id(key) if key else None,
        "signature": sign_bytes(key, pack_bytes) if key else None,
        "url": f"packs/{pack['id']}.json",
    }


def build_store(
    out: Path,
    build_root: Path | None = None,
    key_path: Path | None = None,
) -> dict:
    out = out.resolve()
    build_root = (build_root or engine_root() / "build").resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "packs").mkdir(parents=True, exist_ok=True)

    key = load_private_key(key_path) if key_path else None
    packs = [
        _pocket_incidents(build_root),
        _information_security(build_root),
        _audit_and_control(build_root),
        _assume_breach(),
        _speak_software(),
        _build_web_guide_ai(),
        _systems_analysis_and_design(),
    ]
    catalog_packs = [_write_pack(out, pack, key) for pack in packs]
    catalog = {
        "format": CATALOG_FORMAT,
        "version": CATALOG_VERSION,
        "updatedAt": _now(),
        "packs": catalog_packs,
    }
    (out / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "README.md").write_text(
        "# Lorekeeper pack store\n\n"
        "Generated by `python3 -m lorekeeper store`. Do not edit by hand.\n\n"
        "The player fetches `catalog.json` and verifies each pack SHA-256 before "
        "import. Packs can contain exercise test code; only install packs you trust.\n",
        encoding="utf-8",
    )
    for extra in out.rglob("._*"):
        extra.unlink()
    return catalog
