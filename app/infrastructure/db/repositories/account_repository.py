"""IntegrationAccount repository implementation using SQLAlchemy."""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.models.integration_account import (
    IntegrationAccount, IntegrationType, AccountStatus, Credentials
)
from app.domain.ports.account_repo import IntegrationAccountRepository
from app.infrastructure.db.models import QuickBooksAccountModel


class SQLAlchemyIntegrationAccountRepository(IntegrationAccountRepository):
    """SQLAlchemy implementation of IntegrationAccountRepository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def _get_model(self, integration_type: IntegrationType):
        """Get the SQLAlchemy model class for the integration type."""
        if integration_type == IntegrationType.QUICKBOOKS:
            return QuickBooksAccountModel
        raise ValueError(f"Unsupported integration type: {integration_type}")

    def save(self, account: IntegrationAccount) -> IntegrationAccount:
        """Save or update an integration account."""
        ModelClass = self._get_model(account.integration_type)
        
        # Check if account exists by external ID
        
        db_account = self.session.query(ModelClass).filter_by(
            external_account_id=account.external_account_id
        ).first()
        
        if db_account:
            db_account.access_token = account.credentials.access_token
            db_account.refresh_token = account.credentials.refresh_token
            db_account.token_expires_at = account.credentials.expires_at
            db_account.token_type = account.credentials.token_type
            db_account.status = account.status
            db_account.updated_at = account.updated_at
        else:
            db_account = ModelClass(
                external_account_id=account.external_account_id,
                access_token=account.credentials.access_token,
                refresh_token=account.credentials.refresh_token,
                token_expires_at=account.credentials.expires_at,
                token_type=account.credentials.token_type,
                status=account.status,
                created_at=account.created_at,
                updated_at=account.updated_at
            )
            self.session.add(db_account)
        
        self.session.commit()
        self.session.refresh(db_account)
        
        return self._to_domain(db_account, account.integration_type)
    
    def find_by_id(self, account_id: int) -> Optional[IntegrationAccount]:
        """
        Find account by ID.
        WARNING: ID is not unique across integrations with separate schemas.
        This naive implementation only checks QuickBooks.
        """
        # TODO: Handle multi-integration lookup if needed. 
        # For now, default to QuickBooks as it's the only one.
        db_account = self.session.query(QuickBooksAccountModel).filter_by(id=account_id).first()
        return self._to_domain(db_account, IntegrationType.QUICKBOOKS) if db_account else None
    
    def find_by_external_id(
        self,
        integration_type: IntegrationType,
        external_account_id: str
    ) -> Optional[IntegrationAccount]:
        """Find account by integration type and external account ID."""
        ModelClass = self._get_model(integration_type)
        
        db_account = self.session.query(ModelClass).filter_by(
            external_account_id=external_account_id
        ).first()
        
        return self._to_domain(db_account, integration_type) if db_account else None
    
    def list_all(self) -> list[IntegrationAccount]:
        """List all integration accounts (across all integrations)."""
        # Dictionary of Type -> Model
        models = [
            (IntegrationType.QUICKBOOKS, QuickBooksAccountModel)
        ]
        
        accounts = []
        for int_type, model_class in models:
            db_accounts = self.session.query(model_class).all()
            accounts.extend([self._to_domain(acc, int_type) for acc in db_accounts])
            
        return accounts
    
    def delete(self, account_id: int) -> bool:
        """Delete an integration account."""
        db_account = self.session.query(QuickBooksAccountModel).filter_by(id=account_id).first()
        if db_account:
            self.session.delete(db_account)
            self.session.commit()
            return True
        return False
    
    @staticmethod
    def _to_domain(db_account, integration_type: IntegrationType) -> IntegrationAccount:
        """Convert SQLAlchemy model to domain entity."""
        credentials = Credentials(
            access_token=db_account.access_token,
            refresh_token=db_account.refresh_token,
            expires_at=db_account.token_expires_at,
            token_type=db_account.token_type
        )
        
        return IntegrationAccount(
            id=db_account.id,
            integration_type=integration_type,
            external_account_id=db_account.external_account_id,
            credentials=credentials,
            status=db_account.status,
            created_at=db_account.created_at,
            updated_at=db_account.updated_at
        )

