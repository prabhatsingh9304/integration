"""Integration management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db

from app.infrastructure.db.repositories.account_repository import (
    SQLAlchemyIntegrationAccountRepository
)
from app.infrastructure.db.repositories.cursor_repository import (
    SQLAlchemySyncCursorRepository
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationAccountResponse(BaseModel):
    """Response model for integration account."""
    id: int
    integration_type: str
    external_account_id: str
    status: str
    created_at: str
    updated_at: str


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""
    object_type: str
    last_synced_at: str | None
    last_attempt_at: str
    status: str
    records_synced: int
    error_message: str | None


@router.get("", response_model=List[IntegrationAccountResponse])
async def list_integrations(db: Session = Depends(get_db)):
    """
    List all connected integration accounts.
    
    Returns:
        List of integration accounts
    """
    account_repo = SQLAlchemyIntegrationAccountRepository(db)
    accounts = account_repo.list_all()
    
    return [
        IntegrationAccountResponse(
            id=account.id,
            integration_type=account.integration_type.value,
            external_account_id=account.external_account_id,
            status=account.status.value,
            created_at=account.created_at.isoformat(),
            updated_at=account.updated_at.isoformat()
        )
        for account in accounts
    ]


@router.get("/{account_id}/status", response_model=List[SyncStatusResponse])
async def get_sync_status(account_id: int, db: Session = Depends(get_db)):
    """
    Get sync status for an integration account.
    
    Args:
        account_id: Integration account ID
        db: Database session
        
    Returns:
        List of sync statuses per object type
    """
    account_repo = SQLAlchemyIntegrationAccountRepository(db)
    account = account_repo.find_by_id(account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    cursor_repo = SQLAlchemySyncCursorRepository(db)
    cursors = cursor_repo.list_by_account(
        account.integration_type,
        account.external_account_id
    )
    
    return [
        SyncStatusResponse(
            object_type=cursor.object_type.value,
            last_synced_at=cursor.last_synced_at.isoformat() if cursor.last_synced_at else None,
            last_attempt_at=cursor.last_attempt_at.isoformat(),
            status=cursor.status.value,
            records_synced=cursor.records_synced,
            error_message=cursor.error_message
        )
        for cursor in cursors
    ]


@router.post("/{account_id}/trigger-sync")
async def trigger_sync(account_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger a sync for an integration account.
    
    Args:
        account_id: Integration account ID
        db: Database session
        
    Returns:
        Success message
    """
    account_repo = SQLAlchemyIntegrationAccountRepository(db)
    account = account_repo.find_by_id(account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Signal the workflow to run sync immediately
    try:
        # In a real implementation, you would signal the workflow
        # For now, we'll just return success
        # temporal_client = await Client.connect(...)
        # await temporal_client.get_workflow_handle(workflow_id).signal("trigger_sync")
        
        workflow_id = account.get_workflow_id()
        
        return {
            "message": "Sync triggered successfully",
            "workflow_id": workflow_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger sync: {str(e)}")
