"""Build a Lorekeeper pack from a Quarto book project."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .compile import XP
from .parse import clean_markdown, render_markdown, split_frontmatter, split_sections
from .registry import engine_root, slugify
from .widgets import normalise_question, normalise_widget

PART_PREFIX = re.compile(r"^Part\s+[IVXLC0-9]+\s*[·:.-]\s*", re.IGNORECASE)
H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
ANCHOR = re.compile(r"\s*\{#[^}]+\}\s*$")
IMAGE_BLOCK = re.compile(r"!\[[^\]]*\]\([^)]+\)\{[^}]*\}")
IMAGE_PLAIN = re.compile(r"!\[[^\]]*\]\([^)]+\)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _strip_images(text: str) -> str:
    return IMAGE_PLAIN.sub("", IMAGE_BLOCK.sub("", text))


def _title_of(markdown: str, fallback: str) -> tuple[str, str]:
    match = H1.search(markdown)
    if not match:
        return fallback, markdown
    title = ANCHOR.sub("", match.group(1)).strip()
    body = markdown[: match.start()] + markdown[match.end() :]
    return title, body


def chapter_blocks(path: Path) -> tuple[str, list[dict]]:
    _, raw = split_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
    markdown = _strip_images(raw)
    title, body = _title_of(markdown, path.stem)
    body = clean_markdown(body)
    blocks: list[dict] = []
    first_section = re.search(r"^##\s+", body, re.MULTILINE)
    if first_section:
        intro = body[: first_section.start()].strip()
        body = body[first_section.start() :]
        if intro:
            blocks.append({"type": "html", "html": render_markdown(intro)})
    for section in split_sections(body):
        if section["heading"]:
            blocks.append(
                {
                    "type": "html",
                    "html": f"<h2>{html.escape(section['heading'])}</h2>",
                }
            )
        rendered = render_markdown(section["body"])
        if rendered.strip():
            blocks.append({"type": "html", "html": rendered})
    return ANCHOR.sub("", title).strip(), blocks


def _part_title(value: str) -> str:
    return PART_PREFIX.sub("", value).strip() or value


def _selected_parts(parts: list, spec: str | None) -> list[tuple[int, dict]]:
    numbered = []
    part_number = 0
    for part in parts:
        if isinstance(part, dict) and part.get("part"):
            part_number += 1
            numbered.append((part_number, part))
    if not spec:
        return numbered
    wanted: set[int] = set()
    for token in str(spec).replace(" ", "").split(","):
        if not token:
            continue
        if "-" in token:
            start, end = token.split("-", 1)
            wanted.update(range(int(start), int(end) + 1))
        else:
            wanted.add(int(token))
    return [(index, part) for index, part in numbered if index in wanted]


def _overlay_lessons(unit_id: str, part_number: int) -> list[dict]:
    path = engine_root() / "books" / unit_id / f"part-{part_number}.yml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping")
    return list(data.get("lessons") or [])


def _extra_lesson(unit_id: str, part_number: int, spec: dict, index: int) -> dict:
    kind = str(spec.get("kind", "checkpoint"))
    lesson_id = str(spec.get("id") or f"{part_number:02d}-{index:02d}")
    title = str(spec.get("title") or lesson_id)
    lesson = {
        "id": lesson_id,
        "title": title,
        "kind": kind,
        "xp": int(spec.get("xp") or XP.get(kind, 10)),
        "blocks": [],
    }
    if kind == "checkpoint":
        questions = [
            normalise_question(question, position)
            for position, question in enumerate(spec.get("questions") or [])
        ]
        if not questions:
            raise ValueError(f"{unit_id} part {part_number}: checkpoint has no questions")
        lesson["blocks"].append({"type": "checkpoint", "questions": questions})
    elif kind in {"scenario", "calibration", "viva", "order", "fill", "review", "api", "sql", "terminal"}:
        lesson["blocks"].extend(normalise_widget(kind, spec, lesson_id))
    else:
        raise ValueError(f"{unit_id} part {part_number}: unsupported overlay kind {kind}")
    return lesson


def build_book_pack(
    root: Path,
    *,
    unit_id: str | None = None,
    title: str | None = None,
    theme: str = "storybook",
    tags: list[str] | None = None,
    level: str = "beginner",
    pitch: str = "",
    parts: str | None = None,
) -> dict:
    root = Path(root).expanduser().resolve()
    config_path = root / "_quarto.yml"
    if not config_path.is_file():
        raise FileNotFoundError(f"not a Quarto book: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    book = config.get("book") or {}
    book_title = str(book.get("title") or root.name)
    subtitle = str(book.get("subtitle") or "")
    display_title = title or (f"{book_title}: {subtitle}" if subtitle else book_title)
    unit_id = unit_id or slugify(book_title)
    if not display_title.strip():
        display_title = unit_id
    book_parts = _selected_parts(list(book.get("chapters") or []), parts)
    if not book_parts:
        raise ValueError(f"{unit_id}: no matching book parts")

    modules = []
    for module_number, part in book_parts:
        module_title = _part_title(str(part["part"]))
        lessons = []
        chapter_paths = list(part.get("chapters") or [])
        for chapter_index, chapter in enumerate(chapter_paths, start=1):
            chapter_path = (root / str(chapter)).resolve()
            if not chapter_path.is_file():
                raise FileNotFoundError(f"chapter not found: {chapter_path}")
            chapter_title, blocks = chapter_blocks(chapter_path)
            lessons.append(
                {
                    "id": f"{module_number:02d}-{chapter_index:02d}",
                    "title": chapter_title,
                    "kind": "reading",
                    "xp": XP["reading"],
                    "blocks": blocks,
                }
            )
        for extra_index, spec in enumerate(_overlay_lessons(unit_id, module_number), start=len(lessons) + 1):
            lessons.append(_extra_lesson(unit_id, module_number, spec, extra_index))
        modules.append(
            {
                "number": module_number,
                "slug": slugify(module_title),
                "title": module_title,
                "lessons": lessons,
            }
        )

    start = modules[0]["lessons"][0]["id"] if modules and modules[0]["lessons"] else "01-01"
    course = {
        "schema": 1,
        "generated_at": _now(),
        "unit": {
            "slug": unit_id,
            "title": display_title,
            "theme": theme,
            "tags": list(tags or []),
            "level": level,
            "pitch": pitch or subtitle,
            "start": start,
        },
        "modules": modules,
    }
    return {
        "format": "lorekeeper.pack",
        "version": 1,
        "id": unit_id,
        "title": display_title,
        "author": str(book.get("author") or ""),
        "licence": str(book.get("license") or ""),
        "createdAt": _now(),
        "courses": [
            {
                "slug": unit_id,
                "title": display_title,
                "theme": theme,
                "level": level,
                "tags": list(tags or []),
                "pitch": pitch or subtitle,
                "start": start,
                "course": course,
                "stories": {},
            }
        ],
    }
