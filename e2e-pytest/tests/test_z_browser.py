import pytest
from playwright.sync_api import Page, expect


def test_homepage_redirects_to_tasks(page: Page, base_url: str):
    page.goto(base_url)
    expect(page).to_have_url(f"{base_url}/tasks")


def test_tasks_page_has_heading(page: Page, base_url: str):
    page.goto(f"{base_url}/tasks")
    expect(page.get_by_role("heading", name="Tasks")).to_be_visible()


def test_submit_task_link_visible(page: Page, base_url: str):
    page.goto(f"{base_url}/tasks")
    expect(page.get_by_role("main").get_by_role("link", name="Submit Task")).to_be_visible()
