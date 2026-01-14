"""QuickBooks repository implementation."""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.integrations.quickbooks.models import (
    QuickBooksCustomer, QuickBooksInvoice
)
from app.infrastructure.db.models import (
    QuickBooksCustomerModel, QuickBooksInvoiceModel
)

logger = logging.getLogger(__name__)


class SQLAlchemyQuickBooksRepository:
    """SQLAlchemy implementation of QuickBooks repository."""
    
    def __init__(self, session: Session):
        """
        Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session

    def save_customers_batch(
        self, 
        customers: List[QuickBooksCustomer],
        external_account_id: str
    ) -> None:
        """
        Save customers batch using UPSERT.
        
        Args:
            customers: List of QuickBooks customer DTOs
            external_account_id: Associated Integration Account ID (Realm ID)
        """
        if not customers:
            return

        values = [
            {
                'external_account_id': external_account_id,
                'qbo_id': customer.id,
                'payload': customer.raw_payload,
                'last_updated_time': customer.last_updated_time
            }
            for customer in customers
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
    
    def save_invoices_batch(
        self, 
        invoices: List[QuickBooksInvoice],
        external_account_id: str
    ) -> None:
        """
        Save invoices batch using UPSERT.
        
        Args:
            invoices: List of QuickBooks invoice DTOs
            external_account_id: Associated Integration Account ID (Realm ID)
        """
        if not invoices:
            return

        values = [
            {
                'external_account_id': external_account_id,
                'qbo_id': invoice.id,
                'customer_ref_value': invoice.customer_ref,
                'payload': invoice.raw_payload,
                'last_updated_time': invoice.last_updated_time
            }
            for invoice in invoices
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
