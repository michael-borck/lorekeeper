"""Local authoring studio for Lorekeeper overlays.

The studio is a small HTTP service plus a static browser UI. It edits the same
YAML overlays the compiler reads, validates them with the same lesson
normalisers, and builds the real player for preview.

Run it with:

    python3 -m lorekeeper studio
"""

from __future__ import annotations

import errno
import json
import os
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

from .compile import _lesson_from_spec, compile_unit
from .discover import discover_modules
from .registry import Unit, content_dir, engine_root, get_unit, load_units
from .validate import check_unit
from .widgets import WIDGET_KINDS

MAX_BODY_BYTES = 2 * 1024 * 1024

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
            }
        )
    return StudioValidation(problems, summaries)


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
    validation = validate_overlay(unit, module, text)
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

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/studio/"):
            self._handle_api("GET")
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

        if method == "POST" and parts == ["validate"]:
            body = self._read_json()
            unit = _unit(str(body.get("course", "")))
            module = _module(unit, str(body.get("module", "")))
            validation = validate_overlay(unit, module, str(body.get("yaml", "")))
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
