"""Agent invocation for the worker.

Wraps simple_crewai_pair_agent.CodingAgent to:
  - Create the isolated working directory
  - Insert a WorkDirectory DB record
  - Return (success, error_message) tuple
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from worker.models import Job, Project, WorkDirectory

logger = logging.getLogger(__name__)

# Late import to avoid hard failure if agent package not installed at test time
try:
    from simple_crewai_pair_agent import CodingAgent, CodingAgentConfig
except ImportError:  # pragma: no cover
    CodingAgent = None  # type: ignore[assignment, misc]
    CodingAgentConfig = None  # type: ignore[assignment, misc]


async def run_coding_agent(
    db: AsyncSession,
    job: Job,
    project: Project,
    settings,
) -> tuple[bool, str | None]:
    """Run the coding agent for the given job.

    1. Derives work_dir = Path(settings.AGENT_WORK_PARENT) / str(job.id)
    2. Creates a WorkDirectory DB record
    3. Invokes CodingAgent(CodingAgentConfig(...)).run()
    4. Returns (True, None) on success, (False, error_message) on failure

    Any exception from the agent is caught and returned as an error result.
    """
    work_dir = Path(settings.AGENT_WORK_PARENT) / str(job.id)
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
        },
    )

    try:
        config = CodingAgentConfig(
            working_directory=work_dir,
            project_name=project_name,
            requirement=job.requirement,
            llm_provider=settings.LLM_PROVIDER,
            llm_model=settings.LLM_MODEL,
            llm_temperature=settings.LLM_TEMPERATURE,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            openai_api_key=settings.OPENAI_API_KEY,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
        )
        result = CodingAgent(config).run()

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
        error_msg = str(exc)
        logger.error(
            "agent_exception",
            extra={"event": "agent_exception", "job_id": str(job.id), "error": error_msg},
        )
        return False, error_msg
