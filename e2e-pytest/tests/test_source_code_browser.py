"""E2e tests for the Source Code Browser feature (010)."""
import os

import httpx
import pytest
from playwright.sync_api import Page, expect

API_URL = os.environ.get("API_URL", "http://localhost:8100")
WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8101")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:3100")


def _get_agent_id(http: httpx.Client) -> str:
    r = http.get(f"{API_URL}/agents")
    r.raise_for_status()
    return r.json()[0]["id"]


def _create_task(http: httpx.Client, agent_id: str) -> str:
    r = http.post(
        f"{API_URL}/tasks",
        json={
            "project_type": "new",
            "project_name": "E2E Source Code Browser",
            "agent_id": agent_id,
            "requirements": "e2e source code browser test",
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


def test_task_detail_has_assigned_worker_url_field(http: httpx.Client):
    agent_id = _get_agent_id(http)
    task_id = _create_task(http, agent_id)
    r = http.get(f"{API_URL}/tasks/{task_id}")
    assert r.status_code == 200
    assert "assigned_worker_url" in r.json()


# ---------------------------------------------------------------------------
# Worker-level tests
# ---------------------------------------------------------------------------


def test_worker_files_404_when_idle(http: httpx.Client):
    r = http.get(f"{WORKER_URL}/files")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_worker_file_content_404_when_idle(http: httpx.Client):
    r = http.get(f"{WORKER_URL}/files/readme.md")
    assert r.status_code == 404


def test_worker_files_cors_preflight(http: httpx.Client):
    r = http.options(
        f"{WORKER_URL}/files",
        headers={
            "Origin": "http://web:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    headers_lower = {k.lower(): v for k, v in r.headers.items()}
    assert "access-control-allow-origin" in headers_lower


# ---------------------------------------------------------------------------
# Browser-level tests
# ---------------------------------------------------------------------------


def test_source_code_section_not_visible_for_pending_task(
    page: Page, http: httpx.Client
):
    agent_id = _get_agent_id(http)
    task_id = _create_task(http, agent_id)
    page.goto(f"{BASE_URL}/tasks/{task_id}")
    # Wait for task detail to load
    expect(page.get_by_text("Task Detail")).to_be_visible()
    # Source Code section must NOT appear for pending tasks
    expect(page.get_by_text("Source Code")).not_to_be_visible()


def test_download_code_not_in_main_panel_for_pending_task(
    page: Page, http: httpx.Client
):
    """Download Code button must not appear in the main panel."""
    agent_id = _get_agent_id(http)
    task_id = _create_task(http, agent_id)
    page.goto(f"{BASE_URL}/tasks/{task_id}")
    expect(page.get_by_text("Task Detail")).to_be_visible()
    # Old location (main panel) should not have the button
    expect(
        page.locator(".rounded-lg.border")
        .first.get_by_role("button", name="Download Code")
    ).not_to_be_visible()
