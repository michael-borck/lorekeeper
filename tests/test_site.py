from pathlib import Path

from lorekeeper.site import build_site


def test_site_builds_with_player_build_and_cname(tmp_path: Path):
    out = build_site(tmp_path / "site", cname="lorekeeper.borck.education")
    assert (out / "index.html").is_file()
    landing = (out / "index.html").read_text(encoding="utf-8")
    assert "Open Lorekeeper" in landing
    assert "Private by design" in landing
    assert "progressive web app" in landing
    assert "Build packs on your own machine." in landing
    assert "python3 -m lorekeeper studio" in landing
    assert "https://github.com/michael-borck/lorekeeper-packs" in landing
    assert (out / "nojekyll").is_file() is False
    assert (out / ".nojekyll").is_file()
    assert (out / "player" / "app.js").is_file()
    assert (out / "player" / "storage.js").is_file()
    assert (out / "player" / "manage.js").is_file()
    assert (out / "player" / "journey.js").is_file()
    assert (out / "player" / "tutor.js").is_file()
    assert (out / "player" / "manifest.webmanifest").is_file()
    assert (out / "build" / "index.json").is_file()
    assert (out / "build" / "ship-it" / "course.json").is_file()
    assert (out / "build" / "ship-it" / "stories" / "launch-week.json").is_file()
    assert (out / "store" / "catalog.json").is_file()
    assert (out / "store" / "packs" / "pocket-incidents.json").is_file()
    assert (out / "store" / "packs" / "information-security.json").is_file()
    assert (out / "store" / "packs" / "audit-and-control.json").is_file()
    assert (out / "store" / "packs" / "assume-breach.json").is_file()
    assert (out / "store" / "packs" / "speak-software.json").is_file()
    assert (out / "store" / "packs" / "build-web-guide-ai.json").is_file()
    assert (out / "store" / "packs" / "systems-analysis-and-design.json").is_file()
    assert (out / "store" / "packs" / "follow-the-trace.json").is_file()
    assert (out / "store" / "packs" / "the-human-edge.json").is_file()
    assert (out / "store" / "packs" / "test-the-claim.json").is_file()
    assert (out / "store" / "packs" / "substantiate-dont-assume.json").is_file()
    assert (out / "store" / "packs" / "conversation-not-delegation.json").is_file()
    assert (out / "store" / "packs" / "prove-dont-persuade.json").is_file()
    assert (out / "store" / "packs" / "build-ai-understand-ai.json").is_file()
    assert (out / "store" / "packs" / "break-with-permission.json").is_file()
    assert (out / "store" / "packs" / "follow-the-packet.json").is_file()
    assert (out / "store" / "packs" / "simplebot.json").is_file()
    assert (out / "store" / "packs" / "build-it-teach-it.json").is_file()
    for pack_id in [
        "think-python-direct-ai",
        "code-python-consult-ai",
        "ship-python-orchestrate-ai",
        "converse-python-partner-ai",
        "partner-dont-police",
        "the-absolute-minimum-you-must-know",
        "the-great-silence",
        "programming-paradigms",
        "simulate-it",
        "ai-toys",
        "security-toys",
        "netsim-field-guide",
    ]:
        assert (out / "store" / "packs" / f"{pack_id}.json").is_file()
    assert (out / "CNAME").read_text().strip() == "lorekeeper.borck.education"
