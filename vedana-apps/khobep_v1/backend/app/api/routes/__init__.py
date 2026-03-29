from fastapi import APIRouter, FastAPI

from app.api.routes import dishes, health, imports, inventory, materials, ocr, orders, reports, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(materials.router, tags=["materials"])
    api_router.include_router(inventory.router, tags=["inventory"])
    api_router.include_router(imports.router, tags=["imports"])
    api_router.include_router(dishes.router, tags=["dishes"])
    api_router.include_router(ocr.router, tags=["ocr"])
    api_router.include_router(reports.router, tags=["reports"])
    api_router.include_router(orders.router, tags=["orders"])
    app.include_router(api_router)
