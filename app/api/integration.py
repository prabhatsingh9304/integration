"""Integration management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
import uuid
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
    id: uuid.UUID
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
async def get_sync_status(account_id: uuid.UUID, db: Session = Depends(get_db)):
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
