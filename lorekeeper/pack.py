"""Build a portable Lorekeeper pack from a compiled course."""

from __future__ import annotations

import base64
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .compile import compile_unit
from .registry import Unit, content_dir, engine_root, slugify

PACK_FORMAT = "lorekeeper.pack"
PACK_VERSION = 1
MAX_ASSET_BYTES = 4 * 1024 * 1024


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


def collect_assets(unit: Unit) -> dict[str, str]:
    root = (content_dir() / unit.key / "assets").resolve()
    assets: dict[str, str] = {}
    if not root.is_dir():
        return assets
    for path in sorted(root.iterdir()):
        if not path.is_file() or not path.name[0].isalnum():
            continue
        if not all(char.isalnum() or char in "._-" for char in path.name):
            continue
        mime = mimetypes.guess_type(path.name)[0] or ""
        if not mime.startswith("image/") or mime == "image/svg+xml":
            continue
        data = path.read_bytes()
        if len(data) > MAX_ASSET_BYTES:
            continue
        assets[path.name] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return assets


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
                "assets": collect_assets(unit),
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
