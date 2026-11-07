"""Browser tests for the local authoring studio."""

from __future__ import annotations

import threading

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

from lorekeeper.studio import StudioHandler, StudioServer  # noqa: E402


@pytest.fixture(scope="module")
def studio_url():
    class Handler(StudioHandler):
        studio_token = "test-studio-token"

    server = StudioServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    yield url + "/studio/?token=test-studio-token"
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
def page(browser, studio_url):
    context = browser.new_context()
    page = context.new_page()
    page.goto(studio_url)
    playwright_api.expect(page.locator("#lesson-list .lesson-row").first).to_be_visible()
    yield page
    context.close()


def test_studio_loads_courses_modules_and_lessons(page):
    playwright_api.expect(page.locator("#course")).not_to_have_value("")
    playwright_api.expect(page.locator("#module")).not_to_have_value("")
    playwright_api.expect(page.locator("#lesson-list .lesson-row")).not_to_have_count(0)
    playwright_api.expect(page.locator("#yaml")).not_to_have_value("")


def test_studio_lesson_rows_are_keyboard_accessible(page):
    first = page.locator("#lesson-list .lesson-select").first
    playwright_api.expect(first).to_be_enabled()
    assert first.inner_text().strip()
    first.focus()
    page.keyboard.press("Enter")
    playwright_api.expect(page.locator("#apply-lesson")).to_be_enabled()


def test_studio_lesson_operations_are_reflected_in_yaml(page):
    before = page.locator("#lesson-list .lesson-row").count()
    page.locator("#lesson-list .lesson-actions button[title='Duplicate lesson']").first.click()
    playwright_api.expect(page.locator("#lesson-list .lesson-row")).to_have_count(before + 1)
    assert "(copy)" in page.locator("#yaml").input_value()

    page.locator("#lesson-list .lesson-actions button[title='Delete lesson']").first.click()
    playwright_api.expect(page.locator("#lesson-list .lesson-row")).to_have_count(before)


def test_studio_undo_restores_lesson_list(page):
    before = page.locator("#lesson-list .lesson-row").count()
    page.locator("#lesson-list .lesson-actions button[title='Duplicate lesson']").first.click()
    playwright_api.expect(page.locator("#lesson-list .lesson-row")).to_have_count(before + 1)
    page.locator("#undo").click()
    playwright_api.expect(page.locator("#lesson-list .lesson-row")).to_have_count(before)


def test_studio_source_picker_and_inspector_are_available(page):
    page.locator("details.panel", has_text="Reading source").locator("summary").click()
    playwright_api.expect(page.locator("#source-file option")).not_to_have_count(1)
    page.locator("#source-file").select_option(index=1)
    playwright_api.expect(page.locator("#source-headings label")).not_to_have_count(0)

    inspector = page.locator("details.panel", has_text="Lesson inspector")
    inspector.locator("summary").click()
    playwright_api.expect(inspector.locator("[data-inspector-key='title']")).to_be_visible()
    playwright_api.expect(page.locator("#apply-lesson")).to_be_enabled()


def test_studio_builds_a_pack(page, studio_url):
    pack = page.locator("details.panel", has_text="Build a pack")
    pack.locator("summary").click()
    page.locator("#pack-author").fill("Studio Test")
    page.locator("#pack-licence").fill("CC BY 4.0")
    page.locator("#pack-build").click()
    playwright_api.expect(page.locator("#pack-download")).to_be_visible()
    playwright_api.expect(page.locator("#pack-result")).to_contain_text("Built")
    href = page.locator("#pack-download").get_attribute("href")
    assert href and href.startswith("/build/studio-packs/")
    response = page.request.get(studio_url.split("/studio/")[0] + href)
    assert response.ok
    payload = response.json()
    assert payload["format"] == "lorekeeper.pack"
    assert payload["author"] == "Studio Test"


def test_studio_static_boundary_hides_source_files(page, studio_url):
    base = studio_url.split("/studio/")[0]
    assert page.request.get(base + "/courses").status == 404
    assert page.request.get(base + "/lorekeeper/studio.py").status == 404
    assert page.request.get(base + "/studio/").status == 200
