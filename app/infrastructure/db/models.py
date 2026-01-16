"""SQLAlchemy ORM models for database persistence."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Enum as SQLEnum,
    UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base
from app.domain.models.integration_account import IntegrationType, AccountStatus
from app.domain.models.sync_cursor import ObjectType, SyncStatus


# ----------------------------------------------------------------------
# QuickBooks Schema Models
# ----------------------------------------------------------------------

class QuickBooksAccountModel(Base):
    """SQLAlchemy model for quickbooks.accounts table."""
    
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_account_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    token_type = Column(String(50), nullable=False, default="Bearer")
    status = Column(SQLEnum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('external_account_id', name='uq_qb_account_realm_id'),
        {'schema': 'quickbooks'}
    )


class QuickBooksSyncCursorModel(Base):
    """SQLAlchemy model for quickbooks.sync_cursors table."""
    
    __tablename__ = "sync_cursors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_account_id = Column(String(255), nullable=False)
    object_type = Column(SQLEnum(ObjectType), nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(SQLEnum(SyncStatus), nullable=False, default=SyncStatus.SUCCESS)
    cursor_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    records_synced = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('external_account_id', 'object_type', name='uq_qb_cursor_composite'),
        {'schema': 'quickbooks'}
    )


class QuickBooksCustomerModel(Base):
    """SQLAlchemy model for quickbooks.customers table."""
    
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_account_id = Column(String(255), nullable=False)
    qbo_id = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=False)
    last_updated_time = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('external_account_id', 'qbo_id', name='uq_qb_customer_id'),
        {'schema': 'quickbooks'}
    )


class QuickBooksInvoiceModel(Base):
    """SQLAlchemy model for quickbooks.invoices table."""
    
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_account_id = Column(String(255), nullable=False)
    qbo_id = Column(String(255), nullable=False)
    customer_ref_value = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=False)
    last_updated_time = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('external_account_id', 'qbo_id', name='uq_qb_invoice_id'),
        {'schema': 'quickbooks'}
    )
