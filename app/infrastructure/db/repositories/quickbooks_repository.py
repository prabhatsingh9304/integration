"""QuickBooks repository implementation."""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.domain.models.integration_account import IntegrationType
from app.domain.models.raw_external_object import RawExternalObject
from app.domain.models.sync_cursor import ObjectType
from app.domain.ports.object_repo import RawExternalObjectRepository
from app.infrastructure.db.models import (
    QuickBooksCustomerModel, QuickBooksInvoiceModel
)

logger = logging.getLogger(__name__)


class SQLAlchemyQuickBooksRepository(RawExternalObjectRepository):
    """SQLAlchemy implementation of QuickBooks repository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session

    def save(self, obj: RawExternalObject) -> RawExternalObject:
        """
        Save or update a raw external object (UPSERT).
        
        Args:
            obj: RawExternalObject to save
            
        Returns:
            Saved object with updated ID
        """
        self.save_batch([obj])
        return obj

    def save_batch(self, objects: list[RawExternalObject]) -> list[RawExternalObject]:
        """
        Save multiple objects in a batch (UPSERT).
        
        Args:
            objects: List of RawExternalObject to save
            
        Returns:
            List of saved objects
        """
        if not objects:
            return []

        # Group by type
        customers = []
        invoices = []
        
        for obj in objects:
            if obj.object_type == ObjectType.CUSTOMER:
                customers.append(obj)
            elif obj.object_type == ObjectType.INVOICE:
                invoices.append(obj)
            else:
                logger.warning(f"Unsupported object type in batch save: {obj.object_type}")

        if customers:
            self._save_customers(customers)
        if invoices:
            self._save_invoices(invoices)
            
        return objects

    def _save_customers(self, customers: List[RawExternalObject]) -> None:
        """Helper to save customers."""
        values = [
            {
                'external_account_id': c.external_account_id,
                'qbo_id': c.external_object_id,
                'payload': c.payload,
                'last_updated_time': c.last_updated_time
            }
            for c in customers
        ]
        
        stmt = insert(QuickBooksCustomerModel).values(values).on_conflict_do_update(
            constraint='uq_qb_customer_id',
            set_={
                'payload': insert(QuickBooksCustomerModel).excluded.payload,
                'last_updated_time': insert(QuickBooksCustomerModel).excluded.last_updated_time,
                'updated_at': insert(QuickBooksCustomerModel).excluded.updated_at
            }
        )
        
        self.session.execute(stmt)
        self.session.commit()

    def _save_invoices(self, invoices: List[RawExternalObject]) -> None:
        """Helper to save invoices."""
        values = [
            {
                'external_account_id': i.external_account_id,
                'qbo_id': i.external_object_id,
                'customer_ref_value': i.payload.get("CustomerRef", {}).get("value") if i.payload else None,
                'payload': i.payload,
                'last_updated_time': i.last_updated_time
            }
            for i in invoices
        ]
        
        stmt = insert(QuickBooksInvoiceModel).values(values).on_conflict_do_update(
            constraint='uq_qb_invoice_id',
            set_={
                'customer_ref_value': insert(QuickBooksInvoiceModel).excluded.customer_ref_value,
                'payload': insert(QuickBooksInvoiceModel).excluded.payload,
                'last_updated_time': insert(QuickBooksInvoiceModel).excluded.last_updated_time,
                'updated_at': insert(QuickBooksInvoiceModel).excluded.updated_at
            }
        )
        
        self.session.execute(stmt)
        self.session.commit()

    def find_by_composite_key(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType,
        external_object_id: str
    ) -> Optional[RawExternalObject]:
        """
        Find object by composite key.
        """
        if integration_type != IntegrationType.QUICKBOOKS:
            return None
            
        model_cls = self._get_model_class(object_type)
        if not model_cls:
            return None
            
        stmt = select(model_cls).where(
            model_cls.external_account_id == external_account_id,
            model_cls.qbo_id == external_object_id
        )
        
        result = self.session.execute(stmt).scalar_one_or_none()
        if not result:
            return None
            
        return self._map_to_domain(result, integration_type, object_type)

    def list_by_account_and_type(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType,
        limit: Optional[int] = None
    ) -> list[RawExternalObject]:
        """
        List objects by account and type.
        """
        if integration_type != IntegrationType.QUICKBOOKS:
            return []

        model_cls = self._get_model_class(object_type)
        if not model_cls:
            return []
            
        stmt = select(model_cls).where(
            model_cls.external_account_id == external_account_id
        )
        
        if limit:
            stmt = stmt.limit(limit)
            
        results = self.session.execute(stmt).scalars().all()
        return [
            self._map_to_domain(r, integration_type, object_type) 
            for r in results
        ]

    def _get_model_class(self, object_type: ObjectType):
        if object_type == ObjectType.CUSTOMER:
            return QuickBooksCustomerModel
        elif object_type == ObjectType.INVOICE:
            return QuickBooksInvoiceModel
        return None

    def _map_to_domain(self, model, integration_type: IntegrationType, object_type: ObjectType) -> RawExternalObject:
        return RawExternalObject(
            id=None,
            integration_type=integration_type,
            external_account_id=model.external_account_id,
            object_type=object_type,
            external_object_id=model.qbo_id,
            payload=model.payload,
            last_updated_time=model.last_updated_time,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
