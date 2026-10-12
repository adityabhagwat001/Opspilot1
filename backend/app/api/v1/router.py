from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, nodes

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health & Diagnostics"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Access"])
api_router.include_router(nodes.router, prefix="/nodes", tags=["Managed Infrastructure Nodes"])
