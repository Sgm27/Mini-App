from fastapi import APIRouter, FastAPI

from app.api.routes import health, inventory, menu, orders, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(menu.router)
    api_router.include_router(inventory.router)
    api_router.include_router(orders.router)
    app.include_router(api_router)

