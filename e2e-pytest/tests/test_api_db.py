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
    agents_r = http.get(f"{API_URL}/agents")
    agents = agents_r.json()
    if not agents:
        pytest.skip("No agents available")

    payload = {
        "task_type": "build_feature",
        "agent_id": agents[0]["id"],
        "git_url": "https://github.com/example/repo.git",
        "requirements": "e2e-pytest smoke test task",
    }
    r = http.post(f"{API_URL}/tasks", json=payload)
    assert r.status_code == 201
    task_id = r.json()["id"]

    row = await db.fetchrow("SELECT * FROM jobs WHERE id = $1", task_id)
    assert row is not None
    assert row["requirement"] == payload["requirements"]
    assert row["status"] == "pending"
    assert row["task_type"] == "build_feature"
