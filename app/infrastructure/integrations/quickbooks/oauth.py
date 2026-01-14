"""QuickBooks OAuth 2.0 implementation."""
import base64
from datetime import datetime, timedelta
from typing import Dict, Any
import httpx

from app.core.config import settings
from app.domain.models.integration_account import Credentials
from app.domain.services.credential_policy import CredentialPolicy


class QuickBooksOAuthClient:
    """
    QuickBooks OAuth 2.0 client.
    
    Handles authorization flow and token management.
    """
    
    SCOPES = "com.intuit.quickbooks.accounting"
    
    def __init__(self):
        """Initialize OAuth client with settings."""
        self.client_id = settings.quickbooks_client_id
        self.client_secret = settings.quickbooks_client_secret
        self.redirect_uri = settings.quickbooks_redirect_uri
        self.auth_url = settings.quickbooks_auth_url
        self.token_url = settings.quickbooks_token_url
    
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Credentials:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Authorization code from OAuth callback
            
        Returns:
            Credentials object with tokens
            
        Raises:
            httpx.HTTPError: If token exchange fails
        """
        auth_header = self._get_auth_header()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": self.redirect_uri
                }
            )
            response.raise_for_status()
            token_data = response.json()
        
        return self._parse_token_response(token_data)
    
    async def refresh_access_token(self, refresh_token: str) -> Credentials:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            New credentials with refreshed tokens
            
        Raises:
            httpx.HTTPError: If token refresh fails
        """
        auth_header = self._get_auth_header()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            response.raise_for_status()
            token_data = response.json()
        
        return self._parse_token_response(token_data)
    
    def _get_auth_header(self) -> str:
        """Generate Basic Auth header for token requests."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _parse_token_response(self, token_data: Dict[str, Any]) -> Credentials:
        """
        Parse token response into Credentials object.
        
        Args:
            token_data: Token response from QuickBooks
            
        Returns:
            Credentials object
        """
        expires_at = CredentialPolicy.calculate_expiry_time(
            token_data.get("expires_in", 3600)
        )
        
        return Credentials(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            token_type=token_data.get("token_type", "Bearer")
        )
