"""FastAPI application entry point."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, integration, health

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="QuickBooks Integration Platform",
    description="Production-grade integration platform using DDD, Hexagonal Architecture, and Temporal",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(integration.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting QuickBooks Integration Platform")
    logger.info(f"Environment: {settings.quickbooks_environment}")
    
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down QuickBooks Integration Platform")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "QuickBooks Integration Platform",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
