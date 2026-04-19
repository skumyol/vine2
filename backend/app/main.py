from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes_analyze import router as analyze_router
from backend.app.api.routes_batch import router as batch_router
from backend.app.api.routes_health import router as health_router
from backend.app.api.routes_ocr import router as ocr_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VinoBuzz Photo Verification Backend",
        version="0.1.0",
        debug=settings.debug,
    )
    # Parse CORS origins from env var (comma-separated)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analyze_router, prefix="/api")
    app.include_router(batch_router, prefix="/api")
    app.include_router(ocr_router, prefix="/api")
    return app


app = create_app()
