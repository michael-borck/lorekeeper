"""Player browser smoke and accessibility checks.

These tests use Playwright when it is installed. They build the static site,
serve it locally, and exercise the learner-facing player in a clean context.
"""

from __future__ import annotations

import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")



@pytest.fixture(autouse=True)
def _require_course_sources():
    from lorekeeper.registry import load_units

    for unit in load_units():
        if not unit.root.is_dir():
            pytest.skip(f"course source not available: {unit.root}")

def serve_directory(path: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(path))
    handler.log_message = lambda *args, **kwargs: None
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/"


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> str:
    from lorekeeper.registry import load_units
    from lorekeeper.site import build_site

    for unit in load_units():
        if not unit.root.is_dir():
            pytest.skip(f"course source not available: {unit.root}")

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
    context = browser.new_context(reduced_motion="reduce")
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

    page.locator("#menu-toggle").click()
    for button in page.locator(".menu-panel button:visible").all():
        assert button.inner_text().strip(), "every menu button needs accessible text"
    journey = page.locator("#journey-dialog")
    page.locator("#journey-button").click()
    assert journey.get_attribute("open") is not None
    labelledby = journey.get_attribute("aria-labelledby")
    assert labelledby and journey.locator(f"#{labelledby}").count() == 1
    page.locator("#journey-close").click()


def open_signal_and_noise(page):
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)
    page.locator('.course-card[href*="signal-and-noise"]').click()
    page.wait_for_url("**/player/?course=signal-and-noise*")
    playwright_api.expect(page.locator(".lesson-title")).to_be_visible()


def test_modes_default_to_quest_with_sound_off(page):
    assert page.locator("html").get_attribute("data-theme") == "quest"
    options = [option.text_content() for option in page.locator("#theme-select option").all()]
    assert options == ["Quest", "Study"]
    page.locator("#menu-toggle").click()
    playwright_api.expect(page.locator("#sound-picker")).to_be_visible()
    assert page.locator("#sound-toggle").is_checked() is False

    page.locator("#theme-select").select_option("study")
    assert page.locator("html").get_attribute("data-theme") == "study"
    playwright_api.expect(page.locator("#sound-picker")).to_be_hidden()


def test_legacy_skin_names_migrate_to_modes(browser, site):
    for legacy, expected in (("pixel", "quest"), ("storybook", "quest"), ("ink", "study")):
        context = browser.new_context(reduced_motion="reduce")
        page = context.new_page()
        page.add_init_script(f"localStorage.setItem('lorekeeper:theme', '{legacy}')")
        page.goto(site + "player/")
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("data-theme") == expected
        context.close()


def test_quest_lesson_is_a_scene_with_narrator(page):
    open_signal_and_noise(page)
    playwright_api.expect(page.locator(".scene-banner")).to_be_visible()
    playwright_api.expect(page.locator(".scene-banner-text")).to_contain_text("Scene 1 of")
    playwright_api.expect(page.locator(".narrator-box strong")).not_to_have_text("")
    playwright_api.expect(page.locator(".kind-pill")).to_contain_text("Read")
    playwright_api.expect(page.locator("[data-complete]")).to_have_text("Done reading")
    playwright_api.expect(page.locator(".player-card")).to_contain_text("Level 1")
    playwright_api.expect(page.locator("#content")).to_have_class(re.compile(r"motion-quest"))

    page.locator("#menu-toggle").click()
    page.locator("#theme-select").select_option("study")
    playwright_api.expect(page.locator(".scene-banner")).to_have_count(0)
    playwright_api.expect(page.locator(".narrator")).to_have_count(0)
    playwright_api.expect(page.locator(".scene-count")).to_contain_text("Lesson 1 of")


def test_completion_moment_and_continue_hero(page):
    open_signal_and_noise(page)
    page.locator("[data-complete]").click()
    moment = page.locator("#moment")
    playwright_api.expect(moment).to_contain_text("Scene complete")
    playwright_api.expect(page.locator(".lesson-link.done")).to_have_count(1)

    page.goto(page.url.split("?")[0])
    page.wait_for_load_state("networkidle")
    hero = page.locator("#quest-hero.continuing")
    playwright_api.expect(hero).to_contain_text("Continue your quest")
    playwright_api.expect(hero.locator("[data-hero-next]")).to_contain_text("Next: Chapter 1, Scene 2")
    playwright_api.expect(page.locator(".course-card-kicker").filter(has_text="In progress")).to_have_count(1)


