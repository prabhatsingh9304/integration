"""Core configuration module using Pydantic Settings."""
from typing import Literal
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    database_url: PostgresDsn = Field(
        default="postgresql://integration_user:integration_pass@localhost:5432/integration_db",
        description="PostgreSQL connection string"
    )
    
    quickbooks_client_id: str = Field(
        default="",
        description="QuickBooks Client ID"
    )
    
    quickbooks_client_secret: str = Field(
        default="",
        description="QuickBooks Client Secret"
    )
    
    quickbooks_redirect_uri: str = Field(
        default="http://localhost:8000/auth/quickbooks/callback",
        description="OAuth callback URL"
    )
    quickbooks_environment: Literal["sandbox", "production"] = Field(
        default="sandbox",
        description="QuickBooks environment"
    )
    
    temporal_host: str = Field(
        default="localhost:7233",
        description="Temporal server host"
    )
    temporal_namespace: str = Field(
        default="default",
        description="Temporal namespace"
    )
    temporal_task_queue: str = Field(
        default="integration-sync-queue",
        description="Temporal task queue name"
    )
    
    sync_interval_minutes: int = Field(
        default=5,
        description="Sync interval in minutes"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    
    @property
    def quickbooks_auth_url(self) -> str:
        """Get QuickBooks authorization URL base."""
        if self.quickbooks_environment == "production":
            return "https://appcenter.intuit.com/connect/oauth2"
        return "https://appcenter.intuit.com/connect/oauth2"
    
    @property
    def quickbooks_token_url(self) -> str:
        """Get QuickBooks token endpoint URL."""
        return "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    
    @property
    def quickbooks_api_base_url(self) -> str:
        """Get QuickBooks API base URL."""
        if self.quickbooks_environment == "production":
            return "https://quickbooks.api.intuit.com"
        return "https://sandbox-quickbooks.api.intuit.com"


settings = Settings()
