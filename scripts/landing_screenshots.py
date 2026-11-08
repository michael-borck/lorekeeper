#!/usr/bin/env python3
"""Capture the landing-page screenshots of Quest and Study mode.

Builds the static site into a temporary folder, serves it, drives the player
with Playwright and writes WebP files to player/art/landing/.

  python3 scripts/landing_screenshots.py
"""

from __future__ import annotations

import functools
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from lorekeeper.site import build_site  # noqa: E402

OUT = ROOT / "player" / "art" / "landing"
VIEWPORT = {"width": 1440, "height": 900}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:  # noqa: D401
        return


def save(png: Path, name: str, width: int = 1200) -> None:
    image = Image.open(png).convert("RGB")
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    dest = OUT / f"{name}.webp"
    image.save(dest, "WEBP", quality=80, method=6)
    print(f"  {dest.relative_to(ROOT)}  {dest.stat().st_size // 1024} KB")


def capture(browser, url: str, mode: str, tmp: Path) -> None:
    context = browser.new_context(viewport=VIEWPORT, reduced_motion="reduce")
    page = context.new_page()
    page.add_init_script(f"localStorage.setItem('lorekeeper:theme', '{mode}')")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.locator("[data-starter]").click()
    page.locator('.course-card[href*="signal-and-noise"]').click()
    page.wait_for_url("**signal-and-noise**")
    page.locator("[data-complete]").click()
    page.wait_for_timeout(2200)
    page.locator('[data-lesson="01-02"]').click()
    page.wait_for_timeout(500)
    shot = tmp / f"{mode}-lesson.png"
    page.screenshot(path=str(shot))
    save(shot, f"{mode}-lesson")
    if mode == "quest":
        page.locator("#map-link").click()
        page.wait_for_timeout(500)
        shot = tmp / "quest-map.png"
        page.screenshot(path=str(shot))
        save(shot, "quest-map")
    context.close()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        site = build_site(tmp / "site")
        handler = functools.partial(QuietHandler, directory=str(site))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/player/"
        try:
            with sync_playwright() as runner:
                browser = runner.chromium.launch()
                for mode in ("quest", "study"):
                    capture(browser, url, mode, tmp)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
