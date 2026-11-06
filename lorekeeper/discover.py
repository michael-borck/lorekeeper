"""Read-only discovery of modules inside a unit repo."""

from __future__ import annotations

import re
from pathlib import Path

from .parse import read_frontmatter
from .registry import Unit

MODULE_DIR_RE = re.compile(r"^(\d+)-(.+)$")
TITLE_PREFIX_RE = re.compile(r"^Module\s+\d+\s*:\s*", re.IGNORECASE)


def module_title(module_dir: Path, fallback: str) -> str:
    overview = module_dir / "overview.qmd"
    if not overview.is_file():
        return fallback
    meta, _ = read_frontmatter(overview)
    title = str(meta.get("title", "")).strip()
    return TITLE_PREFIX_RE.sub("", title) or fallback


def discover_modules(unit: Unit) -> list[dict]:
    modules_dir = unit.root / "modules"
    if not modules_dir.is_dir():
        raise FileNotFoundError(f"{unit.code}: no modules/ directory at {modules_dir}")

    modules: list[dict] = []
    for path in sorted(modules_dir.iterdir()):
        if not path.is_dir() or path.name.startswith(("_", ".")):
            continue
        match = MODULE_DIR_RE.match(path.name)
        if not match:
            continue
        number = int(match.group(1))
        slug = path.name
        modules.append(
            {
                "number": number,
                "slug": slug,
                "title": module_title(path, match.group(2).replace("-", " ").title()),
                "dir": path,
            }
        )
    return modules
