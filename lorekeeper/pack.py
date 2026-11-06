"""Build a portable Lorekeeper pack from a compiled course."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .compile import compile_unit
from .registry import Unit, engine_root, slugify

PACK_FORMAT = "lorekeeper.pack"
PACK_VERSION = 1


def unit_from_root(
    root: Path,
    *,
    unit_id: str | None = None,
    title: str | None = None,
    theme: str = "pixel",
    tags: list[str] | None = None,
    level: str = "beginner",
    pitch: str = "",
    start: str = "01-01",
) -> Unit:
    root = Path(root).expanduser().resolve()
    variables = {}
    variables_path = root / "_variables.yml"
    if variables_path.is_file():
        loaded = yaml.safe_load(variables_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            variables = loaded
    code = str(variables.get("course-code") or root.name.upper())
    name = title or str(variables.get("course-name") or root.name)
    return Unit(
        key=root.name,
        code=code,
        slug=unit_id or slugify(name),
        title=name,
        root=root,
        theme=theme,
        tags=tuple(tags or []),
        level=level,
        pitch=pitch,
        start=start,
        replacements={code: "this course"},
    )


def build_pack(unit: Unit, build_root: Path | None = None) -> dict:
    root = (build_root or engine_root() / "build").resolve()
    course = compile_unit(unit, root)
    course_dir = root / unit.slug
    stories: dict[str, dict] = {}

    for module in course["modules"]:
        for lesson in module["lessons"]:
            for block in lesson["blocks"]:
                if block.get("type") != "story":
                    continue
                src = str(block.get("src", ""))
                if not src:
                    continue
                path = (course_dir / src).resolve()
                if not path.is_file():
                    raise FileNotFoundError(f"story not found: {path}")
                stories[src] = json.loads(path.read_text(encoding="utf-8"))

    return {
        "format": PACK_FORMAT,
        "version": PACK_VERSION,
        "id": unit.slug,
        "title": unit.title,
        "author": "",
        "licence": "",
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "courses": [
            {
                "slug": unit.slug,
                "title": unit.title,
                "theme": unit.theme,
                "level": unit.level,
                "tags": list(unit.tags),
                "pitch": unit.pitch,
                "start": unit.start,
                "course": course,
                "stories": stories,
            }
        ],
    }


def write_pack(pack: dict, out: Path) -> Path:
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out
