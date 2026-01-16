"""IntegrationAccount repository port interface."""
from abc import ABC, abstractmethod
from typing import Optional
import uuid

from app.domain.models.integration_account import IntegrationAccount, IntegrationType


class IntegrationAccountRepository(ABC):
    """Repository interface for IntegrationAccount aggregate."""
    
    @abstractmethod
    def save(self, account: IntegrationAccount) -> IntegrationAccount:
        """
        Save or update an integration account.
        
        Args:
            account: IntegrationAccount to save
            
        Returns:
            Saved account with updated ID
        """
        pass
    
    @abstractmethod
    def find_by_id(self, account_id: uuid.UUID) -> Optional[IntegrationAccount]:
        """
        Find account by ID.
        
        Args:
            account_id: Account ID
            
        Returns:
            IntegrationAccount if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_external_id(
        self,
        integration_type: IntegrationType,
        external_account_id: str
    ) -> Optional[IntegrationAccount]:
        """
        Find account by integration type and external account ID.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account identifier
            
        Returns:
            IntegrationAccount if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_all(self) -> list[IntegrationAccount]:
        """
        List all integration accounts.
        
        Returns:
            List of all accounts
        """
        pass
    
    @abstractmethod
    def delete(self, account_id: uuid.UUID) -> bool:
        """
        Delete an integration account.
        
        Args:
            account_id: Account ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
