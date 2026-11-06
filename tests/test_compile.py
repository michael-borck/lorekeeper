import hashlib
import json
from pathlib import Path

import pytest

from lorekeeper.compile import assert_outside_source, compile_all, compile_unit
from lorekeeper.registry import get_unit, load_units
from lorekeeper.validate import check_unit
from lorekeeper.widgets import WIDGET_KINDS


def tree_digest(root: Path) -> str:
    """Digest only the source files the compiler is allowed to read."""
    digest = hashlib.sha256()
    for pattern in ("*.qmd", "*.md", "*.yml", "*.yaml"):
        for path in sorted(root.rglob(pattern)):
            if ".git" in path.parts or path.name.startswith("._"):
                continue
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_all_registered_units_have_valid_overlays():
    problems = []
    for unit in load_units():
        problems.extend(check_unit(unit))
    assert problems == []


def test_compile_isys3004_keeps_unit_repo_unchanged(tmp_path):
    unit = get_unit("ISYS3004")
    before = tree_digest(unit.root)

    course = compile_unit(unit, tmp_path)

    assert tree_digest(unit.root) == before
    assert course["unit"]["slug"] == "ship-it"
    assert course["unit"]["title"].startswith("Ship It")
    assert course["unit"]["theme"] == "storybook"
    assert len(course["modules"]) == 12

    lesson_ids = [lesson["id"] for module in course["modules"] for lesson in module["lessons"]]
    assert len(lesson_ids) == len(set(lesson_ids))
    assert "01-01" in lesson_ids
    assert "01-03" in lesson_ids


def test_written_course_json_has_exercise_tests(tmp_path):
    compile_all(tmp_path)
    course_path = tmp_path / "ship-it" / "course.json"
    course = json.loads(course_path.read_text(encoding="utf-8"))

    module_one = course["modules"][0]
    exercise = next(
        block
        for lesson in module_one["lessons"]
        for block in lesson["blocks"]
        if block["type"] == "exercise"
    )
    assert exercise["language"] == "html"
    assert len(exercise["tests"]) >= 4
    assert all(test["script"] for test in exercise["tests"])


def test_checkpoint_answers_are_in_range(tmp_path):
    compile_all(tmp_path)
    course = json.loads((tmp_path / "signal-and-noise" / "course.json").read_text(encoding="utf-8"))
    checkpoints = [
        block
        for module in course["modules"]
        for lesson in module["lessons"]
        for block in lesson["blocks"]
        if block["type"] == "checkpoint"
    ]
    assert checkpoints
    for checkpoint in checkpoints:
        for question in checkpoint["questions"]:
            assert 0 <= question["answer"] < len(question["options"])


def test_refuses_to_write_inside_unit_repo():
    unit = get_unit("ISYS3004")
    with pytest.raises(ValueError):
        assert_outside_source(unit.root / "build", unit.root)


def test_exercise_viewport_is_compiled(tmp_path):
    course = compile_unit(get_unit("ISYS3004"), tmp_path)
    module_two = course["modules"][1]
    exercise = next(
        block
        for lesson in module_two["lessons"]
        for block in lesson["blocks"]
        if block["type"] == "exercise"
    )
    assert exercise["viewport"] == {"width": 375, "height": 667}


def learner_strings(value, skip_keys=None):
    """Yield learner-facing strings, skipping internal provenance fields."""
    skip = skip_keys or {"semester"}
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from learner_strings(item, skip)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in skip:
                continue
            yield from learner_strings(item, skip)


def test_learner_facing_content_is_unbranded(tmp_path):
    compile_all(tmp_path)
    for path in sorted(tmp_path.glob("*/course.json")):
        course = json.loads(path.read_text(encoding="utf-8"))
        for text in learner_strings(course):
            assert "ISYS" not in text.upper(), text[:160]
            assert "Curtin" not in text, text[:160]


def test_course_titles_and_slugs_are_thematic():
    courses = {unit.code: unit for unit in load_units()}
    assert courses["ISYS3004"].title.startswith("Ship It")
    assert courses["ISYS3004"].slug == "ship-it"
    assert courses["ISYS3004"].theme == "storybook"
    assert courses["ISYS2008"].title.startswith("Signal & Noise")
    assert courses["ISYS2008"].slug == "signal-and-noise"
    assert courses["ISYS2008"].theme == "pixel"


def test_course_code_replacements_apply_to_titles(tmp_path):
    course = compile_unit(get_unit("ISYS2008"), tmp_path)
    module_twelve = course["modules"][-1]
    assert "ISYS" not in module_twelve["title"]
    assert "the next course" in module_twelve["title"]


def test_index_is_unbranded(tmp_path):
    compile_all(tmp_path)
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    for text in learner_strings(index):
        assert "ISYS" not in text.upper(), text
        assert "Curtin" not in text, text


def test_field_kit_contains_every_widget(tmp_path):
    course = compile_unit(get_unit("DEMO"), tmp_path)
    kinds = {
        lesson["kind"]
        for module in course["modules"]
        for lesson in module["lessons"]
    }
    assert WIDGET_KINDS <= kinds


def test_sql_engine_is_vendored():
    root = Path(__file__).resolve().parents[1]
    assert (root / "player" / "vendor" / "sql-wasm.js").is_file()
    assert (root / "player" / "vendor" / "sql-wasm.wasm").is_file()


def test_story_is_copied_into_the_build(tmp_path):
    course = compile_unit(get_unit("ISYS3004"), tmp_path)
    story = next(
        block
        for module in course["modules"]
        for lesson in module["lessons"]
        for block in lesson["blocks"]
        if block["type"] == "story"
    )
    assert story["src"] == "stories/client-engagement.json"
    assert (tmp_path / "ship-it" / story["src"]).is_file()


def test_index_includes_course_themes(tmp_path):
    compile_all(tmp_path)
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    themes = {course["slug"]: course["theme"] for course in index["courses"]}
    assert themes["ship-it"] == "storybook"
    assert themes["signal-and-noise"] == "pixel"
    assert themes["field-kit"] == "pixel"


def test_every_story_is_copied_into_its_course_build(tmp_path):
    compile_all(tmp_path)
    for path in sorted(tmp_path.glob("*/course.json")):
        course = json.loads(path.read_text(encoding="utf-8"))
        slug = course["unit"]["slug"]
        for module in course["modules"]:
            for lesson in module["lessons"]:
                for block in lesson["blocks"]:
                    if block["type"] == "story":
                        assert (tmp_path / slug / block["src"]).is_file(), block["src"]
