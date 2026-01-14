"""SyncCursor repository port interface."""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.integration_account import IntegrationType
from app.domain.models.sync_cursor import ObjectType, SyncCursor


class SyncCursorRepository(ABC):
    """Repository interface for SyncCursor entity."""
    
    @abstractmethod
    def save(self, cursor: SyncCursor) -> SyncCursor:
        """
        Save or update a sync cursor (UPSERT).
        
        Args:
            cursor: SyncCursor to save
            
        Returns:
            Saved cursor with updated ID
        """
        pass
    
    @abstractmethod
    def find_by_composite_key(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType
    ) -> Optional[SyncCursor]:
        """
        Find cursor by composite key.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account identifier
            object_type: Type of object being synced
            
        Returns:
            SyncCursor if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_by_account(
        self,
        integration_type: IntegrationType,
        external_account_id: str
    ) -> list[SyncCursor]:
        """
        List all cursors for an account.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account identifier
            
        Returns:
            List of cursors for the account
        """
        pass
