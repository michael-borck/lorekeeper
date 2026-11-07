"""Player browser smoke and accessibility checks.

These tests use Playwright when it is installed. They build the static site,
serve it locally, and exercise the learner-facing player in a clean context.
"""

from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")


def serve_directory(path: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(path))
    handler.log_message = lambda *args, **kwargs: None
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/"


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> str:
    from lorekeeper.site import build_site

    out = build_site(tmp_path_factory.mktemp("player-site") / "site")
    server, url = serve_directory(out)
    yield url
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as runner:
        try:
            browser = runner.chromium.launch()
        except Exception as error:
            pytest.skip(f"Playwright Chromium is unavailable: {error}")
        yield browser
        browser.close()


@pytest.fixture
def page(browser, site):
    context = browser.new_context()
    page = context.new_page()
    console_errors = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.console_errors = console_errors
    page.goto(site + "player/")
    page.wait_for_load_state("networkidle")
    yield page
    context.close()


def test_landing_page_exposes_authoring_studio(site, browser):
    page = browser.new_context().new_page()
    page.goto(site)
    section = page.locator("#authors")
    expect = playwright_api.expect
    expect(section).to_contain_text("Build packs on your own machine.")
    expect(section).to_contain_text("python3 -m lorekeeper studio")
    expect(section).to_contain_text("A GitHub account is required")
    link = section.get_by_role("link", name="Pack submission queue")
    expect(link).to_have_attribute("href", "https://github.com/michael-borck/lorekeeper-packs")
    page.context.close()


def test_player_shell_meets_basic_accessibility(page):
    assert page.locator("html").get_attribute("lang") == "en-AU"
    assert page.locator("main").count() == 1
    assert page.locator('aside[aria-label="Course outline"]').count() == 1

    for button in page.locator("button:visible").all():
        assert button.inner_text().strip(), "every visible button needs accessible text"
    for image in page.locator("img").all():
        assert image.get_attribute("alt") is not None, "every image needs an alt attribute"

    journey = page.locator("#journey-dialog")
    page.locator("#journey-button").click()
    assert journey.get_attribute("open") is not None
    labelledby = journey.get_attribute("aria-labelledby")
    assert labelledby and journey.locator(f"#{labelledby}").count() == 1
    page.locator("#journey-close").click()


def test_player_starts_empty_and_restores_starter_kit(page):
    empty = page.locator(".empty-library")
    playwright_api.expect(empty).to_contain_text("Your library is empty")
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)


def test_direct_link_to_hidden_builtin_course_still_opens(page):
    page.goto(page.url.split("player/")[0] + "player/?course=signal-and-noise")
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".lesson-title")).to_be_visible()
    playwright_api.expect(page.locator(".lesson-title")).not_to_have_text("Not quite yet")


def test_store_search_and_filters(page):
    page.locator("#store-open").click()
    grid = page.locator(".store-grid")
    playwright_api.expect(grid.locator(".store-card")).to_have_count(30)

    page.locator('[data-store-cat="programming"]').click()
    programming_count = grid.locator(".store-card").count()
    assert programming_count > 0

    page.locator("#store-search").fill("network")
    playwright_api.expect(page.locator(".store-toolbar")).to_be_visible()
    assert grid.locator(".store-card").count() <= programming_count
    page.locator("#store-close").click()


def test_progress_is_persisted_in_indexeddb(page):
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)

    page.locator('.course-card[href*="signal-and-noise"]').click()
    page.wait_for_url("**/player/?course=signal-and-noise*")
    complete = page.locator("[data-complete]")
    complete.click()
    playwright_api.expect(complete).to_have_text("Completed")

    value = page.evaluate(
        "async () => {"
        " await window.LorekeeperPackStorage.ready();"
        " return window.LorekeeperPackStorage.getProgress('signal-and-noise');"
        "}"
    )
    assert value and value.get("completed", {}).get("01-01") is True

    page.reload()
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator("[data-complete]")).to_have_text("Completed")


def test_exercise_sandbox_runs_under_csp(page):
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)
    page.locator('.course-card[href*="ship-it"]').click()
    page.wait_for_url("**/player/?course=ship-it*")
    sidebar_link = page.locator('[data-lesson="01-03"]')
    playwright_api.expect(sidebar_link).to_be_visible()
    sidebar_link.click()
    page.wait_for_load_state("networkidle")

    exercise = page.locator("div.exercise")
    playwright_api.expect(exercise).to_be_visible()
    exercise.locator("[data-run]").click()
    exercise.locator(".test-item").first.wait_for(state="visible", timeout=10_000)
    summary = exercise.locator("[data-summary]").inner_text()
    assert "tests passed" in summary.lower()


def test_pack_prose_sanitizer_blocks_active_content(page):
    result = page.evaluate(
        """() => window.LorekeeperSanitize.html(`
            <p onclick="alert(1)">Safe <strong>prose</strong></p>
            <script>window.__pwned = true;<\\/script>
            <a href="javascript:alert(1)">bad</a>
            <img src="x" onerror="alert(1)">
        `)"""
    )
    assert "Safe" in result
    assert "<strong>" in result
    assert "<script" not in result.lower()
    assert "onerror" not in result.lower()
    assert 'onclick' not in result.lower()
    assert "javascript:" not in result.lower()
    safe_markup = page.evaluate(
        """() => window.LorekeeperSanitize.html(
          '<div class="hotspot-board" data-spot="bad"><a id="target" href="#target">link</a></div>'
        )"""
    )
    assert 'class="hotspot-board"' in safe_markup
    assert 'data-spot="bad"' in safe_markup
    assert 'id="lr-target"' in safe_markup
    assert 'href="#lr-target"' in safe_markup
    assert page.evaluate("() => window.__pwned === undefined")
    asset = page.evaluate(
        """() => {
          window.LorekeeperPackAssets = {"dot.png": "data:image/png;base64,AAAA"};
          return window.LorekeeperSanitize.html('<img src="assets/dot.png" alt="">');
        }"""
    )
    assert 'src="data:image/png;base64,AAAA"' in asset


def test_pack_structure_cannot_inject_markup(page):
    error = page.evaluate(
        """() => {
          const pack = {
            format: "lorekeeper.pack",
            version: 1,
            id: "bad-pack",
            title: "Bad",
            courses: [{
              slug: "bad-pack",
              course: {
                unit: { slug: "bad-pack", title: "Bad" },
                modules: [{
                  number: 1,
                  slug: "01-bad",
                  title: "Bad",
                  lessons: [{
                    id: "01-01",
                    title: "Bad",
                    kind: 'reading\" onmouseover=\"alert(1)',
                    xp: 10,
                    blocks: [{ type: "html", html: "<p>ok</p>" }]
                  }]
                }]
              },
              stories: {}
            }]
          };
          try {
            window.LorekeeperLibrary.validatePack(pack);
            return "";
          } catch (error) {
            return error.message;
          }
        }"""
    )
    assert "unknown lesson kind" in error


def test_player_shell_works_offline(browser, site):
    context = browser.new_context()
    page = context.new_page()
    page.goto(site + "player/")
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=10_000)
    page.reload()
    page.wait_for_load_state("networkidle")
    context.set_offline(True)
    page.goto(site + "player/", wait_until="domcontentloaded")
    assert page.locator("#content").inner_text().strip()
    assert "Lorekeeper" in page.inner_text("body")
    context.close()


def test_player_has_no_console_errors(page):
    assert page.locator("#content").inner_text().strip()
    assert page.console_errors == []
