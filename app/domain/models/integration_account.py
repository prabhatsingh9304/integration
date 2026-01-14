"""IntegrationAccount aggregate root - represents a connected external account."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class IntegrationType(str, Enum):
    """Supported integration types."""
    QUICKBOOKS = "quickbooks"


class AccountStatus(str, Enum):
    """Integration account status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class Credentials:
    """OAuth credentials value object."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "Bearer"
    
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return datetime.utcnow() >= self.expires_at
    
    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        """
        Check if token needs refresh with buffer time.
        
        Args:
            buffer_minutes: Refresh buffer in minutes before actual expiry
        """
        from datetime import timedelta
        buffer_time = self.expires_at - timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= buffer_time


@dataclass
class IntegrationAccount:
    """
    Aggregate root representing one connected external account.
    
    Invariants:
    - (integration_type, external_account_id) must be unique
    - credentials must be refreshed before expiry
    - only one sync workflow per integration account
    """
    id: Optional[int]
    integration_type: IntegrationType
    external_account_id: str
    credentials: Credentials
    status: AccountStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate invariants."""
        if not self.external_account_id:
            raise ValueError("external_account_id cannot be empty")
        if not self.credentials.access_token:
            raise ValueError("access_token cannot be empty")
        if not self.credentials.refresh_token:
            raise ValueError("refresh_token cannot be empty")
    
    def update_credentials(self, credentials: Credentials) -> None:
        """
        Update account credentials.
        
        Args:
            credentials: New credentials to store
        """
        self.credentials = credentials
        self.updated_at = datetime.utcnow()
        
        # Update status based on credential state
        if credentials.is_expired():
            self.status = AccountStatus.EXPIRED
        else:
            self.status = AccountStatus.ACTIVE
    
    def mark_error(self) -> None:
        """Mark account as having an error."""
        self.status = AccountStatus.ERROR
        self.updated_at = datetime.utcnow()
    
    def mark_disconnected(self) -> None:
        """Mark account as disconnected."""
        self.status = AccountStatus.DISCONNECTED
        self.updated_at = datetime.utcnow()
    
    def get_workflow_id(self) -> str:
        """
        Get unique workflow ID for this integration account.
        
        Returns:
            Unique workflow identifier
        """
        return f"{self.integration_type.value}-{self.external_account_id}"
