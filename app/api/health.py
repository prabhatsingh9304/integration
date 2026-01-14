"""Health check endpoints."""
from fastapi import APIRouter
from sqlalchemy import text
from temporalio.client import Client

from app.core.config import settings
from app.core.database import SessionLocal

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Basic health check.
    
    Returns:
        Health status
    """
    return {"status": "healthy"}


@router.get("/db")
async def database_health():
    """
    Check database connectivity.
    
    Returns:
        Database health status
    """
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
    finally:
        db.close()


@router.get("/temporal")
async def temporal_health():
    """
    Check Temporal connectivity.
    
    Returns:
        Temporal health status
    """
    try:
        client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace
        )
        return {"status": "healthy", "temporal": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "temporal": "disconnected", "error": str(e)}