def test_course_map_shows_chapters_as_stops(page):
    open_signal_and_noise(page)
    page.locator("#map-link").click()
    playwright_api.expect(page.locator(".map-stop")).to_have_count(12)
    playwright_api.expect(page.locator(".map-stop.current")).to_have_count(1)
    page.locator(".map-stop-button").nth(2).click()
    playwright_api.expect(page.locator(".lesson-title")).to_be_visible()
    assert "#03-" in page.url


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

    # Read IndexedDB directly: the read transaction waits for the write to commit.
    value = page.evaluate(
        """() => new Promise((resolve, reject) => {
          const request = indexedDB.open("lorekeeper");
          request.onerror = () => reject(request.error);
          request.onsuccess = () => {
            const read = request.result.transaction("progress").objectStore("progress").get("signal-and-noise");
            read.onsuccess = () => resolve(read.result ? read.result.value : null);
            read.onerror = () => reject(read.error);
          };
        })"""
    )
    assert value and value.get("completed", {}).get("01-01") is True
    assert value.get("xp", 0) > 0

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


def test_interrupted_progress_write_is_replayed(page):
    page.evaluate(
        """() => localStorage.setItem(
          'lorekeeper:pending-progress:field-kit',
          JSON.stringify({ completed: { '01-01': true }, xp: 20, history: [] })
        )"""
    )
    page.reload()
    page.wait_for_load_state("networkidle")
    value = page.evaluate(
        "async () => { await window.LorekeeperPackStorage.ready();"
        " return window.LorekeeperPackStorage.getProgress('field-kit'); }"
    )
    assert value["completed"]["01-01"] is True
    assert page.evaluate("() => localStorage.getItem('lorekeeper:pending-progress:field-kit')") is None


def test_hotspot_markup_survives_sanitising(page):
    page.goto(page.url.split("player/")[0] + "player/?course=field-kit#01-03")
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".hotspot-target")).to_have_count(3)
    assert page.locator(".hotspot-board button").first.get_attribute("type") == "button"
    assert page.locator(".hotspot-board").get_by_text("No hotspot targets").count() == 0


def test_workshop_tools_are_marked_external(page):
    page.locator("#menu-toggle").click()
    for name in ("AI Toys", "Security Toys", "NetSim", "Programming Labs"):
        link = page.locator(".tool-link.external", has_text=name)
        playwright_api.expect(link).to_be_visible()
        assert link.get_attribute("target") == "_blank"
        assert "noopener" in link.get_attribute("rel")
        assert link.locator(".tool-icon").count() == 1
        assert "opens outside Lorekeeper" in link.locator(".sr-only").text_content()
    for name in ("Study Buddy", "Career Compass"):
        link = page.locator(".tool-link.download", has_text=name)
        playwright_api.expect(link.locator(".tool-tag")).to_have_text("Desktop")
        assert "desktop download" in link.locator(".sr-only").text_content()


def narration_data():
    import json
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "player" / "narrators.json").read_text(encoding="utf-8"))


def fill_vars(lines, **values):
    return [line.replace("{course}", values.get("course", "")).replace("{chapter}", values.get("chapter", "")) for line in lines]


def test_author_narrator_and_course_start_line(page):
    open_signal_and_noise(page)
    playwright_api.expect(page.locator(".narrator-box strong")).to_have_text("Master Hale")
    course = "Signal & Noise: An Enterprise Systems Field Guide"
    expected = fill_vars(narration_data()["narrators"]["architect"]["moments"]["courseStart"], course=course)
    assert page.locator("[data-narrator-line]").text_content() in expected


def test_learner_can_choose_a_guide(page):
    open_signal_and_noise(page)
    page.locator("#menu-toggle").click()
    page.locator("#narrator-select").select_option("oracle")
    playwright_api.expect(page.locator(".narrator-box strong")).to_have_text("Cog")
    page.locator("#narrator-select").select_option("")
    playwright_api.expect(page.locator(".narrator-box strong")).to_have_text("Master Hale")


def test_chapter_start_line_names_the_chapter(page):
    open_signal_and_noise(page)
    page.locator(".outline-module summary").nth(1).click()
    page.locator('[data-lesson="02-01"]').click()
    chapter = page.locator(".outline-module").nth(1).locator(".chapter-title").text_content().strip()
    expected = fill_vars(narration_data()["narrators"]["architect"]["moments"]["chapterStart"], chapter=chapter)
    playwright_api.expect(page.locator("[data-narrator-line]")).to_have_text(re.compile("|".join(map(re.escape, expected))))


def test_narrator_reacts_to_a_wrong_answer(page):
    page.goto(page.url.split("player/")[0] + "player/?course=field-kit#01-01")
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".narrator-box strong")).to_have_text("Orin the Archivist")
    page.get_by_role("button", name="Check order").click()
    retry = narration_data()["narrators"]["keeper"]["moments"]["retry"]
    playwright_api.expect(page.locator("[data-narrator-line]")).to_have_text(re.compile("|".join(map(re.escape, retry))))


def plan_security_trail(page):
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)
    page.locator(".wayfinder-cta [data-wayfinder-open]").click()
    for question, value in (("goal", 4), ("experience", 0), ("situation", 3), ("style", 1)):
        page.locator(f'input[name="{question}"][value="{value}"]').check()
    page.locator("#wayfinder-submit").click()
    playwright_api.expect(page.locator("#wayfinder-body .trail-strip")).to_be_visible()


