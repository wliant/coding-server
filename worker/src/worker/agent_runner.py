"""Agent invocation for the worker.

Wraps simple_crewai_pair_agent.CodingAgent to:
  - Fetch LLM configuration from the API's GET /settings endpoint
  - Create the isolated working directory
  - Insert a WorkDirectory DB record
  - Return (success, error_message) tuple
"""
import logging
import traceback
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from worker.models import Job, Project, WorkDirectory

logger = logging.getLogger(__name__)

# Module-level import; set to None on ImportError so tests can still patch
# worker.agent_runner.CodingAgent / CodingAgentConfig.
try:
    from simple_crewai_pair_agent import CodingAgent, CodingAgentConfig
except ImportError:  # pragma: no cover
    CodingAgent = None  # type: ignore[assignment, misc]
    CodingAgentConfig = None  # type: ignore[assignment, misc]


def _resolve_agent_classes():
    """Return (CodingAgent, CodingAgentConfig), retrying import if module-level failed."""
    global CodingAgent, CodingAgentConfig  # noqa: PLW0603
    if CodingAgent is not None and CodingAgentConfig is not None:
        return CodingAgent, CodingAgentConfig
    # Retry import — the package may have become available after worker startup
    from simple_crewai_pair_agent import CodingAgent as _CA, CodingAgentConfig as _CAC
    CodingAgent = _CA  # type: ignore[assignment]
    CodingAgentConfig = _CAC  # type: ignore[assignment]
    return CodingAgent, CodingAgentConfig


async def _fetch_agent_settings(api_url: str) -> dict[str, str]:
    """Fetch settings from the API. Raises httpx.RequestError on network failure."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/settings")
        response.raise_for_status()
        data = response.json()
        return data["settings"]


async def run_coding_agent(
    db: AsyncSession,
    job: Job,
    project: Project,
    settings,
) -> tuple[bool, str | None]:
    """Run the coding agent for the given job.

    1. Fetches config via GET {settings.API_URL}/settings
       Returns (False, "unable to fetch agent settings") if API is unreachable.
    2. Derives work_dir using agent.work.path from settings (must be absolute);
       falls back to settings.AGENT_WORK_PARENT if empty or relative.
    3. Creates a WorkDirectory DB record
    4. Invokes CodingAgent(CodingAgentConfig(...)).run()
    5. Returns (True, None) on success, (False, error_message) on failure

    Any exception from the agent is caught and returned as an error result.
    """
    # Fetch LLM configuration from the API
    try:
        agent_settings = await _fetch_agent_settings(settings.API_URL)
    except httpx.RequestError as exc:
        logger.error(
            "settings_fetch_failed",
            extra={"event": "settings_fetch_failed", "job_id": str(job.id), "error": str(exc)},
        )
        return False, "unable to fetch agent settings"

    configured_path = agent_settings.get("agent.work.path", "").strip()
    work_base = configured_path if configured_path else settings.AGENT_WORK_PARENT
    work_base_path = Path(work_base)
    if not work_base_path.is_absolute():
        logger.warning(
            "work_path_not_absolute",
            extra={
                "event": "work_path_not_absolute",
                "job_id": str(job.id),
                "configured_path": work_base,
                "fallback": settings.AGENT_WORK_PARENT,
            },
        )
        work_base_path = Path(settings.AGENT_WORK_PARENT)
    work_dir = work_base_path / str(job.id)
    work_dir_path = str(work_dir)

    # Insert WorkDirectory record before running the agent
    work_directory = WorkDirectory(
        job_id=job.id,
        path=work_dir_path,
    )
    db.add(work_directory)
    await db.commit()

    project_name = project.name if project.name else str(job.id)[:8]

    logger.info(
        "agent_starting",
        extra={
            "event": "agent_starting",
            "job_id": str(job.id),
            "work_dir": work_dir_path,
            "project_name": project_name,
            "llm_provider": agent_settings.get("agent.simple_crewai.llm_provider", "ollama"),
            "llm_model": agent_settings.get("agent.simple_crewai.llm_model", "qwen2.5-coder:7b"),
            "llm_temperature": agent_settings.get("agent.simple_crewai.llm_temperature", "0.2"),
            "ollama_base_url": agent_settings.get("agent.simple_crewai.ollama_base_url", "http://localhost:11434"),
            "openai_api_key_set": bool(agent_settings.get("agent.simple_crewai.openai_api_key", "")),
            "anthropic_api_key_set": bool(agent_settings.get("agent.simple_crewai.anthropic_api_key", "")),
        },
    )

    # Resolve agent classes (retry import if module-level failed)
    try:
        AgentCls, ConfigCls = _resolve_agent_classes()
    except ImportError:
        tb = traceback.format_exc()
        logger.error(
            "agent_import_failed",
            extra={"event": "agent_import_failed", "job_id": str(job.id), "traceback": tb},
        )
        return False, f"Failed to import simple_crewai_pair_agent: {tb}"

    try:
        config = ConfigCls(
            working_directory=work_dir,
            project_name=project_name,
            requirement=job.requirement,
            llm_provider=agent_settings.get("agent.simple_crewai.llm_provider", "ollama"),
            llm_model=agent_settings.get("agent.simple_crewai.llm_model", "qwen2.5-coder:7b"),
            llm_temperature=float(agent_settings.get("agent.simple_crewai.llm_temperature", "0.2")),
            ollama_base_url=agent_settings.get("agent.simple_crewai.ollama_base_url", "http://localhost:11434"),
            openai_api_key=agent_settings.get("agent.simple_crewai.openai_api_key", ""),
            anthropic_api_key=agent_settings.get("agent.simple_crewai.anthropic_api_key", ""),
        )
        result = AgentCls(config).run()

        error_msg = getattr(result, "error", None)
        if error_msg:
            logger.warning(
                "agent_returned_error",
                extra={"event": "agent_returned_error", "job_id": str(job.id), "error": error_msg},
            )
            return False, str(error_msg)

        logger.info(
            "agent_succeeded",
            extra={"event": "agent_succeeded", "job_id": str(job.id)},
        )
        return True, None

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "agent_exception",
            extra={
                "event": "agent_exception",
                "job_id": str(job.id),
                "error": str(exc),
                "traceback": tb,
            },
        )
        return False, str(exc)
