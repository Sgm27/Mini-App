from fastapi import APIRouter, FastAPI

from app.api.routes import health, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    app.include_router(api_router)

