"""Run integration sync application service."""
import logging
from typing import List

from app.domain.models.integration_account import IntegrationAccount, IntegrationType
from app.domain.models.sync_cursor import ObjectType
from app.domain.ports.account_repo import IntegrationAccountRepository
from app.domain.ports.cursor_repo import SyncCursorRepository
from app.domain.services.credential_policy import CredentialPolicy
from app.domain.ports.object_repo import RawExternalObjectRepository
from app.infrastructure.integrations.quickbooks.client import QuickBooksAPIClient
from app.infrastructure.integrations.quickbooks.oauth import QuickBooksOAuthClient
from app.application.services.sync_external_objects import SyncExternalObjectsService

logger = logging.getLogger(__name__)


class RunIntegrationSyncService:
    """
    High-level orchestration service for running integration sync.
    
    Responsibilities:
    - Coordinate sync across multiple object types
    - Handle credential refresh
    - Error handling and recovery
    """
    
    # Object types to sync for QuickBooks
    QUICKBOOKS_OBJECT_TYPES = [ObjectType.CUSTOMER, ObjectType.INVOICE]
    
    def __init__(
        self,
        account_repo: IntegrationAccountRepository,
        cursor_repo: SyncCursorRepository,
        object_repo: RawExternalObjectRepository
    ):
        """
        Initialize service with repositories.
        
        Args:
            account_repo: Account repository
            cursor_repo: Cursor repository
            object_repo: Object repository
        """
        self.account_repo = account_repo
        self.cursor_repo = cursor_repo
        self.sync_service = SyncExternalObjectsService(cursor_repo, object_repo)
    
    async def run_sync(
        self,
        integration_type: IntegrationType,
        external_account_id: str
    ) -> dict:
        """
        Run sync for an integration account.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account ID
            
        Returns:
            Sync results summary
            
        Raises:
            ValueError: If account not found
            Exception: If sync fails
        """
        logger.info(f"Running sync for {integration_type.value} account {external_account_id}")
        
        account = self.account_repo.find_by_external_id(integration_type, external_account_id)
        if not account:
            raise ValueError(f"Account not found: {integration_type.value}/{external_account_id}")
        
        # Refresh credentials if needed
        await self._ensure_valid_credentials(account)
        
        # Get object types to sync
        object_types = self._get_object_types_for_integration(integration_type)
        
        results = {}
        for object_type in object_types:
            try:
                sync_result = await self._sync_object_type(account, object_type)
                results[object_type.value] = {
                    "status": "success", 
                    "count": sync_result.get("count", 0),
                    "has_more": sync_result.get("has_more", False)
                }
            except Exception as e:
                logger.error(f"Failed to sync {object_type.value}: {str(e)}")
                results[object_type.value] = {"status": "error", "error": str(e)}
        
        return results
    
    async def _ensure_valid_credentials(self, account: IntegrationAccount) -> None:
        """
        Ensure account has valid credentials, refresh if needed.
        
        Args:
            account: Integration account
        """
        if CredentialPolicy.should_refresh_credentials(account):
            logger.info(f"Refreshing credentials for account {account.external_account_id}")
            
            if account.integration_type == IntegrationType.QUICKBOOKS:
                oauth_client = QuickBooksOAuthClient()
                new_credentials = await oauth_client.refresh_access_token(
                    account.credentials.refresh_token
                )
                account.update_credentials(new_credentials)
                self.account_repo.save(account)
                logger.info("Credentials refreshed successfully")
            else:
                raise ValueError(f"Unsupported integration type: {account.integration_type}")
    
    async def _sync_object_type(
        self,
        account: IntegrationAccount,
        object_type: ObjectType
    ) -> dict:
        """
        Sync a specific object type.
        
        Args:
            account: Integration account
            object_type: Type of object to sync
            
        Returns:
            Sync result dictionary
        """
        if account.integration_type == IntegrationType.QUICKBOOKS:
            api_client = QuickBooksAPIClient(
                realm_id=account.external_account_id,
                access_token=account.credentials.access_token
            )
            
            return await self.sync_service.sync_quickbooks_objects(
                account.integration_type,
                account.external_account_id,
                object_type,
                api_client
            )
        else:
            raise ValueError(f"Unsupported integration type: {account.integration_type}")
    
    def _get_object_types_for_integration(
        self,
        integration_type: IntegrationType
    ) -> List[ObjectType]:
        """
        Get list of object types to sync for an integration.
        
        Args:
            integration_type: Type of integration
            
        Returns:
            List of object types
        """
        if integration_type == IntegrationType.QUICKBOOKS:
            return self.QUICKBOOKS_OBJECT_TYPES
        else:
            raise ValueError(f"Unsupported integration type: {integration_type}")
