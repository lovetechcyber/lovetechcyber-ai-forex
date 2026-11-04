
from fastapi import APIRouter, Response, status

from app.db.mongo import check_database_health


router = APIRouter(tags=["Health"])


@router.get("/live", include_in_schema=False)
async def liveness():
    # Confirms the API process is running.
    return {"status": "alive"}


@router.get("/ready", include_in_schema=False)
async def readiness(response: Response):
    # Confirms the API can reach its database.
    if not await check_database_health():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}

    return {"status": "ready"}
