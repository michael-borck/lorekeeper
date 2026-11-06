"""Lorekeeper command-line interface.

    lorekeeper courses
        list the courses the engine can read

    lorekeeper check [COURSE|all]
        validate overlays without writing anything

    lorekeeper build [COURSE|all] [--out DIR]
        compile course JSON into build/ (default: every registered unit)

    lorekeeper serve [--port 8000] [--no-build]
        build if needed, then serve the player at http://localhost:PORT/player/

    lorekeeper studio [--port 8765]
        open the local authoring studio for course overlays
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__
from .compile import compile_all, compile_unit
from .registry import engine_root, get_unit, load_units
from .validate import check_all, check_unit


def _build_dir(value: str | None) -> Path:
    return Path(value).resolve() if value else engine_root() / "build"


def _cmd_courses(_args: argparse.Namespace) -> int:
    units = load_units()
    if not units:
        print("No courses registered. Add a YAML file under courses/.")
        return 0
    for unit in units:
        print(unit.title)
        print(f"  source: {unit.root}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        units = load_units() if args.unit == "all" else [get_unit(args.unit)]
    except KeyError as exc:
        print(exc, file=sys.stderr)
        return 2

    problems = check_all(units) if args.unit == "all" else check_unit(units[0])
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        return 1
    print(f"✓ {', '.join(unit.title for unit in units)}: no problems")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    out_root = _build_dir(args.out)
    try:
        if args.unit == "all":
            courses = compile_all(out_root)
        else:
            courses = [compile_unit(get_unit(args.unit), out_root)]
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    for course in courses:
        lessons = sum(len(module["lessons"]) for module in course["modules"])
        print(
            f"✓ {course['unit']['title']}: "
            f"{len(course['modules'])} modules, {lessons} lessons "
            f"-> {out_root / course['unit']['slug'] / 'course.json'}"
        )
    return 0


def _cmd_studio(args: argparse.Namespace) -> int:
    from .studio import start_studio

    return start_studio(port=args.port, open_browser=not args.no_open)


def _cmd_serve(args: argparse.Namespace) -> int:
    root = engine_root()
    out_root = _build_dir(args.out)

    if not args.no_build:
        try:
            compile_all(out_root)
        except (ValueError, FileNotFoundError) as exc:
            print(f"✗ build failed: {exc}", file=sys.stderr)
            return 1

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(root)
    )
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/player/"
        print(f"Serving {root}")
        print(f"Lorekeeper: {url}  (Ctrl+C to stop)")
        if not args.no_open:
            threading.Timer(0.6, webbrowser.open, args=(url,)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lorekeeper", description=__doc__)
    parser.add_argument("--version", action="version", version=f"lorekeeper {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    courses = sub.add_parser("courses", help="list registered courses")
    courses.set_defaults(func=_cmd_courses)

    check = sub.add_parser("check", help="validate overlays")
    check.add_argument("unit", nargs="?", default="all")
    check.set_defaults(func=_cmd_check)

    build = sub.add_parser("build", help="compile course JSON")
    build.add_argument("unit", nargs="?", default="all")
    build.add_argument("--out", help="output directory (default: engine build/)")
    build.set_defaults(func=_cmd_build)

    serve = sub.add_parser("serve", help="serve the player locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--out", help="build directory (default: engine build/)")
    serve.add_argument("--no-build", action="store_true", help="skip the rebuild")
    serve.add_argument("--no-open", action="store_true", help="do not open a browser")
    serve.set_defaults(func=_cmd_serve)

    studio = sub.add_parser("studio", help="open the local authoring studio")
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-open", action="store_true", help="do not open a browser")
    studio.set_defaults(func=_cmd_studio)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
