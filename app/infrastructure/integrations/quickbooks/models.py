"""QuickBooks-specific data transfer objects."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class QuickBooksObject:
    """Base DTO for QuickBooks objects."""
    id: str
    last_updated_time: datetime
    raw_payload: Dict[str, Any]


@dataclass
class QuickBooksCustomer(QuickBooksObject):
    """DTO for QuickBooks Customer."""
    display_name: Optional[str] = None


@dataclass
class QuickBooksInvoice(QuickBooksObject):
    """DTO for QuickBooks Invoice."""
    customer_ref: Optional[str] = None
    total_amount: Optional[float] = None
