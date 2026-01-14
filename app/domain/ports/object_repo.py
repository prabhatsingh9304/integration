"""RawExternalObject repository port interface."""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models.integration_account import IntegrationType
from app.domain.models.raw_external_object import RawExternalObject
from app.domain.models.sync_cursor import ObjectType


class RawExternalObjectRepository(ABC):
    """Repository interface for RawExternalObject entity."""
    
    @abstractmethod
    def save(self, obj: RawExternalObject) -> RawExternalObject:
        """
        Save or update a raw external object (UPSERT).
        
        Args:
            obj: RawExternalObject to save
            
        Returns:
            Saved object with updated ID
        """
        pass
    
    @abstractmethod
    def save_batch(self, objects: list[RawExternalObject]) -> list[RawExternalObject]:
        """
        Save multiple objects in a batch (UPSERT).
        
        Args:
            objects: List of RawExternalObject to save
            
        Returns:
            List of saved objects
        """
        pass
    
    @abstractmethod
    def find_by_composite_key(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType,
        external_object_id: str
    ) -> Optional[RawExternalObject]:
        """
        Find object by composite key.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account identifier
            object_type: Type of object
            external_object_id: External object identifier
            
        Returns:
            RawExternalObject if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_by_account_and_type(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType,
        limit: Optional[int] = None
    ) -> list[RawExternalObject]:
        """
        List objects by account and type.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account identifier
            object_type: Type of object
            limit: Optional limit on number of results
            
        Returns:
            List of objects
        """
        pass
