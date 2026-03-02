import os
import pytest


def test_agent_state_keys():
    from worker.state import AgentState
    state: AgentState = {
        "job_id": "test-123",
        "requirement": "Build something",
        "messages": [],
        "tool_calls": [],
        "output": None,
        "error": None,
    }
    assert "job_id" in state
    assert "requirement" in state
    assert "messages" in state


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://testhost:6379/0")
    monkeypatch.setenv("AGENT_WORK_PARENT", "/tmp/test-work")
    # Re-import to pick up patched env
    import importlib
    import worker.config as cfg_module
    importlib.reload(cfg_module)
    from worker.config import Settings
    settings = Settings()
    assert settings.REDIS_URL == "redis://testhost:6379/0"
    assert settings.AGENT_WORK_PARENT == "/tmp/test-work"
