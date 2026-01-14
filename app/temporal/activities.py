"""Temporal activities - idempotent, retriable operations."""
import logging
from temporalio import activity

from app.core.database import SessionLocal
from app.domain.models.integration_account import IntegrationType
from app.infrastructure.db.repositories.account_repository import (
    SQLAlchemyIntegrationAccountRepository
)
from app.infrastructure.db.repositories.cursor_repository import (
    SQLAlchemySyncCursorRepository
)
from app.infrastructure.db.repositories.quickbooks_repository import (
    SQLAlchemyQuickBooksRepository
)
from app.application.services.run_integration_sync import RunIntegrationSyncService

logger = logging.getLogger(__name__)


@activity.defn
async def run_integration_sync(integration_type: str, external_account_id: str) -> dict:
    """
    Activity to run integration sync.
    
    This activity is idempotent and can be safely retried.
    
    Args:
        integration_type: Type of integration
        external_account_id: External account ID
        
    Returns:
        Sync results summary
    """
    activity.logger.info(
        f"Running sync activity for {integration_type} account {external_account_id}"
    )
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Wire up repositories
        account_repo = SQLAlchemyIntegrationAccountRepository(db)
        cursor_repo = SQLAlchemySyncCursorRepository(db)
        quickbooks_repo = SQLAlchemyQuickBooksRepository(db)
        
        # Create service
        sync_service = RunIntegrationSyncService(
            account_repo, cursor_repo, quickbooks_repo
        )
        
        # Run sync
        integration_type_enum = IntegrationType(integration_type)
        results = await sync_service.run_sync(integration_type_enum, external_account_id)
        
        activity.logger.info(f"Sync completed: {results}")
        return results
        
    except Exception as e:
        activity.logger.error(f"Sync failed: {str(e)}")
        raise
    finally:
        db.close()
