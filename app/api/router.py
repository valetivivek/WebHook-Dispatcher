from fastapi import APIRouter

from app.api.webhooks import router as webhooks_router
from app.api.events import router as events_router

router = APIRouter()
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(events_router, prefix="/events", tags=["events"])
