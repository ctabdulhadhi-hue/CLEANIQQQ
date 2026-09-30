from fastapi import APIRouter
from app.core.session_store import session_store

router = APIRouter(tags=["Health"])

APP_NAME = "CleanIQ API"
VERSION = "1.0.0"


@router.get("/")
@router.get("/health")
@router.get("/api/health")
async def health():
    """
    Lightweight health and operational readiness probe.
    Returns service metadata and active in-memory session count.
    """
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": VERSION,
        "active_sessions": len(session_store.list_active_dataset_ids()),
    }

