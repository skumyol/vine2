from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
