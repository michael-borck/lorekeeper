from pathlib import Path

from lorekeeper.book import build_book_pack


def make_book(root: Path) -> Path:
    (root / "chapters").mkdir(parents=True)
    (root / "_quarto.yml").write_text(
        """book:
  title: "Test Book"
  subtitle: "A Short Guide"
  author: "Test Author"
  license: "CC BY 4.0 International"
  chapters:
    - index.qmd
    - part: "Part I · Basics"
      chapters:
        - chapters/01-one.qmd
    - part: "Part II · More"
      chapters:
        - chapters/02-two.qmd
""",
        encoding="utf-8",
    )
    (root / "chapters/01-one.qmd").write_text(
        "# One\n\nIntro prose.\n\n## A section\n\nBody with ![alt](../images/x.png){fig-alt=\"x\"}.\n",
        encoding="utf-8",
    )
    (root / "chapters/02-two.qmd").write_text(
        "# Two\n\nSecond chapter.\n", encoding="utf-8"
    )
    return root


def test_book_pack_selects_part_and_strips_images(tmp_path: Path):
    pack = build_book_pack(
        make_book(tmp_path / "book"),
        unit_id="test-book",
        title="Test Book",
        tags=["demo"],
        parts="1",
    )
    assert pack["format"] == "lorekeeper.pack"
    assert pack["id"] == "test-book"
    assert pack["licence"] == "CC BY 4.0 International"
    assert len(pack["courses"][0]["course"]["modules"]) == 1
    module = pack["courses"][0]["course"]["modules"][0]
    assert module["number"] == 1
    assert module["title"] == "Basics"
    assert len(module["lessons"]) == 1
    assert module["lessons"][0]["title"] == "One"
    html = " ".join(
        block.get("html", "")
        for block in module["lessons"][0]["blocks"]
        if block["type"] == "html"
    )
    assert "Intro prose" in html
    assert "A section" in html
    assert "<img" not in html


def test_book_pack_can_select_a_later_part(tmp_path: Path):
    pack = build_book_pack(
        make_book(tmp_path / "book"), unit_id="test-book", parts="2"
    )
    module = pack["courses"][0]["course"]["modules"][0]
    assert module["number"] == 2
    assert pack["courses"][0]["start"] == "02-01"
