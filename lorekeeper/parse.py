"""Parse Quarto/Markdown sources without modifying them."""

from __future__ import annotations

import html
import re
from pathlib import Path

import markdown as markdown_lib
import yaml

SHORTCODE_RE = re.compile(r"\{\{<.*?>\}\}", re.DOTALL)
CALLOUT_RE = re.compile(r"^\s*:::+.*$", re.MULTILINE)
SECTION_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, parts[2]


def read_frontmatter(path: Path) -> tuple[dict, str]:
    return split_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))


def clean_markdown(text: str) -> str:
    text = SHORTCODE_RE.sub("", text)
    text = CALLOUT_RE.sub("", text)
    return text.strip()


def split_sections(body: str) -> list[dict]:
    """Split a markdown body on level 1 and 2 headings."""
    matches = list(SECTION_RE.finditer(body))
    if not matches:
        return [{"level": 1, "heading": "", "body": body.strip()}] if body.strip() else []

    sections: list[dict] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append(
            {
                "level": len(match.group(1)),
                "heading": match.group(2).strip(),
                "body": body[start:end].strip(),
            }
        )
    return sections


def render_markdown(text: str) -> str:
    return markdown_lib.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )


def blocks_from_source(
    source: Path,
    include: list[str] | None = None,
    heading_level: int = 2,
) -> list[dict]:
    """Turn one source file into html blocks, optionally filtered by heading."""
    if not source.is_file():
        raise FileNotFoundError(f"source not found: {source}")

    _, body = read_frontmatter(source)
    sections = split_sections(clean_markdown(body))

    if include:
        invalid = [item for item in include if not isinstance(item, str)]
        if invalid:
            raise ValueError(
                f"{source}: include entries must be quoted strings (got {invalid})"
            )
        wanted = {item.strip().lower() for item in include}
        found = {section["heading"].lower() for section in sections}
        missing = [item for item in wanted if item not in found]
        if missing:
            raise ValueError(
                f"{source}: heading(s) not found: {', '.join(sorted(missing))}"
            )
        sections = [s for s in sections if s["heading"].lower() in wanted]

    blocks: list[dict] = []
    for section in sections:
        if section["heading"]:
            level = min(max(heading_level, 1), 6)
            heading = html.escape(section["heading"])
            blocks.append({"type": "html", "html": f"<h{level}>{heading}</h{level}>"})
        rendered = render_markdown(section["body"])
        if rendered.strip():
            blocks.append({"type": "html", "html": rendered})
    return blocks
