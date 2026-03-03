import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID):
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: uuid.UUID):
    return []
