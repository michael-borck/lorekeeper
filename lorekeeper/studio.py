"""Local authoring studio for Lorekeeper overlays.

The studio is a small HTTP service plus a static browser UI. It edits the same
YAML overlays the compiler reads, validates them with the same lesson
normalisers, and builds the real player for preview.

Run it with:

    python3 -m lorekeeper studio
"""

from __future__ import annotations

import base64
import copy
import errno
import json
import mimetypes
import os
import re
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from .compile import _default_specs, _lesson_from_spec, compile_unit, load_overlay
from .discover import discover_modules
from .pack import build_pack, collect_assets, write_pack
from .registry import Unit, content_dir, engine_root, get_unit, load_units, slugify
from .validate import check_unit
from .widgets import WIDGET_KINDS

MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_ASSET_BYTES = 4 * 1024 * 1024
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SAFE_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

LESSON_KINDS = ["reading", "checkpoint", "exercise", "story", *sorted(WIDGET_KINDS)]

LESSON_TEMPLATES: dict[str, str] = {
    "reading": """- id: 01-01
  kind: reading
  title: New reading
  source: overview.qmd
  include:
    - Learning objectives
""",
    "checkpoint": """- id: 01-02
  kind: checkpoint
  title: "Checkpoint: new checkpoint"
  questions:
    - prompt: What is the key idea?
      options:
        - The right answer
        - A plausible wrong answer
      answer: 0
      explanation: Explain why the answer is right.
""",
    "exercise": """- id: 01-03
  kind: exercise
  title: Build something
  language: html
  prompt: |
    Describe the task in one or two sentences.
  starter: |
    <!doctype html>
    <html lang="en"><body></body></html>
  tests:
    - name: Has a heading
      script: |
        assert(doc.querySelector('h1'), 'Add an h1.')
  hints:
    - Start with the smallest change that makes the test pass.
""",
    "order": """- id: 01-04
  kind: order
  title: Put the steps in order
  prompt: |
    Put these steps in a safe order.
  items:
    - First step
    - Second step
    - Third step
  explanation: |
    Explain the order and why it matters.
""",
    "fill": """- id: 01-05
  kind: fill
  title: Complete the passage
  prompt: |
    Fill the blanks.
  passage: |
    The host port comes first: [[1]]:80
  blanks:
    - answers:
        - "8080"
      hint: Use the host port from the example.
""",
    "hotspot": """- id: 01-06
  kind: hotspot
  title: Find the targets
  prompt: |
    Click the thing that should not be public.
  markup: |
    <div class="hotspot-board">
      <button type="button" data-spot="safe">Public menu</button>
      <button type="button" data-spot="bad">Old admin account</button>
    </div>
  targets:
    - selector: "[data-spot=bad]"
      label: Old administrator account
      feedback: Remove the unowned administrator.
""",
    "review": """- id: 01-07
  kind: review
  title: Which line weakened the check?
  prompt: |
    Click the line that hid the problem instead of fixing it.
  lines:
    - code: "expect(page).toHaveTitle('Home');"
      kind: context
    - code: "// removed so the test passes"
      kind: add
      bad: true
      feedback: A comment cannot fix a broken page.
    - code: "});"
      kind: context
  explanation: |
    The check was weakened. Fix the page instead.
""",
    "scenario": """- id: 01-08
  kind: scenario
  title: Choose a path
  prompt: |
    Make a decision and explain the trade-off.
  options:
    - id: a
      label: The cautious path
      outcome: It costs more now and less later.
      effects:
        Build cost: Higher
        Lock-in: Low
      recommended: true
      feedback: This protects the exit cost.
    - id: b
      label: The cheap path
      outcome: It is fast now and expensive to leave.
      effects:
        Build cost: Lower
        Lock-in: High
      feedback: Cheap to build, expensive to leave.
  debrief: |
    Name the trade-off, not just the price.
""",
    "calibration": """- id: 01-09
  kind: calibration
  title: Which answer is stronger?
  prompt: |
    Choose the stronger answer and explain why.
  a:
    title: Answer A
    body: |
      A vague answer with no priorities.
  b:
    title: Answer B
    body: |
      A specific answer with a priority and a trade-off.
  better: b
  rationale: |
    Answer B chooses, prioritises, and names the trade-off.
""",
    "viva": """- id: 01-10
  kind: viva
  title: Mock viva
  context: |
    The examiner is non-technical but has read your proposal.
  questions:
    - prompt: Why did you choose this approach?
      strong_answer: |
        A strong answer names the priority, the trade-off, and the evidence.
      signals:
        - label: Names the priority
          pattern: "priority|first|main"
        - label: Names the trade-off
          pattern: "trade|cost|risk|later"
  rubric:
    - The reasoning holds up under challenge.
    - Trade-offs are named.
""",
    "api": """- id: 01-11
  kind: api
  title: Inspect the endpoints
  prompt: |
    Send each request and read the response.
  endpoints:
    - id: users
      method: GET
      path: /api/users
      status: 200
      body:
        - id: 1
          name: maria
          roles: [administrator]
  questions:
    - prompt: Which endpoint exposes too much?
      options:
        - /api/users
        - /api/menu
      answer: 0
      explanation: It exposes account names and roles.
""",
    "sql": """- id: 01-12
  kind: sql
  title: Write a query
  prompt: |
    Return the three most recent bookings.
  task: |
    Write a query that returns the three most recent bookings.
  schema: |
    CREATE TABLE bookings (id INTEGER, created_at TEXT);
  seed: |
    INSERT INTO bookings VALUES (1, '2026-01-01'), (2, '2026-01-02');
  solution: |
    SELECT * FROM bookings ORDER BY created_at DESC LIMIT 3;
""",
    "story": """- id: 01-14
  kind: story
  title: Play the client meeting
  story: stories/your-story.json
  intro: |
    Set the scene in one or two sentences.
  debrief: |
    Ask what the player noticed or would do differently.
""",
    "terminal": """- id: 01-13
  kind: terminal
  title: Diagnose the service
  prompt: |
    Use the terminal to find why the service is down.
  host: operator@workbench
  cwd: ~
  goals:
    - id: inspect
      label: Inspect the running containers
  commands:
    - pattern: "^docker ps$"
      output: |
        CONTAINER ID   IMAGE     STATUS
        1a2b3c4d       nginx     Exited (1)
      completes:
        - inspect
  help: |
    Start with docker ps.
""",
}


