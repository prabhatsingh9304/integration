"""RawExternalObject entity - stores raw external payloads."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from app.domain.models.integration_account import IntegrationType
from app.domain.models.sync_cursor import ObjectType


@dataclass
class RawExternalObject:
    """
    Entity storing raw external payloads with no transformation.
    
    Rules:
    - No transformation applied
    - No business logic
    - Stored exactly as received from vendor
    - (integration_type, external_account_id, object_type, external_object_id) is unique
    """
    id: Optional[int]
    integration_type: IntegrationType
    external_account_id: str
    object_type: ObjectType
    external_object_id: str
    payload: Dict[str, Any]
    last_updated_time: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate invariants."""
        if not self.external_account_id:
            raise ValueError("external_account_id cannot be empty")
        if not self.external_object_id:
            raise ValueError("external_object_id cannot be empty")
        if not self.payload:
            raise ValueError("payload cannot be empty")
    
    def update_payload(self, new_payload: Dict[str, Any], last_updated_time: datetime) -> None:
        """
        Update object payload.
        
        Args:
            new_payload: New raw payload from vendor
            last_updated_time: Timestamp from vendor
        """
        self.payload = new_payload
        self.last_updated_time = last_updated_time
        self.updated_at = datetime.utcnow()
    
    def get_composite_key(self) -> tuple:
        """
        Get composite key for this object.
        
        Returns:
            Tuple of (integration_type, external_account_id, object_type, external_object_id)
        """
        return (
            self.integration_type.value,
            self.external_account_id,
            self.object_type.value,
            self.external_object_id
        )
