"""Shared fixtures for controller tests."""
import pytest
from controller.registry import WorkerRegistry


@pytest.fixture
def registry() -> WorkerRegistry:
    return WorkerRegistry()
