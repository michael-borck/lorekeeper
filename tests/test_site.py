from pathlib import Path

from lorekeeper.site import build_site


def test_site_builds_with_player_build_and_cname(tmp_path: Path):
    out = build_site(tmp_path / "site", cname="lorekeeper.borck.education")
    assert (out / "index.html").is_file()
    assert (out / "nojekyll").is_file() is False
    assert (out / ".nojekyll").is_file()
    assert (out / "player" / "app.js").is_file()
    assert (out / "player" / "manifest.webmanifest").is_file()
    assert (out / "build" / "index.json").is_file()
    assert (out / "build" / "ship-it" / "course.json").is_file()
    assert (out / "build" / "ship-it" / "stories" / "launch-week.json").is_file()
    assert (out / "store" / "catalog.json").is_file()
    assert (out / "store" / "packs" / "pocket-incidents.json").is_file()
    assert (out / "CNAME").read_text().strip() == "lorekeeper.borck.education"
