"""Course registry: which source repos the engine may read."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    return SLUG_RE.sub("-", value.lower()).strip("-")


@dataclass(frozen=True)
class Unit:
    key: str
    code: str
    slug: str
    title: str
    root: Path
    theme: str = "ink"
    semester: str = ""
    tags: tuple[str, ...] = ()
    level: str = "beginner"
    pitch: str = ""
    start: str = ""
    replacements: dict[str, str] = field(default_factory=dict)


def engine_root() -> Path:
    return Path(__file__).resolve().parents[1]


def registry_dir() -> Path:
    return engine_root() / "courses"


def content_dir() -> Path:
    return engine_root() / "content"


def load_units() -> list[Unit]:
    units: list[Unit] = []
    for path in sorted(registry_dir().glob("*.yaml")):
        if path.name.startswith("._") or path.name.startswith("."):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw_root = Path(data["root"])
        root = raw_root if raw_root.is_absolute() else (path.parent / raw_root)
        raw_replacements = data.get("replacements") or {}
        if not isinstance(raw_replacements, dict):
            raise ValueError(f"{path}: replacements must be a mapping")
        title = str(data.get("title", ""))
        key = data.get("key", path.stem)
        units.append(
            Unit(
                key=key,
                code=data.get("code", path.stem.upper()),
                slug=str(data.get("slug") or slugify(title) or key),
                title=title,
                root=root.resolve(),
                theme=str(data.get("theme", "ink")),
                semester=str(data.get("semester", "")),
                tags=tuple(str(tag) for tag in (data.get("tags") or [])),
                level=str(data.get("level", "beginner")),
                pitch=str(data.get("pitch", "")),
                start=str(data.get("start", "")),
                replacements={
                    str(old): str(new) for old, new in raw_replacements.items()
                },
            )
        )
    return units


def get_unit(key: str) -> Unit:
    wanted = key.lower()
    for unit in load_units():
        if wanted in (unit.key.lower(), unit.code.lower(), unit.slug.lower()):
            return unit
    known = ", ".join(u.code for u in load_units()) or "none"
    raise KeyError(f"unknown unit '{key}' (known: {known})")
