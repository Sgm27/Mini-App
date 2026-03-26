from fastapi import APIRouter, FastAPI

from app.api.routes import checkins, health, ocr, room_assignments, rooms, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(ocr.router, tags=["ocr"])
    api_router.include_router(checkins.router, tags=["checkins"])
    api_router.include_router(rooms.router, tags=["rooms"])
    api_router.include_router(room_assignments.router, tags=["room-assignments"])
    app.include_router(api_router)
