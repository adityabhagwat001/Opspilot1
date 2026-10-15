"""
OpsPilot Enterprise AI Operations Platform - FastAPI Application
"""

import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import init_system_db
from app.api import auth, dashboard, chat, approvals, integrations, audit, github_ops

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed baseline users & connections
    await init_system_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Agentic AI Platform with FastMCP, PostgreSQL, GitHub, and Mandatory Write Approval",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(github_ops.router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "platform": "OpsPilot",
        "environment": settings.ENVIRONMENT,
        "mcp_active": True
    }

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
