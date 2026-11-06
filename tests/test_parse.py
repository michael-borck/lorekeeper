import pytest

from lorekeeper.parse import (
    blocks_from_source,
    clean_markdown,
    render_markdown,
    split_frontmatter,
    split_sections,
)


def test_split_frontmatter_reads_title():
    meta, body = split_frontmatter('---\ntitle: "Module 01: Test"\n---\n\n## A\n\nText\n')
    assert meta["title"] == "Module 01: Test"
    assert body.lstrip().startswith("## A")


def test_split_frontmatter_without_header_returns_body():
    meta, body = split_frontmatter("hello\n")
    assert meta == {}
    assert body == "hello\n"


def test_split_sections_uses_level_one_and_two_headings():
    body = "intro\n\n## One\n\nalpha\n\n### Nested\n\nbeta\n\n## Two\n\ngamma\n"
    sections = split_sections(body)
    assert [section["heading"] for section in sections] == ["One", "Two"]
    assert "Nested" in sections[0]["body"]


def test_clean_markdown_strips_shortcodes_and_callout_fences():
    text = "{{< meta course-code >}}\n\n::: {.callout-note}\nBody\n:::\n"
    cleaned = clean_markdown(text)
    assert "{{<" not in cleaned
    assert ":::" not in cleaned
    assert "Body" in cleaned


def test_render_markdown_renders_tables():
    html = render_markdown("| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "<table>" in html
    assert "<td>1</td>" in html


def test_blocks_from_source_rejects_missing_heading(tmp_path):
    source = tmp_path / "lesson.qmd"
    source.write_text("## Known\n\nText\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        blocks_from_source(source, include=["Missing"])
