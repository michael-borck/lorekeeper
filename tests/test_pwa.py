import json
from pathlib import Path


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_pwa_assets_are_present():
    for name in (
        "player/manifest.webmanifest",
        "player/sw.js",
        "player/progress-file.js",
        "player/wayfinder.js",
        "player/icons/icon-192.png",
        "player/icons/icon-512.png",
        "player/icons/icon-maskable-512.png",
    ):
        assert (root() / name).is_file(), name


def test_manifest_has_install_fields():
    manifest = json.loads((root() / "player" / "manifest.webmanifest").read_text())
    assert manifest["name"]
    assert manifest["short_name"]
    assert manifest["start_url"] == "./"
    assert manifest["display"] == "standalone"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert "192x192" in sizes
    assert "512x512" in sizes
