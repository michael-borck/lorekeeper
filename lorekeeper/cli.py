"""Lorekeeper command-line interface.

    lorekeeper courses
        list the courses the engine can read

    lorekeeper check [COURSE|all]
        validate overlays without writing anything

    lorekeeper build [COURSE|all] [--out DIR]
        compile course JSON into build/ (default: every registered unit)

    lorekeeper serve [--port 8000] [--no-build]
        build if needed, then serve the player at http://localhost:PORT/player/

    lorekeeper site [--out _site] [--cname DOMAIN]
        assemble a static site for GitHub Pages or another static host

    lorekeeper pack COURSE [--out FILE]
        build a portable pack from a compiled course

    lorekeeper pack --root DIR --id SLUG --title TITLE
        build a pack straight from a unit folder, without registering it

    lorekeeper pack-book BOOK_ROOT [--id SLUG] [--part 1]
        build a pack from a Quarto book, with optional part overlays

    lorekeeper store [--out DIR] [--key FILE]
        build the static pack catalogue and sample pack

    lorekeeper keygen [--private FILE] [--public FILE] [--trusted FILE]
        create an Ed25519 signing key

    lorekeeper verify-store [--store DIR] [--trusted FILE]
        verify the catalogue hashes and signatures with public keys

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


def _cmd_store(args: argparse.Namespace) -> int:
    from .store import build_store

    out = Path(args.out).resolve() if args.out else engine_root() / "store"
    key = Path(args.key).expanduser() if args.key else None
    try:
        catalog = build_store(out, key_path=key)
    except (ValueError, OSError, KeyError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ pack store: {out} ({len(catalog['packs'])} pack)")
    return 0


def _cmd_verify_store(args: argparse.Namespace) -> int:
    from .verify import verify_store

    store = Path(args.store).resolve() if args.store else engine_root() / "store"
    trusted = Path(args.trusted) if args.trusted else engine_root() / "player" / "trusted-keys.js"
    problems = verify_store(store, trusted)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        return 1
    print("✓ pack store: hashes and signatures verified")
    return 0


def _cmd_keygen(args: argparse.Namespace) -> int:
    from .signing import DEFAULT_PRIVATE, DEFAULT_PUBLIC, keygen

    private = Path(args.private).expanduser() if args.private else DEFAULT_PRIVATE
    public = Path(args.public).expanduser() if args.public else DEFAULT_PUBLIC
    trusted = Path(args.trusted) if args.trusted else None
    try:
        kid = keygen(private, public, trusted, force=args.force, append=args.append)
    except (FileExistsError, ValueError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ key {kid}")
    print(f"  private: {private}")
    print(f"  public:  {public}")
    if trusted:
        print(f"  trusted: {trusted}")
    return 0


def _cmd_pack_book(args: argparse.Namespace) -> int:
    from .book import build_book_pack
    from .pack import write_pack

    try:
        pack = build_book_pack(
            Path(args.root),
            unit_id=args.id,
            title=args.title,
            theme=args.theme,
            tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()],
            level=args.level,
            pitch=args.pitch or "",
            parts=args.part,
            sanitize=args.sanitize,
        )
        out = (
            Path(args.out).resolve()
            if args.out
            else engine_root() / "build" / "packs" / f"{pack['id']}.json"
        )
        target = write_pack(pack, out)
    except (KeyError, ValueError, OSError, FileNotFoundError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ book pack: {target}")
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    import tempfile

    from .pack import build_pack, unit_from_root, write_pack

    try:
        if args.root:
            if args.unit:
                raise ValueError("use either COURSE or --root, not both")
            unit = unit_from_root(
                Path(args.root),
                unit_id=args.id,
                title=args.title,
                theme=args.theme,
                tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()],
                level=args.level,
                pitch=args.pitch or "",
                start=args.start,
            )
            with tempfile.TemporaryDirectory(prefix="lorekeeper-pack-") as temp:
                pack = build_pack(unit, Path(temp))
        else:
            unit = get_unit(args.unit)
            pack = build_pack(unit)
        out = (
            Path(args.out).resolve()
            if args.out
            else engine_root() / "build" / "packs" / f"{unit.slug}.json"
        )
        target = write_pack(pack, out)
    except (KeyError, ValueError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ pack: {target}")
    return 0


def _cmd_site(args: argparse.Namespace) -> int:
    from .site import build_site

    out = Path(args.out).resolve() if args.out else engine_root() / "_site"
    try:
        target = build_site(out, cname=args.cname)
    except (ValueError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ static site: {target}")
    return 0


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

    site = sub.add_parser("site", help="assemble a static site")
    site.add_argument("--out", help="output directory (default: _site)")
    site.add_argument("--cname", help="custom domain to write into CNAME")
    site.set_defaults(func=_cmd_site)

    pack = sub.add_parser("pack", help="build a portable course pack")
    pack.add_argument("unit", nargs="?", help="course key, code or slug")
    pack.add_argument("--root", help="unit folder to package without registering it")
    pack.add_argument("--id", help="pack/course slug for --root")
    pack.add_argument("--title", help="learner-facing title for --root")
    pack.add_argument("--theme", default="pixel", help="skin for --root (default: pixel)")
    pack.add_argument("--tags", default="", help="comma-separated tags for --root")
    pack.add_argument("--level", default="beginner", help="level for --root")
    pack.add_argument("--pitch", help="one-line pitch for --root")
    pack.add_argument("--start", default="01-01", help="starting lesson for --root")
    pack.add_argument("--out", help="output file (default: build/packs/<slug>.json)")
    pack.set_defaults(func=_cmd_pack)

    book = sub.add_parser("pack-book", help="build a pack from a Quarto book")
    book.add_argument("root", help="book repository root")
    book.add_argument("--id", help="pack/course slug")
    book.add_argument("--title", help="learner-facing title")
    book.add_argument("--theme", default="storybook", help="skin (default: storybook)")
    book.add_argument("--tags", default="", help="comma-separated tags")
    book.add_argument("--level", default="beginner", help="level")
    book.add_argument("--pitch", help="one-line pitch")
    book.add_argument("--part", help="book part number, range or list (default: all)")
    book.add_argument("--sanitize", action="store_true", help="replace course codes in learner content")
    book.add_argument("--out", help="output file")
    book.set_defaults(func=_cmd_pack_book)

    store = sub.add_parser("store", help="build the static pack catalogue")
    store.add_argument("--out", help="output directory (default: store/)")
    store.add_argument("--key", help="Ed25519 private key for signing")
    store.set_defaults(func=_cmd_store)

    keygen = sub.add_parser("keygen", help="create an Ed25519 signing key")
    keygen.add_argument("--private", help="private key path")
    keygen.add_argument("--public", help="public key path")
    keygen.add_argument("--trusted", help="write player/trusted-keys.js here")
    keygen.add_argument("--force", action="store_true", help="overwrite an existing key")
    keygen.add_argument("--append", action="store_true", help="append the public key to --trusted")
    keygen.set_defaults(func=_cmd_keygen)

    verify = sub.add_parser("verify-store", help="verify pack hashes and signatures")
    verify.add_argument("--store", help="store directory (default: store/)")
    verify.add_argument("--trusted", help="trusted keys file (default: player/trusted-keys.js)")
    verify.set_defaults(func=_cmd_verify_store)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
