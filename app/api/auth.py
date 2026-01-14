"""OAuth authentication endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from temporalio.client import Client
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.domain.models.integration_account import (
    IntegrationAccount, IntegrationType, AccountStatus
)
from app.infrastructure.db.repositories.account_repository import (
    SQLAlchemyIntegrationAccountRepository
)
from app.infrastructure.integrations.quickbooks.oauth import QuickBooksOAuthClient
from app.temporal.workflows import IntegrationSyncWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class QuickBooksAuthRequest(BaseModel):
    """Request model for manual QuickBooks authorization."""
    authorization_code: str
    realm_id: str


@router.post("/quickbooks/connect")
async def quickbooks_connect(
    request: QuickBooksAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Connect QuickBooks account using authorization code and realm ID.
    
    This endpoint allows users to manually provide the authorization code
    and realm ID obtained from QuickBooks OAuth flow (e.g., from OAuth Playground).
    
    Args:
        request: Contains authorization_code and realm_id
        db: Database session
        
    Returns:
        Success message with account details and workflow information
    """
    # Exchange code for tokens
    oauth_client = QuickBooksOAuthClient()
    try:
        credentials = await oauth_client.exchange_code_for_tokens(request.authorization_code)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Token exchange failed: {str(e)}. Make sure the authorization code is valid and not expired."
        )
    
    # Save integration account
    account_repo = SQLAlchemyIntegrationAccountRepository(db)
    
    account = IntegrationAccount(
        id=None,
        integration_type=IntegrationType.QUICKBOOKS,
        external_account_id=request.realm_id,
        credentials=credentials,
        status=AccountStatus.ACTIVE
    )
    
    saved_account = account_repo.save(account)
    
    # Start Temporal workflow
    workflow_id = None
    workflow_started = False
    try:
        temporal_client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace
        )
        
        workflow_id = saved_account.get_workflow_id()
        
        await temporal_client.start_workflow(
            IntegrationSyncWorkflow.run,
            args=[
                IntegrationType.QUICKBOOKS.value,
                request.realm_id,
                settings.sync_interval_minutes
            ],
            id=workflow_id,
            task_queue=settings.temporal_task_queue
        )
        workflow_started = True
        logger.info(f"Started sync workflow {workflow_id}")
        
    except Exception as e:
        # Check if it's an "already started" error by string message if class is unavailable
        if "already start" in str(e).lower():
             logger.info(f"Workflow {workflow_id} already running")
             workflow_started = True
             workflow_id = saved_account.get_workflow_id()
        else:
            # Log error but don't fail the request
            logger.error(f"Failed to start workflow: {e}", exc_info=True)
    
    return {
        "message": "QuickBooks account connected successfully",
        "account_id": saved_account.id,
        "external_account_id": saved_account.external_account_id,
        "status": saved_account.status.value,
        "workflow_id": workflow_id,
        "workflow_started": workflow_started,
        "next_steps": {
            "view_workflow": f"http://localhost:8080/namespaces/default/workflows/{workflow_id}",
            "check_sync_status": f"http://localhost:8000/integrations/{saved_account.id}/status",
            "temporal_ui": "http://localhost:8080"
        }
    }
