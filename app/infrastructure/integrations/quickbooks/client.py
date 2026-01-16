"""QuickBooks API client - Anti-Corruption Layer."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import settings
from app.infrastructure.integrations.quickbooks.models import (
    QuickBooksCustomer, QuickBooksInvoice, QuickBooksObject
)


class QuickBooksAPIClient:
    """
    QuickBooks API client implementing Anti-Corruption Layer.
    
    Responsibilities:
    - Hide QuickBooks API specifics
    - Normalize pagination
    - Handle vendor quirks
    - Return plain Python objects
    
    QuickBooks objects MUST NOT leak outside this class.
    """
    
    API_VERSION = "v3"
    MAX_RESULTS = 1000
    
    def __init__(self, realm_id: str, access_token: str):
        """
        Initialize API client.
        
        Args:
            realm_id: QuickBooks company/realm ID
            access_token: Valid OAuth access token
        """
        self.realm_id = realm_id
        self.access_token = access_token
        self.base_url = f"{settings.quickbooks_api_base_url}/{self.API_VERSION}/company/{realm_id}"
    
    async def fetch_customers(
        self,
        updated_since: Optional[datetime] = None,
        max_results: Optional[int] = None,
        start_position: Optional[int] = None
    ) -> List[QuickBooksCustomer]:
        """
        Fetch customers with optional incremental sync and pagination.
        
        Args:
            updated_since: Only fetch customers updated after this time
            max_results: Maximum number of results to return
            start_position: Starting position for pagination (1-based)
            
        Returns:
            List of QuickBooks customers
        """
        query = "SELECT * FROM Customer"
        
        if updated_since:
            formatted_date = updated_since.strftime("%Y-%m-%dT%H:%M:%S")
            query += f" WHERE Active IN (true, false) AND MetaData.LastUpdatedTime > '{formatted_date}Z'"
        else:
            query += " WHERE Active IN (true, false)"
        
        query += " ORDERBY MetaData.LastUpdatedTime"
        
        if start_position:
            query += f" STARTPOSITION {start_position}"
        
        if max_results:
            query += f" MAXRESULTS {min(max_results, self.MAX_RESULTS)}"
        
        results = await self._execute_query(query)
        
        customers = []
        for item in results.get("Customer", []):
            customers.append(self._parse_customer(item))
        
        return customers
    
    async def fetch_invoices(
        self,
        updated_since: Optional[datetime] = None,
        max_results: Optional[int] = None,
        start_position: Optional[int] = None
    ) -> List[QuickBooksInvoice]:
        """
        Fetch invoices with optional incremental sync and pagination.
        
        Args:
            updated_since: Only fetch invoices updated after this time
            max_results: Maximum number of results to return
            start_position: Starting position for pagination (1-based)
            
        Returns:
            List of QuickBooks invoices
        """
        query = "SELECT * FROM Invoice"
        
        if updated_since:
            formatted_date = updated_since.strftime("%Y-%m-%dT%H:%M:%S")
            query += f" WHERE MetaData.LastUpdatedTime > '{formatted_date}Z'"
        
        query += " ORDERBY MetaData.LastUpdatedTime"
        
        if start_position:
            query += f" STARTPOSITION {start_position}"
        
        if max_results:
            query += f" MAXRESULTS {min(max_results, self.MAX_RESULTS)}"
        
        results = await self._execute_query(query)
        
        invoices = []
        for item in results.get("Invoice", []):
            invoices.append(self._parse_invoice(item))
        
        return invoices
    
    async def _execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute QuickBooks query.
        
        Args:
            query: SQL-like query string
            
        Returns:
            Query results
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/query"
        params = {"query": query}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            data = response.json()
        
        return data.get("QueryResponse", {})
    
    @staticmethod
    def _parse_customer(data: Dict[str, Any]) -> QuickBooksCustomer:
        """
        Parse QuickBooks Customer response.
        
        Args:
            data: Raw customer data from API
            
        Returns:
            QuickBooksCustomer DTO
        """
        metadata = data.get("MetaData", {})
        
        ts_str = metadata.get("LastUpdatedTime")
        if ts_str:
            if ts_str.endswith("Z"):
                ts_str = ts_str.replace("Z", "+00:00")
            last_updated = datetime.fromisoformat(ts_str)
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
        else:
            last_updated = datetime.now(timezone.utc)
        
        return QuickBooksCustomer(
            id=data["Id"],
            last_updated_time=last_updated,
            raw_payload=data,
            display_name=data.get("DisplayName")
        )
    
    @staticmethod
    def _parse_invoice(data: Dict[str, Any]) -> QuickBooksInvoice:
        """
        Parse QuickBooks Invoice response.
        
        Args:
            data: Raw invoice data from API
            
        Returns:
            QuickBooksInvoice DTO
        """
        metadata = data.get("MetaData", {})
        
        ts_str = metadata.get("LastUpdatedTime")
        if ts_str:
            if ts_str.endswith("Z"):
                ts_str = ts_str.replace("Z", "+00:00")
            last_updated = datetime.fromisoformat(ts_str)
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
        else:
            last_updated = datetime.now(timezone.utc)
        
        customer_ref = None
        if "CustomerRef" in data:
            customer_ref = data["CustomerRef"].get("value")
        
        return QuickBooksInvoice(
            id=data["Id"],
            last_updated_time=last_updated,
            raw_payload=data,
            customer_ref=customer_ref,
            total_amount=data.get("TotalAmt")
        )
