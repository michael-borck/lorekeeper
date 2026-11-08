"""Authoring checks. Run before a build to catch broken overlays early."""

from __future__ import annotations

from .compile import _default_specs, _lesson_from_spec, load_overlay
from .discover import discover_modules
from .registry import Unit, content_dir


def check_unit(unit: Unit) -> list[str]:
    problems: list[str] = []
    if not unit.root.is_dir():
        return [f"{unit.code}: unit root not found: {unit.root}"]

    try:
        modules = discover_modules(unit)
    except FileNotFoundError as exc:
        return [str(exc)]

    known_slugs = {module["slug"] for module in modules}

    from .narrators import check_narrator

    try:
        check_narrator(unit.narrator, unit.code)
    except ValueError as exc:
        problems.append(str(exc))

    for module in modules:
        overlay = load_overlay(unit, module["slug"])
        specs = (overlay or {}).get("lessons") or _default_specs(module)
        seen: set[str] = set()
        for index, spec in enumerate(specs, start=1):
            fallback = f"{module['number']:02d}-{index:02d}"
            try:
                lesson = _lesson_from_spec(unit, module, spec, fallback)
            except (ValueError, FileNotFoundError) as exc:
                problems.append(f"{module['slug']}: {exc}")
                continue
            if lesson["id"] in seen:
                problems.append(f"{module['slug']}: duplicate lesson id {lesson['id']}")
            seen.add(lesson["id"])

    overlay_root = content_dir() / unit.key / "modules"
    if overlay_root.is_dir():
        for path in sorted(overlay_root.iterdir()):
            if path.is_dir() and path.name not in known_slugs:
                problems.append(
                    f"{unit.code}: overlay for unknown module '{path.name}' "
                    f"({path.relative_to(content_dir().parent)})"
                )

    return problems


def check_all(units: list[Unit]) -> list[str]:
    problems: list[str] = []
    for unit in units:
        problems.extend(check_unit(unit))
    return problems
