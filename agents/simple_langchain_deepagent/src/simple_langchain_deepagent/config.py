"""Configuration for the DeepAgent."""

from pathlib import Path

from pydantic import BaseModel, Field


class DeepAgentConfig(BaseModel):
    """Immutable, fully self-contained configuration for a deep agent run."""

    model_config = {"frozen": True}

    # LLM settings
    llm_provider: str = "ollama"  # "ollama" | "openai" | "anthropic"
    llm_model: str = "qwen2.5-coder:7b"
    llm_temperature: float = Field(0.2, ge=0.0, le=2.0)
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = "NA"
    anthropic_api_key: str = ""

    # Job inputs (per-run)
    working_directory: Path
    project_name: str = Field(..., min_length=1)
    requirement: str = Field(..., min_length=1)
