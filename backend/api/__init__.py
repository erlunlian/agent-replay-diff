from fastapi import APIRouter

from api.runs import router as runs_router

router = APIRouter()

router.include_router(runs_router, prefix="/runs", tags=["runs"])
