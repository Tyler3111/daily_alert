"""API route definitions."""

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import JobOut, RefreshResponse, StatsResponse
from src.jobs.database import JobDatabase
from src.jobs.filters import FilterEngine
router = APIRouter()


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs() -> list[JobOut]:
    """Return a placeholder list of jobs."""
    db = JobDatabase()
    filters = FilterEngine()
    
    jobs = db.get_recent_jobs()
    filtered = filters.apply_filters(jobs, location, experience, language)
    
    return {"jobs": filtered[:limit], "total": len(filtered)}
    return []


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: int) -> JobOut:
    """Return a placeholder job or 404 when not found."""

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job with id {job_id} not found.",
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_jobs() -> RefreshResponse:
    """Trigger a placeholder refresh action."""

    return RefreshResponse(success=True, message="Refresh triggered.")


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Return placeholder dashboard statistics."""

    return StatsResponse(total_jobs=0, total_matches=0, last_refresh=None)
