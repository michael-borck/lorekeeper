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
    assert result.lessons == [
        {"id": "01-01", "title": "Put the steps in order", "kind": "order", "xp": 20}
    ]


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
