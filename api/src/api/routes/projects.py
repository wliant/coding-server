import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/projects")
async def list_projects():
    return []


@router.post("/projects", status_code=501)
async def create_project():
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.get("/projects/{project_id}")
async def get_project(project_id: uuid.UUID):
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@router.get("/projects/{project_id}/jobs")
async def list_project_jobs(project_id: uuid.UUID):
    return []


@router.post("/projects/{project_id}/jobs", status_code=501)
async def create_job(project_id: uuid.UUID):
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})
