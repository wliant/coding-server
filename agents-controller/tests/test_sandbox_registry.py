"""Tests for the SandboxRegistry."""
import uuid

import pytest

from controller.sandbox_registry import SandboxRegistry


@pytest.mark.asyncio
async def test_register_sandbox():
    registry = SandboxRegistry()
    sid = await registry.register("sb-1", "http://sandbox1:8006", ["python", "git"])
    assert sid == "sb-1"
    all_sandboxes = await registry.get_all()
    assert len(all_sandboxes) == 1
    assert all_sandboxes[0].sandbox_id == "sb-1"
    assert all_sandboxes[0].labels == ["python", "git"]
    assert all_sandboxes[0].status == "free"


@pytest.mark.asyncio
async def test_register_replaces_existing():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    await registry.register("sb-1", "http://sandbox1-new:8006", ["python", "docker"])
    all_sandboxes = await registry.get_all()
    assert len(all_sandboxes) == 1
    assert all_sandboxes[0].sandbox_url == "http://sandbox1-new:8006"
    assert all_sandboxes[0].labels == ["python", "docker"]


@pytest.mark.asyncio
async def test_heartbeat_updates_status():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    result = await registry.heartbeat("sb-1", "free")
    assert result is True


@pytest.mark.asyncio
async def test_heartbeat_returns_false_for_unknown():
    registry = SandboxRegistry()
    result = await registry.heartbeat("nonexistent", "free")
    assert result is False


@pytest.mark.asyncio
async def test_get_free_sandbox_for_capabilities_exact_match():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python", "git"])
    sandbox = await registry.get_free_sandbox_for_capabilities(["python", "git"])
    assert sandbox is not None
    assert sandbox.sandbox_id == "sb-1"


@pytest.mark.asyncio
async def test_get_free_sandbox_for_capabilities_subset():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python", "git", "docker"])
    sandbox = await registry.get_free_sandbox_for_capabilities(["python"])
    assert sandbox is not None
    assert sandbox.sandbox_id == "sb-1"


@pytest.mark.asyncio
async def test_get_free_sandbox_for_capabilities_no_match():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    sandbox = await registry.get_free_sandbox_for_capabilities(["python", "docker"])
    assert sandbox is None


@pytest.mark.asyncio
async def test_get_free_sandbox_for_capabilities_skips_allocated():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python", "git"])
    await registry.allocate("sb-1", str(uuid.uuid4()))
    sandbox = await registry.get_free_sandbox_for_capabilities(["python"])
    assert sandbox is None


@pytest.mark.asyncio
async def test_get_free_sandbox_no_capabilities_required():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    sandbox = await registry.get_free_sandbox_for_capabilities(None)
    assert sandbox is not None


@pytest.mark.asyncio
async def test_allocate_and_free():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    task_id = str(uuid.uuid4())
    await registry.allocate("sb-1", task_id)

    all_sandboxes = await registry.get_all()
    assert all_sandboxes[0].status == "allocated"
    assert all_sandboxes[0].current_task_id == task_id

    await registry.free_sandbox("sb-1")
    all_sandboxes = await registry.get_all()
    assert all_sandboxes[0].status == "free"
    assert all_sandboxes[0].current_task_id is None


@pytest.mark.asyncio
async def test_mark_unreachable():
    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    await registry.mark_unreachable("sb-1")
    all_sandboxes = await registry.get_all()
    assert all_sandboxes[0].status == "unreachable"


@pytest.mark.asyncio
async def test_get_stale_sandboxes():
    from datetime import datetime, timedelta, timezone

    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    # Make it stale
    registry._sandboxes["sb-1"].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )
    stale = await registry.get_stale_sandboxes(timeout_seconds=60)
    assert len(stale) == 1
    assert stale[0].sandbox_id == "sb-1"


@pytest.mark.asyncio
async def test_get_stale_sandboxes_excludes_unreachable():
    from datetime import datetime, timedelta, timezone

    registry = SandboxRegistry()
    await registry.register("sb-1", "http://sandbox1:8006", ["python"])
    registry._sandboxes["sb-1"].last_heartbeat_at = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    )
    await registry.mark_unreachable("sb-1")
    stale = await registry.get_stale_sandboxes(timeout_seconds=60)
    assert len(stale) == 0
