from pathlib import Path

from lorekeeper.registry import Unit, engine_root
from lorekeeper.studio import (
    LESSON_TEMPLATES,
    save_overlay,
    validate_overlay,
)


def unit() -> Unit:
    return Unit(
        key="test-course",
        code="TEST",
        slug="test-course",
        title="Test Course",
        root=engine_root(),
    )


def module() -> dict:
    return {
        "number": 1,
        "slug": "01-test",
        "title": "Test",
        "dir": engine_root(),
    }


def test_valid_order_overlay() -> None:
    text = """lessons:
  - id: 01-01
    kind: order
    title: Put the steps in order
    prompt: Put these in order.
    items:
      - First
      - Second
    explanation: Because order matters.
"""
    result = validate_overlay(unit(), module(), text)
    assert result.problems == []
    assert result.lessons[0]["id"] == "01-01"
    assert result.lessons[0]["title"] == "Put the steps in order"
    assert result.lessons[0]["kind"] == "order"
    assert result.lessons[0]["xp"] == 20
    assert result.lessons[0]["spec"]["items"] == ["First", "Second"]


def test_duplicate_lesson_ids() -> None:
    text = """lessons:
  - id: 01-01
    kind: order
    title: One
    items: [A, B]
    explanation: Why.
  - id: 01-01
    kind: order
    title: Two
    items: [A, B]
    explanation: Why.
"""
    result = validate_overlay(unit(), module(), text)
    assert any("duplicate lesson id 01-01" in problem for problem in result.problems)


def test_invalid_order_reports_problem() -> None:
    text = """lessons:
  - id: 01-01
    kind: order
    title: Too small
    items: [Only one]
    explanation: Why.
"""
    result = validate_overlay(unit(), module(), text)
    assert any("at least two items" in problem for problem in result.problems)


def test_bad_yaml_reports_problem() -> None:
    result = validate_overlay(unit(), module(), "lessons: [\n")
    assert result.problems
    assert "YAML error" in result.problems[0] or "top level" in result.problems[0]


def test_save_overlay_writes_and_backs_up(tmp_path: Path) -> None:
    content_root = tmp_path / "content"
    backup_root = tmp_path / "backups"
    text = """lessons:
  - id: 01-01
    kind: order
    title: Save me
    items: [A, B]
    explanation: Why.
"""
    first = save_overlay(unit(), module(), text, content_root, backup_root)
    assert first["ok"] is True
    path = content_root / "test-course" / "modules" / "01-test" / "lessons.yml"
    assert path.is_file()
    assert path.read_text() == text

    second = save_overlay(unit(), module(), text, content_root, backup_root)
    assert second["ok"] is True
    assert second["backup"]
    assert list(backup_root.glob("*.yml"))


def test_templates_are_yaml_mappings() -> None:
    import yaml

    for kind, template in LESSON_TEMPLATES.items():
        data = yaml.safe_load(f"lessons:\n{template}")
        assert isinstance(data, dict), kind
        assert isinstance(data.get("lessons"), list), kind
        assert data["lessons"][0]["kind"] == kind


def test_course_wide_duplicate_ids_are_reported(tmp_path: Path):
    from lorekeeper.studio import validate_course_overlay

    source = tmp_path / "source"
    for name in ("01-first", "02-second"):
        module = source / "modules" / name
        module.mkdir(parents=True)
        (module / "overview.qmd").write_text(f"# {name}\n\nText.\n", encoding="utf-8")
    test_unit = Unit(
        key="duplicate-course",
        code="DUP",
        slug="duplicate-course",
        title="Duplicate",
        root=source,
    )
    first = {
        "number": 1,
        "slug": "01-first",
        "title": "First",
        "dir": source / "modules" / "01-first",
    }
    text = """lessons:
  - id: 02-01
    kind: order
    title: Clashes with the default second-module id
    items: [A, B]
    explanation: Why.
"""
    result = validate_course_overlay(test_unit, first, text)
    assert any("duplicate lesson id 02-01" in problem for problem in result.problems)


def test_transform_overlay_duplicates_moves_and_deletes():
    from lorekeeper.studio import transform_overlay

    text = """lessons:
  - id: 01-01
    kind: order
    title: One
    items: [A, B]
    explanation: Why.
  - id: 01-02
    kind: order
    title: Two
    items: [A, B]
    explanation: Why.
"""
    duplicated = transform_overlay(unit(), module(), text, "duplicate", 0)
    assert duplicated["ok"] is True
    assert [item["id"] for item in duplicated["lessons"]] == ["01-01", "01-03", "01-02"]

    moved = transform_overlay(unit(), module(), text, "move", 0, 1)
    assert [item["id"] for item in moved["lessons"]] == ["01-02", "01-01"]

    deleted = transform_overlay(unit(), module(), text, "delete", 0)
    assert [item["id"] for item in deleted["lessons"]] == ["01-02"]


def test_register_course_writes_registry_entry(tmp_path: Path, monkeypatch):
    from lorekeeper import studio

    source = tmp_path / "source"
    (source / "modules").mkdir(parents=True)
    monkeypatch.setattr(studio, "engine_root", lambda: tmp_path / "engine")
    result = studio.register_course(
        {
            "title": "New Course",
            "key": "new-course",
            "root": str(source),
            "tags": "one, two",
        }
    )
    path = tmp_path / "engine" / "courses" / "new-course.yaml"
    assert result["ok"] is True
    assert path.is_file()
    assert "title: New Course" in path.read_text()


def test_save_asset_writes_image(tmp_path: Path, monkeypatch):
    from lorekeeper import studio

    monkeypatch.setattr(studio, "content_dir", lambda: tmp_path / "content")
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
    result = studio.save_asset(unit(), {"name": "dot.png", "data": f"data:image/png;base64,{png}"})
    assert result["ok"] is True
    assert (tmp_path / "content" / "test-course" / "assets" / "dot.png").is_file()
    assert result["assets"][0]["name"] == "dot.png"
    assert studio.list_assets(unit())[0]["name"] == "dot.png"
