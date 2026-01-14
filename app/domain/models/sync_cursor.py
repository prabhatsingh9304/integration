"""SyncCursor entity - tracks incremental sync progress."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.domain.models.integration_account import IntegrationType


class ObjectType(str, Enum):
    """Supported external object types."""
    CUSTOMER = "customer"
    INVOICE = "invoice"


class SyncStatus(str, Enum):
    """Sync operation status."""
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"


@dataclass
class SyncCursor:
    """
    Entity tracking incremental sync progress per account and object type.
    
    Invariants:
    - cursor is monotonic (never moves backward)
    - cursor advances only after successful persistence
    - (integration_type, external_account_id, object_type) is unique
    """
    id: Optional[int]
    integration_type: IntegrationType
    external_account_id: str
    object_type: ObjectType
    last_synced_at: Optional[datetime]
    last_attempt_at: datetime
    status: SyncStatus
    cursor_data: Optional[dict] = None
    error_message: Optional[str] = None
    records_synced: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate invariants."""
        if not self.external_account_id:
            raise ValueError("external_account_id cannot be empty")
    
    def advance_cursor(
        self,
        new_timestamp: datetime,
        records_count: int,
        cursor_data: Optional[dict] = None
    ) -> None:
        """
        Advance cursor after successful sync.
        
        Args:
            new_timestamp: New cursor position
            records_count: Number of records synced
            cursor_data: Optional granular cursor data (e.g. next page token)
            
        Raises:
            ValueError: If trying to move cursor backward
        """
        # Normalize to naive UTC if timezone aware
        if new_timestamp.tzinfo is not None:
             new_timestamp = new_timestamp.astimezone(timezone.utc).replace(tzinfo=None)

        # Enforce monotonic cursor
        if self.last_synced_at:
             # Ensure last_synced_at is also naive UTC (it should be if coming from DB, but for safety)
             last_synced_at = self.last_synced_at
             if last_synced_at.tzinfo is not None:
                  last_synced_at = last_synced_at.astimezone(timezone.utc).replace(tzinfo=None)
            
             if new_timestamp < last_synced_at:
                raise ValueError(
                    f"Cannot move cursor backward: {new_timestamp} < {last_synced_at}"
                )
        
        self.last_synced_at = new_timestamp
        self.last_attempt_at = datetime.utcnow()
        self.status = SyncStatus.SUCCESS
        self.cursor_data = cursor_data
        self.error_message = None
        self.records_synced += records_count
        self.updated_at = datetime.utcnow()
    
    def mark_attempt(self) -> None:
        """Mark sync attempt started."""
        self.last_attempt_at = datetime.utcnow()
        self.status = SyncStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
    
    def mark_failure(self, error_message: str, cursor_data: Optional[dict] = None) -> None:
        """
        Mark sync attempt as failed.
        
        Args:
            error_message: Error description
            cursor_data: Optional granular cursor data to resume from
        """
        self.last_attempt_at = datetime.utcnow()
        self.status = SyncStatus.FAILURE
        if cursor_data:
            self.cursor_data = cursor_data
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
    
    def get_cursor_value(self) -> Optional[datetime]:
        """
        Get current cursor value for incremental queries.
        
        Returns:
            Last successfully synced timestamp, or None for initial sync
        """
        return self.last_synced_at
