"""simple_crewai_pair_agent — public API for the CrewAI pair-programming agent."""

from simple_crewai_pair_agent.agent import CodingAgent
from simple_crewai_pair_agent.config import CodingAgentConfig
from simple_crewai_pair_agent.result import CodingAgentResult

__all__ = ["CodingAgent", "CodingAgentConfig", "CodingAgentResult"]
