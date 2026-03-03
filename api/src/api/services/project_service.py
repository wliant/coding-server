from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.project import Project


async def list_named_projects(db: AsyncSession) -> list[Project]:
    """Return only projects where name IS NOT NULL and status='active', ordered by name."""
    result = await db.execute(
        select(Project)
        .where(Project.name.isnot(None))
        .where(Project.status == "active")
        .order_by(Project.name)
    )
    return list(result.scalars().all())


async def create_project(db: AsyncSession, source_type: str = "new") -> Project:
    """Insert a project with name=None and return the ORM object."""
    project = Project(name=None, source_type=source_type, status="active")
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project
