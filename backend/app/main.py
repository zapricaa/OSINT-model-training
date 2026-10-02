"""ZAPRICA — Enterprise AI OSINT Platform.

Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.database import engine, Base

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("zaprica")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("ZAPRICA starting up...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    await engine.dispose()
    logger.info("ZAPRICA shut down")


# Create the application
app = FastAPI(
    title="ZAPRICA",
    description="Enterprise AI OSINT Investigation Platform",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        },
    )


# Register routers
from app.api.auth_routes import router as auth_router
from app.api.case_routes import router as case_router
from app.api.investigation_routes import router as investigation_router
from app.api.graph_routes import router as graph_router

app.include_router(auth_router)
app.include_router(case_router)
app.include_router(investigation_router)
app.include_router(graph_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "zaprica-backend",
        "version": settings.app_version,
    }


@app.get("/api/v1/status")
async def system_status():
    """System status with version and configuration info."""
    return {
        "service": "ZAPRICA",
        "version": settings.app_version,
        "environment": settings.environment,
        "features": {
            "planner_llm": settings.planner_llm_provider,
            "extractor_llm": settings.extractor_llm_provider,
            "max_concurrent_investigations": settings.max_concurrent_investigations,
        },
    }
