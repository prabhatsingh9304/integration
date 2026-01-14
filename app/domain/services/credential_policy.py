"""Credential policy domain service - manages credential lifecycle rules."""
from datetime import datetime, timedelta

from app.domain.models.integration_account import Credentials, IntegrationAccount


class CredentialPolicy:
    """
    Domain service for credential expiration and refresh policies.
    
    This is pure business logic with no infrastructure dependencies.
    """
    
    DEFAULT_REFRESH_BUFFER_MINUTES = 5
    
    @staticmethod
    def should_refresh_credentials(
        account: IntegrationAccount,
        buffer_minutes: int = DEFAULT_REFRESH_BUFFER_MINUTES
    ) -> bool:
        """
        Determine if credentials should be refreshed.
        
        Args:
            account: Integration account to check
            buffer_minutes: Buffer time before expiry to trigger refresh
            
        Returns:
            True if credentials should be refreshed
        """
        return account.credentials.needs_refresh(buffer_minutes)
    
    @staticmethod
    def is_token_expired(credentials: Credentials) -> bool:
        """
        Check if access token is expired.
        
        Args:
            credentials: Credentials to check
            
        Returns:
            True if token is expired
        """
        return credentials.is_expired()
    
    @staticmethod
    def calculate_expiry_time(expires_in_seconds: int) -> datetime:
        """
        Calculate expiry timestamp from expires_in value.
        
        Args:
            expires_in_seconds: Seconds until expiry
            
        Returns:
            Absolute expiry timestamp
        """
        return datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    
    @staticmethod
    def validate_credentials(credentials: Credentials) -> bool:
        """
        Validate that credentials are complete and valid.
        
        Args:
            credentials: Credentials to validate
            
        Returns:
            True if credentials are valid
        """
        if not credentials.access_token:
            return False
        if not credentials.refresh_token:
            return False
        if not credentials.expires_at:
            return False
        return True
