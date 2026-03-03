import pytest
from api.models.project import Project
from api.services import project_service


async def test_list_named_projects_returns_only_named(db_session):
    """list_named_projects should return only projects where name IS NOT NULL."""
    # Create a project with a name
    named_project = Project(name="My Project", source_type="new", status="active")
    db_session.add(named_project)
    # Create a project without a name
    unnamed_project = Project(name=None, source_type="new", status="active")
    db_session.add(unnamed_project)
    await db_session.commit()

    result = await project_service.list_named_projects(db_session)

    assert len(result) == 1
    assert result[0].name == "My Project"


async def test_list_named_projects_empty_when_none(db_session):
    """list_named_projects returns empty list when no named projects exist."""
    result = await project_service.list_named_projects(db_session)
    assert result == []


async def test_create_project_inserts_with_null_name(db_session):
    """create_project should insert a project with name=None."""
    project = await project_service.create_project(db_session, source_type="new")

    assert project.id is not None
    assert project.name is None
    assert project.source_type == "new"
    assert project.status == "active"


async def test_create_project_with_different_source_type(db_session):
    """create_project respects the source_type parameter."""
    project = await project_service.create_project(db_session, source_type="existing")

    assert project.source_type == "existing"
