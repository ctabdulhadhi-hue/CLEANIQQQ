from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/")
@router.get("/health")
@router.get("/api/health")
async def health():
    return {"status": "ok"}

