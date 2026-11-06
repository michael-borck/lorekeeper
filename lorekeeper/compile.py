"""Compile a unit repo plus engine overlays into a course JSON bundle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .discover import discover_modules
from .parse import blocks_from_source, clean_markdown, read_frontmatter, render_markdown
from .registry import Unit, content_dir, engine_root, slugify

SCHEMA_VERSION = 1
XP = {"reading": 10, "checkpoint": 25, "exercise": 50}


def xp_for(kind: str) -> int:
    return XP.get(kind, 10)


def apply_replacements(value, replacements: dict[str, str]):
    """Apply a course's word replacements to learner-facing values."""
    if not replacements:
        return value
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [apply_replacements(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: apply_replacements(item, replacements)
            for key, item in value.items()
        }
    return value


def overlay_path(unit: Unit, slug: str) -> Path:
    return content_dir() / unit.key / "modules" / slug / "lessons.yml"


def load_overlay(unit: Unit, slug: str) -> dict | None:
    path = overlay_path(unit, slug)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return data


def assert_outside_source(out_dir: Path, source_root: Path) -> None:
    """Refuse to write anything inside a unit repo."""
    out = out_dir.resolve()
    source = source_root.resolve()
    if out == source or out.is_relative_to(source):
        raise ValueError(
            f"refusing to write into the unit repo: {out} is inside {source}"
        )


def _normalise_question(raw: dict, index: int) -> dict:
    prompt = str(raw.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(f"checkpoint question {index} has no prompt")

    options_raw = raw.get("options") or []
    options: list[str] = []
    answer = -1

    for position, option in enumerate(options_raw):
        if isinstance(option, dict):
            options.append(str(option.get("text", "")).strip())
            if option.get("correct"):
                answer = position
        else:
            text = str(option).strip()
            options.append(text)
            if raw.get("correct") is not None and text == str(raw["correct"]).strip():
                answer = position

    if "answer" in raw:
        answer = int(raw["answer"])
    if not options:
        raise ValueError(f"checkpoint question {index} has no options")
    if not 0 <= answer < len(options):
        raise ValueError(f"checkpoint question {index} has no valid answer")

    return {
        "id": str(raw.get("id") or f"q{index + 1}"),
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": str(raw.get("explanation", "")).strip(),
    }


def _normalise_tests(raw_tests: list, lesson_id: str) -> list[dict]:
    tests: list[dict] = []
    for position, test in enumerate(raw_tests or []):
        if isinstance(test, str):
            name, script = f"Test {position + 1}", test
        else:
            name = str(test.get("name") or f"Test {position + 1}")
            script = str(test.get("script", "")).strip()
        if not script:
            raise ValueError(f"{lesson_id}: test '{name}' has no script")
        tests.append({"name": name, "script": script})
    if not tests:
        raise ValueError(f"{lesson_id}: exercise has no tests")
    return tests


def _reading_blocks(unit: Unit, module_dir: Path, spec: dict) -> list[dict]:
    source = str(spec.get("source") or "overview.qmd")
    include = spec.get("include")
    return blocks_from_source(module_dir / source, include=include)


def _lesson_from_spec(unit: Unit, module: dict, spec: dict, fallback_id: str) -> dict:
    kind = str(spec.get("kind", "reading"))
    lesson_id = str(spec.get("id") or fallback_id)
    lesson = {
        "id": lesson_id,
        "title": str(spec.get("title") or fallback_id),
        "kind": kind,
        "xp": int(spec.get("xp") or xp_for(kind)),
        "blocks": [],
    }

    if kind == "reading":
        lesson["blocks"].extend(_reading_blocks(unit, module["dir"], spec))

    elif kind == "checkpoint":
        if spec.get("brief"):
            lesson["blocks"].append(
                {"type": "html", "html": render_markdown(clean_markdown(str(spec["brief"])))}
            )
        questions = [
            _normalise_question(question, index)
            for index, question in enumerate(spec.get("questions") or [])
        ]
        if not questions:
            raise ValueError(f"{lesson_id}: checkpoint has no questions")
        lesson["blocks"].append({"type": "checkpoint", "questions": questions})

    elif kind == "exercise":
        if spec.get("brief"):
            lesson["blocks"].append(
                {"type": "html", "html": render_markdown(clean_markdown(str(spec["brief"])))}
            )
        exercise = {
            "type": "exercise",
            "id": str(spec.get("exercise_id") or f"{lesson_id}-exercise"),
            "language": str(spec.get("language", "html")),
            "prompt": render_markdown(clean_markdown(str(spec.get("prompt", "")))),
            "starter": str(spec.get("starter", "")),
            "tests": _normalise_tests(spec.get("tests"), lesson_id),
            "hints": [str(hint) for hint in spec.get("hints") or []],
        }
        if spec.get("viewport"):
            exercise["viewport"] = {
                "width": int(spec["viewport"].get("width", 375)),
                "height": int(spec["viewport"].get("height", 667)),
            }
        if spec.get("html"):
            exercise["html"] = str(spec["html"])
        if spec.get("mock"):
            exercise["mock"] = spec["mock"]
        lesson["blocks"].append(exercise)

    else:
        raise ValueError(f"{lesson_id}: unknown lesson kind '{kind}'")

    return lesson


def _default_specs(module: dict) -> list[dict]:
    specs: list[dict] = [
        {"kind": "reading", "title": module["title"], "source": "overview.qmd"}
    ]
    activity = module["dir"] / "in-class" / "activity-01.qmd"
    if activity.is_file():
        meta, _ = read_frontmatter(activity)
        specs.append(
            {
                "kind": "reading",
                "title": str(meta.get("title") or "Workshop"),
                "source": "in-class/activity-01.qmd",
            }
        )
    return specs


def compile_unit(unit: Unit, out_root: Path) -> dict:
    out_dir = out_root / unit.slug
    assert_outside_source(out_dir, unit.root)

    modules_out: list[dict] = []
    seen_lessons: set[str] = set()

    for module in discover_modules(unit):
        overlay = load_overlay(unit, module["slug"]) or {}
        specs = overlay.get("lessons") or _default_specs(module)

        lessons = []
        for index, spec in enumerate(specs, start=1):
            fallback = f"{module['number']:02d}-{index:02d}"
            lesson = apply_replacements(
                _lesson_from_spec(unit, module, spec, fallback),
                unit.replacements,
            )
            if lesson["id"] in seen_lessons:
                raise ValueError(f"duplicate lesson id: {lesson['id']}")
            seen_lessons.add(lesson["id"])
            lessons.append(lesson)

        modules_out.append(
            {
                "number": module["number"],
                "slug": slugify(apply_replacements(module["title"], unit.replacements)),
                "title": apply_replacements(module["title"], unit.replacements),
                "lessons": lessons,
            }
        )

    course = {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unit": {
            "slug": unit.slug,
            "title": unit.title,
        },
        "modules": modules_out,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    course_path = out_dir / "course.json"
    course_path.write_text(
        json.dumps(course, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return course


def compile_all(out_root: Path | None = None) -> list[dict]:
    from .registry import load_units

    root = out_root or engine_root() / "build"
    courses = [compile_unit(unit, root) for unit in load_units()]
    index = {
        "schema": SCHEMA_VERSION,
        "courses": [
            {
                "slug": course["unit"]["slug"],
                "title": course["unit"]["title"],
                "url": f"{course['unit']['slug']}/course.json",
                "modules": len(course["modules"]),
                "lessons": sum(len(m["lessons"]) for m in course["modules"]),
            }
            for course in courses
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return courses
