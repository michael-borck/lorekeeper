import json
from pathlib import Path


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_pwa_assets_are_present():
    for name in (
        "player/manifest.webmanifest",
        "player/sw.js",
        "player/progress-file.js",
        "player/storage.js",
        "player/sanitize.js",
        "player/library.js",
        "player/wayfinder.js",
        "player/store.js",
        "player/icons/icon-192.png",
        "player/icons/icon-512.png",
        "player/icons/icon-maskable-512.png",
    ):
        assert (root() / name).is_file(), name


def test_player_csp_blocks_remote_scripts_and_active_content():
    html = (root() / "player" / "index.html").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html
    assert "default-src 'self'" in html
    assert "object-src 'none'" in html
    assert "script-src" in html
    assert "https:" not in html.split("script-src", 1)[1].split(";", 1)[0]


def test_pack_library_sanitizes_rendered_prose():
    library = (root() / "player" / "library.js").read_text(encoding="utf-8")
    assert "LorekeeperSanitize?.html(block.html)" in library
    assert "LorekeeperSanitize?.html(block.prompt)" in library

    app = (root() / "player" / "app.js").read_text(encoding="utf-8")
    assert "LorekeeperSanitize?.html" in app


def test_progress_uses_indexeddb_storage_abstraction():
    storage = (root() / "player" / "storage.js").read_text(encoding="utf-8")
    for name in ("PROGRESS_STORE", "getProgress", "putProgress", "deleteProgress", "clearProgress"):
        assert name in storage
    app = (root() / "player" / "app.js").read_text(encoding="utf-8")
    assert "LorekeeperPackStorage?.getProgress(" in app
    assert "LorekeeperPackStorage?.putProgress(" in app


def test_manifest_has_install_fields():
    manifest = json.loads((root() / "player" / "manifest.webmanifest").read_text())
    assert manifest["name"]
    assert manifest["short_name"]
    assert manifest["start_url"] == "./"
    assert manifest["display"] == "standalone"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert "192x192" in sizes
    assert "512x512" in sizes