@dataclass
class StudioValidation:
    problems: list[str]
    lessons: list[dict[str, Any]]


class StudioError(Exception):
    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _unit(key: str) -> Unit:
    try:
        return get_unit(key)
    except KeyError as exc:
        raise StudioError(str(exc), HTTPStatus.NOT_FOUND) from exc


def _module(unit: Unit, slug: str) -> dict[str, Any]:
    for module in discover_modules(unit):
        if module["slug"] == slug:
            return module
    raise StudioError(
        f"unknown module '{slug}' in {unit.key}", HTTPStatus.NOT_FOUND
    )


def overlay_path(
    unit: Unit, module: dict[str, Any], content_root: Path | None = None
) -> Path:
    root = (content_root or content_dir()).resolve()
    path = (root / unit.key / "modules" / module["slug"] / "lessons.yml").resolve()
    if not path.is_relative_to(root):
        raise StudioError("overlay path escaped the content directory")
    return path


def parse_lessons(text: str) -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise StudioError(f"YAML error: {exc}") from exc
    if not isinstance(data, dict):
        raise StudioError("top level must be a mapping")
    lessons = data.get("lessons")
    if not isinstance(lessons, list):
        raise StudioError("top level needs a 'lessons' list")
    for index, lesson in enumerate(lessons, start=1):
        if not isinstance(lesson, dict):
            raise StudioError(f"lesson {index} must be a mapping")
    return lessons


