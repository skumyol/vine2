from fastapi import APIRouter, Request
from fastapi.routing import APIRoute


router = APIRouter(tags=["health"])


@router.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/routes")
def list_routes(request: Request) -> dict:
    """List all registered API routes for debugging."""
    routes = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name,
            })
    return {"routes": sorted(routes, key=lambda r: r["path"])}
