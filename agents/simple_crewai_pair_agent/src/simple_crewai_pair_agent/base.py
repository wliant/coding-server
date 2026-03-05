"""Base classes for all agents in this library."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseAgentConfig(BaseModel):
    """Immutable configuration base for all agents."""

    model_config = {"frozen": True}


class BaseAgent(ABC):
    """Abstract base for all agent implementations."""

    def __init__(self, config: BaseAgentConfig) -> None:
        self.config = config

    @abstractmethod
    def run(self) -> Any: ...