def validate_overlay(unit: Unit, module: dict[str, Any], text: str) -> StudioValidation:
    problems: list[str] = []
    summaries: list[dict[str, Any]] = []
    try:
        lessons = parse_lessons(text)
    except StudioError as exc:
        return StudioValidation([str(exc)], [])

    seen: set[str] = set()
    for index, spec in enumerate(lessons, start=1):
        fallback = f"{module['number']:02d}-{index:02d}"
        try:
            lesson = _lesson_from_spec(unit, module, spec, fallback)
        except (ValueError, FileNotFoundError) as exc:
            problems.append(str(exc))
            continue
        lesson_id = str(lesson.get("id", fallback))
        if lesson_id in seen:
            problems.append(f"duplicate lesson id {lesson_id}")
        seen.add(lesson_id)
        summaries.append(
            {
                "id": lesson_id,
                "title": lesson.get("title", fallback),
                "kind": lesson.get("kind", "reading"),
                "xp": lesson.get("xp", 0),
                "spec": spec,
            }
        )
    return StudioValidation(problems, summaries)


def _module_specs(
    unit: Unit, module: dict[str, Any], override_text: str | None = None
) -> list[dict[str, Any]]:
    if override_text is not None:
        return parse_lessons(override_text)
    overlay = load_overlay(unit, module["slug"]) or {}
    specs = overlay.get("lessons")
    return specs if isinstance(specs, list) else _default_specs(module)


def _course_lesson_ids(
    unit: Unit, target: dict[str, Any], override_text: str | None = None
) -> list[tuple[str, str]]:
    ids: list[tuple[str, str]] = []
    try:
        modules = discover_modules(unit)
    except FileNotFoundError:
        return ids
    for module in modules:
        try:
            specs = _module_specs(
                unit, module, override_text if module["slug"] == target["slug"] else None
            )
        except (StudioError, OSError, ValueError):
            continue
        for index, spec in enumerate(specs, start=1):
            fallback = f"{module['number']:02d}-{index:02d}"
            try:
                lesson = _lesson_from_spec(unit, module, spec, fallback)
            except (ValueError, FileNotFoundError):
                continue
            ids.append((str(lesson.get("id", fallback)), module["slug"]))
    return ids


def validate_course_overlay(
    unit: Unit, module: dict[str, Any], text: str
) -> StudioValidation:
    validation = validate_overlay(unit, module, text)
    seen: dict[str, str] = {}
    for lesson_id, module_slug in _course_lesson_ids(unit, module, text):
        if lesson_id in seen and seen[lesson_id] != module_slug:
            validation.problems.append(
                f"duplicate lesson id {lesson_id} in modules {seen[lesson_id]} and {module_slug}"
            )
        else:
            seen.setdefault(lesson_id, module_slug)
    return validation


def load_module(unit: Unit, module: dict[str, Any]) -> dict[str, Any]:
    path = overlay_path(unit, module)
    if not path.is_file():
        return {
            "course": unit.key,
            "module": module["slug"],
            "title": module["title"],
            "path": _display_path(path),
            "exists": False,
            "yaml": "",
            "lessons": [],
            "problems": [],
        }
    text = path.read_text(encoding="utf-8")
    validation = validate_overlay(unit, module, text)
    return {
        "course": unit.key,
        "module": module["slug"],
        "title": module["title"],
        "path": _display_path(path),
        "exists": True,
        "yaml": text,
        "lessons": validation.lessons,
        "problems": validation.problems,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(engine_root()))
    except ValueError:
        return str(path)


