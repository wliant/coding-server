import pytest
import httpx
import asyncpg
import os

API_URL = os.environ.get("API_URL", "http://localhost:8100")


async def test_list_tasks_count_matches_db(http: httpx.Client, db: asyncpg.Connection):
    r = http.get(f"{API_URL}/tasks")
    assert r.status_code == 200
    db_count = await db.fetchval("SELECT COUNT(*) FROM jobs")
    assert len(r.json()) == db_count


async def test_create_task_persisted_in_db(http: httpx.Client, db: asyncpg.Connection):
    projects_r = http.get(f"{API_URL}/projects")
    projects = projects_r.json()
    if not projects:
        pytest.skip("No projects available")

    payload = {
        "project_id": projects[0]["id"],
        "description": "e2e-pytest smoke test task",
        "branch": "main",
    }
    r = http.post(f"{API_URL}/tasks", json=payload)
    assert r.status_code == 201
    task_id = r.json()["id"]

    row = await db.fetchrow("SELECT * FROM jobs WHERE id = $1", task_id)
    assert row is not None
    assert row["description"] == payload["description"]
    assert row["status"] == "pending"
