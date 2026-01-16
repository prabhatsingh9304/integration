"""SyncCursor repository implementation using SQLAlchemy."""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.domain.models.integration_account import IntegrationType
from app.domain.models.sync_cursor import SyncCursor, ObjectType, SyncStatus
from app.domain.ports.cursor_repo import SyncCursorRepository
from app.infrastructure.db.models import QuickBooksSyncCursorModel


class SQLAlchemySyncCursorRepository(SyncCursorRepository):
    """SQLAlchemy implementation of SyncCursorRepository."""
    
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
            return QuickBooksSyncCursorModel
        raise ValueError(f"Unsupported integration type: {integration_type}")
    
    def save(self, cursor: SyncCursor) -> SyncCursor:
        """Save or update a sync cursor using UPSERT."""
        ModelClass = self._get_model(cursor.integration_type)
        
        # Upsert cursor state
        stmt = insert(ModelClass).values(
            external_account_id=cursor.external_account_id,
            object_type=cursor.object_type,
            last_synced_at=cursor.last_synced_at,
            last_attempt_at=cursor.last_attempt_at,
            status=cursor.status,
            cursor_data=cursor.cursor_data,
            error_message=cursor.error_message,
            records_synced=cursor.records_synced,
            updated_at=cursor.updated_at
        ).on_conflict_do_update(
            constraint='uq_qb_cursor_composite',
            set_={
                'last_synced_at': insert(ModelClass).excluded.last_synced_at,
                'last_attempt_at': insert(ModelClass).excluded.last_attempt_at,
                'status': insert(ModelClass).excluded.status,
                'cursor_data': insert(ModelClass).excluded.cursor_data,
                'error_message': insert(ModelClass).excluded.error_message,
                'records_synced': insert(ModelClass).excluded.records_synced,
                'updated_at': insert(ModelClass).excluded.updated_at
            }
        ).returning(ModelClass)
        
        result = self.session.execute(stmt)
        self.session.commit()
        db_cursor = result.fetchone()
        
        db_cursor = self.session.query(ModelClass).filter_by(
            external_account_id=cursor.external_account_id,
            object_type=cursor.object_type
        ).first()
        
        return self._to_domain(db_cursor, cursor.integration_type)
    
    def find_by_composite_key(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType
    ) -> Optional[SyncCursor]:
        """Find cursor by composite key."""
        ModelClass = self._get_model(integration_type)
        
        db_cursor = self.session.query(ModelClass).filter_by(
            external_account_id=external_account_id,
            object_type=object_type
        ).first()
        
        return self._to_domain(db_cursor, integration_type) if db_cursor else None
    
    def list_by_account(
        self,
        integration_type: IntegrationType,
        external_account_id: str
    ) -> list[SyncCursor]:
        """List all cursors for an account."""
        ModelClass = self._get_model(integration_type)
        
        db_cursors = self.session.query(ModelClass).filter_by(
            external_account_id=external_account_id
        ).all()
        
        return [self._to_domain(db_cursor, integration_type) for db_cursor in db_cursors]
    
    @staticmethod
    def _to_domain(db_cursor, integration_type: IntegrationType) -> SyncCursor:
        """Convert SQLAlchemy model to domain entity."""
        return SyncCursor(
            id=db_cursor.id,
            integration_type=integration_type,
            external_account_id=db_cursor.external_account_id,
            object_type=db_cursor.object_type,
            last_synced_at=db_cursor.last_synced_at,
            last_attempt_at=db_cursor.last_attempt_at,
            status=db_cursor.status,
            cursor_data=db_cursor.cursor_data,
            error_message=db_cursor.error_message,
            records_synced=db_cursor.records_synced,
            created_at=db_cursor.created_at,
            updated_at=db_cursor.updated_at
        )