def test_wayfinder_plans_a_trail_across_courses(page):
    plan_security_trail(page)
    stops = page.locator("#wayfinder-body .trail-stop")
    assert 2 <= stops.count() <= 4
    playwright_api.expect(stops.first).to_have_class(re.compile("current"))
    assert page.locator("#wayfinder-body .trail-stop.unexplored").count() >= 1
    page.locator("#wayfinder-close").click()
    panel = page.locator("#trail-card")
    playwright_api.expect(panel).to_be_visible()
    playwright_api.expect(panel.locator(".trail-summary-count")).to_have_text(re.compile(r"0/\d"))
    panel.locator("summary").click()
    assert panel.get_attribute("open") is None
    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.locator("#trail-card").get_attribute("open") is None


def test_world_map_shows_regions_courses_unexplored_and_trail(page):
    plan_security_trail(page)
    page.goto(page.url.split("?")[0] + "?view=world")
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".world-region-label")).to_have_count(8)
    playwright_api.expect(page.locator(".world-marker.known")).to_have_count(3)
    assert page.locator(".world-marker.unexplored").count() >= 25
    playwright_api.expect(page.locator(".world-route-line")).to_have_count(1)
    assert page.locator(".world-marker.on-trail").count() >= 2
    playwright_api.expect(page.locator(".world-marker.trail-current")).to_have_count(1)
    shire = page.locator(".world-marker.known", has=page.locator(".world-label", has_text="Signal & Noise"))
    assert "Hale's Keep" in shire.get_attribute("aria-label")

    page.locator("[data-world-unexplored]").uncheck()
    playwright_api.expect(page.locator(".world-marker.unexplored:not(.on-trail)")).to_have_count(0)
    page.locator("[data-world-unexplored]").check()

    page.locator(".world-marker.unexplored[data-world-store]").first.click(force=True)
    playwright_api.expect(page.locator("#store-dialog")).to_have_attribute("open", "")
    assert page.locator("#store-search").input_value()
    playwright_api.expect(page.locator(".store-card")).not_to_have_count(0)


def test_world_map_can_add_a_hidden_builtin_course(page):
    page.goto(page.url.split("?")[0] + "?view=world")
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".world-marker.known")).to_have_count(0)
    page.locator('.world-marker[data-world-add="field-kit"]').click(force=True)
    page.wait_for_url("**course=field-kit**")
    page.goto(page.url.split("?")[0])
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator(".course-card[href*='field-kit']")).to_have_count(1)


def test_version_one_trail_migrates(page):
    page.evaluate(
        """() => localStorage.setItem('lorekeeper:path', JSON.stringify({
          version: 1, course: 'field-kit', title: 'Field Kit',
          steps: [{ id: '01-01', title: 'Order the incident response', kind: 'order' }],
          secondary: { slug: 'ship-it', title: 'Ship It' }
        }))"""
    )
    page.reload()
    page.wait_for_load_state("networkidle")
    path = page.evaluate("() => JSON.parse(localStorage.getItem('lorekeeper:path'))")
    assert path["version"] == 2
    assert [stop["slug"] for stop in path["stops"]] == ["field-kit", "ship-it"]


def test_study_mode_world_is_a_list(page):
    page.goto(page.url.split("?")[0] + "?view=world")
    page.wait_for_load_state("networkidle")
    page.locator("#menu-toggle").click()
    page.locator("#theme-select").select_option("study")
    playwright_api.expect(page.locator(".world-stage")).to_be_hidden()
    playwright_api.expect(page.locator(".world-list")).to_be_visible()
    assert page.locator(".world-region").count() >= 5


def test_completing_every_stop_finishes_the_trail(page):
    page.evaluate(
        """() => {
          localStorage.setItem('lorekeeper:path', JSON.stringify({
            version: 2, answers: {}, createdAt: new Date().toISOString(),
            stops: [{ slug: 'field-kit', title: 'Field Kit', tags: [], narrator: '',
                      goal: [{ id: '01-01', title: 'Order the incident response', kind: 'order' }], chapter: 'Chapter 1' }]
          }));
          localStorage.setItem('lorekeeper:setting:hidden-courses', '[]');
          localStorage.setItem('lorekeeper:pending-progress:field-kit',
            JSON.stringify({ completed: { '01-01': true }, xp: 20, history: [] }));
        }"""
    )
    page.locator("[data-starter]").click()
    playwright_api.expect(page.locator(".course-row")).to_have_count(3)
    page.reload()
    page.wait_for_load_state("networkidle")
    playwright_api.expect(page.locator("#moment")).to_contain_text("Trail complete")
    playwright_api.expect(page.locator(".picker-trail")).to_contain_text("Pathfinder")
    assert page.evaluate("() => JSON.parse(localStorage.getItem('lorekeeper:path')).completedAt")
