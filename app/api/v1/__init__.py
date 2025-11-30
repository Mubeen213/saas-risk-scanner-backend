from fastapi import APIRouter

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.integration_routes import router as integration_router
from app.api.v1.workspace_routes import router as workspace_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(integration_router)
api_v1_router.include_router(workspace_router)