def _backup_path(
    unit: Unit, module: dict[str, Any], backup_root: Path | None = None
) -> Path:
    root = (backup_root or (engine_root() / "build" / "studio-backups")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{_now_stamp()}-{unit.key}-{module['slug']}.yml"


def save_overlay(
    unit: Unit,
    module: dict[str, Any],
    text: str,
    content_root: Path | None = None,
    backup_root: Path | None = None,
) -> dict[str, Any]:
    validation = validate_course_overlay(unit, module, text)
    if validation.problems:
        return {
            "ok": False,
            "problems": validation.problems,
            "lessons": validation.lessons,
        }

    path = overlay_path(unit, module, content_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = ""
    if path.is_file():
        backup_path = _backup_path(unit, module, backup_root)
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        backup = _display_path(backup_path)

    temporary = path.with_suffix(".yml.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
    return {
        "ok": True,
        "problems": [],
        "lessons": validation.lessons,
        "path": _display_path(path),
        "backup": backup,
    }


def _yaml_lessons(lessons: list[dict[str, Any]]) -> str:
    return yaml.safe_dump(
        {"lessons": lessons}, sort_keys=False, allow_unicode=True, width=1000
    )


def next_lesson_id(module: dict[str, Any], lessons: list[dict[str, Any]]) -> str:
    prefix = f"{module['number']:02d}-"
    highest = 0
    for lesson in lessons:
        value = str(lesson.get("id", ""))
        if not value.startswith(prefix):
            continue
        try:
            highest = max(highest, int(value[len(prefix) :]))
        except ValueError:
            continue
    return f"{prefix}{highest + 1:02d}"


def transform_overlay(
    unit: Unit,
    module: dict[str, Any],
    text: str,
    action: str,
    index: int,
    target: int | None = None,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lessons = parse_lessons(text)
    if index < 0 or index >= len(lessons):
        raise StudioError("lesson index is out of range")

    if action == "move":
        if target is None:
            raise StudioError("move needs a target index")
        target = max(0, min(int(target), len(lessons) - 1))
        lesson = lessons.pop(index)
        lessons.insert(target, lesson)
    elif action == "duplicate":
        lesson = copy.deepcopy(lessons[index])
        lesson["id"] = next_lesson_id(module, lessons)
        lesson["title"] = f"{lesson.get('title', 'Lesson')} (copy)"
        lessons.insert(index + 1, lesson)
    elif action == "delete":
        lessons.pop(index)
    elif action == "update":
        if not isinstance(fields, dict):
            raise StudioError("update needs a fields object")
        for key, value in fields.items():
            if key == "id" or not isinstance(key, str):
                continue
            lessons[index][key] = value
    else:
        raise StudioError(f"unknown lesson action '{action}'")

    updated = _yaml_lessons(lessons)
    validation = validate_course_overlay(unit, module, updated)
    return {
        "ok": not validation.problems,
        "yaml": updated,
        "problems": validation.problems,
        "lessons": validation.lessons,
    }


def list_sources(unit: Unit, module: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    root = module["dir"]
    if not root.is_dir():
        return found
    for path in sorted(root.rglob("*.qmd")):
        if any(part.startswith((".", "_")) for part in path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        headings = [
            match.group(1).strip()
            for match in re.finditer(r"^#{1,3}\s+(.+?)\s*$", text, re.MULTILINE)
        ]
        found.append(
            {
                "path": str(path.relative_to(root)),
                "headings": headings[:80],
            }
        )
    return found


def register_course(data: dict[str, Any]) -> dict[str, Any]:
    key = slugify(str(data.get("key") or data.get("title") or ""))
    if not key or not SLUG_RE.fullmatch(key):
        raise StudioError("course key must use lowercase letters, numbers and hyphens")
    title = str(data.get("title") or "").strip()
    if not title:
        raise StudioError("course title is required")
    root_value = str(data.get("root") or "").strip()
    if not root_value:
        raise StudioError("source root is required")
    root = Path(root_value).expanduser().resolve()
    if not root.is_dir():
        raise StudioError(f"source root not found: {root}")
    if not (root / "modules").is_dir():
        raise StudioError(f"source root has no modules directory: {root}")

    path = engine_root() / "courses" / f"{key}.yaml"
    if path.exists():
        raise StudioError(f"course '{key}' is already registered")
    slug = str(data.get("slug") or slugify(title) or key)
    if not SLUG_RE.fullmatch(slug):
        raise StudioError("course slug must use lowercase letters, numbers and hyphens")
    code = str(data.get("code") or key.upper())
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    payload = {
        "key": key,
        "code": code,
        "slug": slug,
        "title": title,
        "root": str(root),
        "theme": str(data.get("theme") or "ink"),
        "tags": [str(tag) for tag in tags],
        "level": str(data.get("level") or "beginner"),
        "pitch": str(data.get("pitch") or ""),
        "start": str(data.get("start") or ""),
        "replacements": {code: "this course"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return {"ok": True, "key": key, "path": _display_path(path)}


def initialise_overlay(unit: Unit, module: dict[str, Any]) -> dict[str, Any]:
    specs = _default_specs(module)
    text = _yaml_lessons(specs)
    result = save_overlay(unit, module, text)
    if result.get("ok"):
        result["yaml"] = text
    return result


def _asset_root(unit: Unit) -> Path:
    root = (content_dir() / unit.key / "assets").resolve()
    content = content_dir().resolve()
    if not root.is_relative_to(content):
        raise StudioError("asset path escaped the content directory")
    return root


def list_assets(unit: Unit) -> list[dict[str, Any]]:
    root = _asset_root(unit)
    if not root.is_dir():
        return []
    return [
        {"name": path.name, "url": f"/content/{unit.key}/assets/{path.name}", "size": path.stat().st_size}
        for path in sorted(root.iterdir())
        if path.is_file() and SAFE_FILE_RE.fullmatch(path.name)
    ]


def save_asset(unit: Unit, data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name") or "").strip()
    if not SAFE_FILE_RE.fullmatch(name):
        raise StudioError("asset name must be a simple file name")
    mime = mimetypes.guess_type(name)[0] or ""
    if not mime.startswith("image/") or mime == "image/svg+xml":
        raise StudioError("only PNG, JPEG, GIF, WebP and AVIF images are allowed")
    raw = str(data.get("data") or "")
    if "," in raw and raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        payload = base64.b64decode(raw, validate=True)
    except ValueError as exc:
        raise StudioError("asset data is not valid base64") from exc
    if len(payload) > MAX_ASSET_BYTES:
        raise StudioError("asset is too large (limit 4 MB)")
    root = _asset_root(unit)
    root.mkdir(parents=True, exist_ok=True)
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise StudioError("asset path escaped the content directory")
    path.write_bytes(payload)
    return {"ok": True, "name": name, "url": f"/content/{unit.key}/assets/{name}", "assets": list_assets(unit)}


def build_studio_pack(unit: Unit, data: dict[str, Any]) -> dict[str, Any]:
    pack_id = str(data.get("id") or unit.slug).strip()
    title = str(data.get("title") or unit.title).strip()
    author = str(data.get("author") or "").strip()
    licence = str(data.get("licence") or "").strip()
    problems = []
    if not SLUG_RE.fullmatch(pack_id):
        problems.append("pack id must use lowercase letters, numbers and hyphens")
    if not title:
        problems.append("pack title is required")
    if not author:
        problems.append("author is required")
    if not licence:
        problems.append("licence is required")
    if problems:
        return {"ok": False, "problems": problems}

    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    pack = build_pack(unit, engine_root() / "build")
    pack["id"] = pack_id
    pack["title"] = title
    pack["author"] = author
    pack["licence"] = licence
    entry = pack["courses"][0]
    entry["title"] = title
    entry["tags"] = [str(tag) for tag in tags]
    entry["level"] = str(data.get("level") or unit.level)
    entry["pitch"] = str(data.get("pitch") or unit.pitch)
    entry["start"] = str(data.get("start") or unit.start)
    entry["assets"] = collect_assets(unit)

    out = (engine_root() / "build" / "studio-packs" / f"{pack_id}.json").resolve()
    build_root = (engine_root() / "build").resolve()
    if not out.is_relative_to(build_root):
        raise StudioError("pack path escaped the build directory")
    write_pack(pack, out)
    return {
        "ok": True,
        "problems": [],
        "path": _display_path(out),
        "url": f"/build/studio-packs/{pack_id}.json",
        "filename": f"{pack_id}.json",
        "size": out.stat().st_size,
    }


def list_courses() -> list[dict[str, Any]]:
    courses = []
    for unit in load_units():
        courses.append(
            {
                "key": unit.key,
                "code": unit.code,
                "slug": unit.slug,
                "title": unit.title,
                "root": str(unit.root),
                "rootExists": unit.root.is_dir(),
                "theme": unit.theme,
                "tags": list(unit.tags),
                "level": unit.level,
                "pitch": unit.pitch,
                "start": unit.start,
            }
        )
    return courses


def list_modules(unit: Unit) -> list[dict[str, Any]]:
    modules = []
    for module in discover_modules(unit):
        path = overlay_path(unit, module)
        count = 0
        if path.is_file():
            try:
                count = len(parse_lessons(path.read_text(encoding="utf-8")))
            except StudioError:
                count = 0
        modules.append(
            {
                "number": module["number"],
                "slug": module["slug"],
                "title": module["title"],
                "hasOverlay": path.is_file(),
                "lessonCount": count,
            }
        )
    return modules


def build_course(unit: Unit) -> dict[str, Any]:
    try:
        course = compile_unit(unit, engine_root() / "build")
    except (ValueError, FileNotFoundError) as exc:
        raise StudioError(f"build failed: {exc}", HTTPStatus.UNPROCESSABLE_ENTITY) from exc
    return {
        "ok": True,
        "course": unit.slug,
        "title": course["unit"]["title"],
        "url": f"/player/?course={unit.slug}",
    }


def check_course(unit: Unit) -> dict[str, Any]:
    problems = check_unit(unit)
    return {"ok": not problems, "problems": problems}


class StudioHandler(SimpleHTTPRequestHandler):
    studio_token = ""
    content_root: Path | None = None

    def __init__(
        self, *args: Any, studio_token: str | None = None, **kwargs: Any
    ):
        if studio_token is not None:
            self.studio_token = studio_token
        super().__init__(*args, directory=str(engine_root()), **kwargs)

    def _static_allowed(self) -> bool:
        path = unquote(urlparse(self.path).path)
        if path.startswith(("/studio/", "/player/", "/build/", "/store/")):
            return True
        return bool(re.fullmatch(r"/content/[a-z0-9][a-z0-9-]*/assets/[A-Za-z0-9][A-Za-z0-9._-]*", path))

    def _not_found(self) -> None:
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        if self.path.startswith("/api/studio/") or not self._static_allowed():
            self._not_found()
            return
        super().do_HEAD()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/studio"):
            query = f"?{parsed.query}" if parsed.query else ""
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", f"/studio/{query}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/api/studio/"):
            self._handle_api("GET")
            return
        if not self._static_allowed():
            self._not_found()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/studio/"):
            self._handle_api("POST")
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        if self.path.startswith("/api/studio/"):
            self._handle_api("PUT")
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def _authorised(self) -> bool:
        token = self.headers.get("X-Studio-Token", "")
        if not token:
            token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return bool(token) and secrets.compare_digest(token, self.studio_token)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_BYTES:
            raise StudioError("request body is too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StudioError(f"invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise StudioError("request body must be a JSON object")
        return data

    def _handle_api(self, method: str) -> None:
        if not self._authorised():
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "bad studio token"})
            return

        path = unquote(urlparse(self.path).path)
        parts = [part for part in path.split("/") if part]
        # /api/studio/...
        parts = parts[2:]
        try:
            self._route(method, parts)
        except StudioError as exc:
            self._json(exc.status, {"ok": False, "error": str(exc)})
        except (KeyError, OSError, ValueError) as exc:
            self._json(
                HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)}
            )

    def _route(self, method: str, parts: list[str]) -> None:
        if method == "GET" and parts == ["courses"]:
            self._json(HTTPStatus.OK, {"ok": True, "courses": list_courses()})
            return

        if method == "POST" and parts == ["courses"]:
            self._json(HTTPStatus.OK, register_course(self._read_json()))
            return

        if method == "GET" and parts == ["templates"]:
            self._json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "kinds": LESSON_KINDS,
                    "templates": LESSON_TEMPLATES,
                },
            )
            return

        if len(parts) == 3 and parts[0] == "courses" and parts[2] == "sources":
            unit = _unit(parts[1])
            module = _module(unit, str(parse_qs(urlparse(self.path).query).get("module", [""])[0]))
            self._json(HTTPStatus.OK, {"ok": True, "sources": list_sources(unit, module)})
            return

        if len(parts) == 3 and parts[0] == "courses" and parts[2] == "assets":
            unit = _unit(parts[1])
            if method == "GET":
                self._json(HTTPStatus.OK, {"ok": True, "assets": list_assets(unit)})
                return
            if method == "POST":
                body = self._read_json()
                body["course"] = unit.key
                self._json(HTTPStatus.OK, save_asset(unit, body))
                return

        if len(parts) >= 3 and parts[0] == "courses" and parts[2] == "modules":
            unit = _unit(parts[1])
            if len(parts) == 3 and method == "GET":
                self._json(HTTPStatus.OK, {"ok": True, "modules": list_modules(unit)})
                return
            if len(parts) == 4 and method == "GET":
                module = _module(unit, parts[3])
                self._json(HTTPStatus.OK, load_module(unit, module))
                return
            if len(parts) == 4 and method == "PUT":
                module = _module(unit, parts[3])
                body = self._read_json()
                text = str(body.get("yaml", ""))
                if not text.strip():
                    raise StudioError("yaml is empty")
                self._json(HTTPStatus.OK, save_overlay(unit, module, text))
                return
            if len(parts) == 4 and method == "POST":
                module = _module(unit, parts[3])
                action = str(self._read_json().get("action", ""))
                if action != "init":
                    raise StudioError("unknown module action")
                self._json(HTTPStatus.OK, initialise_overlay(unit, module))
                return

        if method == "POST" and parts == ["validate"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            module = _module(unit, str(body.get("module", "")))
            validation = validate_course_overlay(unit, module, str(body.get("yaml", "")))
            self._json(
                HTTPStatus.OK,
                {
                    "ok": not validation.problems,
                    "problems": validation.problems,
                    "lessons": validation.lessons,
                },
            )
            return

        if method == "POST" and parts == ["build"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            self._json(HTTPStatus.OK, build_course(unit))
            return

        if method == "POST" and parts == ["check"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            self._json(HTTPStatus.OK, check_course(unit))
            return

        if method == "POST" and parts == ["lessons"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            module = _module(unit, str(body.get("module", "")))
            self._json(
                HTTPStatus.OK,
                transform_overlay(
                    unit,
                    module,
                    str(body.get("yaml", "")),
                    str(body.get("action", "")),
                    int(body.get("index", -1)),
                    int(body["target"]) if body.get("target") is not None else None,
                    body.get("fields") if isinstance(body.get("fields"), dict) else None,
                ),
            )
            return

        if method == "POST" and parts == ["pack"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            self._json(HTTPStatus.OK, build_studio_pack(unit, body))
            return

        raise StudioError("not found", HTTPStatus.NOT_FOUND)


class StudioServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _bind(port: int, handler: type[StudioHandler]) -> StudioServer:
    last: OSError | None = None
    for candidate in range(port, port + 20):
        try:
            return StudioServer(("127.0.0.1", candidate), handler)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            last = exc
    raise OSError(f"no free port in range {port}-{port + 19}") from last


def start_studio(port: int = 8765, open_browser: bool = True) -> int:
    token = secrets.token_urlsafe(24)

    class Handler(StudioHandler):
        pass

    Handler.studio_token = token
    server = _bind(port, Handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/studio/?token={token}"
    print(f"Lorekeeper studio: {url}")
    print("Local only. Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0
