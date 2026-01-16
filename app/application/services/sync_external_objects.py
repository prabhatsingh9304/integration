"""Sync external objects application service."""
from datetime import datetime
from typing import List
import logging

from app.domain.models.integration_account import IntegrationType
from app.domain.models.raw_external_object import RawExternalObject
from app.domain.models.sync_cursor import ObjectType, SyncCursor, SyncStatus
from app.domain.ports.cursor_repo import SyncCursorRepository
from app.domain.ports.object_repo import RawExternalObjectRepository
from app.infrastructure.integrations.quickbooks.client import QuickBooksAPIClient
from app.infrastructure.integrations.quickbooks.models import QuickBooksObject

logger = logging.getLogger(__name__)


class SyncExternalObjectsService:
    """
    Application service for syncing external objects.
    
    Responsibilities:
    - Fetch current cursor position
    - Query external API for changes since cursor
    - Handle pagination
    - Upsert raw objects to database
    - Advance cursor only after successful persistence
    - Idempotent by design
    """
    
    def __init__(
        self,
        cursor_repo: SyncCursorRepository,
        object_repo: RawExternalObjectRepository
    ):
        """
        Initialize service with repositories.
        
        Args:
            cursor_repo: Cursor repository
            object_repo: Object repository (generic)
        """
        self.cursor_repo = cursor_repo
        self.object_repo = object_repo
    
    async def sync_quickbooks_objects(
        self,
        integration_type: IntegrationType,
        external_account_id: str,
        object_type: ObjectType,
        api_client: QuickBooksAPIClient
    ) -> dict:
        """
        Sync QuickBooks objects for a specific type.
        
        Args:
            integration_type: Type of integration
            external_account_id: External account ID
            object_type: Type of object to sync
            api_client: QuickBooks API client
            
        Returns:
            Number of objects synced
            
        Raises:
            Exception: If sync fails
        """
        logger.info(
            f"Starting sync for {integration_type.value} account {external_account_id}, "
            f"object type {object_type.value}"
        )
        
        # Get or create cursor
        cursor = self.cursor_repo.find_by_composite_key(
            integration_type, external_account_id, object_type
        )
        
        if not cursor:
            cursor = SyncCursor(
                id=None,
                integration_type=integration_type,
                external_account_id=external_account_id,
                object_type=object_type,
                last_synced_at=None,
                last_attempt_at=datetime.utcnow(),
                status=SyncStatus.IN_PROGRESS
            )
        
        # Mark attempt started
        cursor.mark_attempt()
        self.cursor_repo.save(cursor)
        
        total_synced = 0
        start_position = 1
        
        # Check for resumption
        if cursor.cursor_data and "start_position" in cursor.cursor_data:
            start_position = cursor.cursor_data["start_position"]
            logger.info(f"Resuming sync from position {start_position}")
        
        try:
            while True:
                # Fetch objects from external API
                qb_objects = await self._fetch_objects_from_api(
                    api_client, 
                    object_type, 
                    cursor.get_cursor_value(),
                    start_position=start_position
                )
                
                if not qb_objects:
                    logger.info(f"No more {object_type.value} objects to sync")
                    break
                
                # Convert DTOs to Domain Entities
                raw_objects = []
                for obj in qb_objects:
                    raw_objects.append(RawExternalObject(
                        id=None,
                        integration_type=integration_type,
                        external_account_id=external_account_id,
                        object_type=object_type,
                        external_object_id=obj.id,
                        payload=obj.raw_payload,
                        last_updated_time=obj.last_updated_time
                    ))
                
                # Persist objects (UPSERT)
                self.object_repo.save_batch(raw_objects)

                # Calculate latest timestamp for cursor
                latest_timestamp = max(obj.last_updated_time for obj in qb_objects)
                
                # Update loop state
                batch_size = len(qb_objects)
                total_synced += batch_size
                start_position += batch_size
                
                # Advance cursor incrementally (checkpoint)
                cursor.advance_cursor(
                    latest_timestamp, 
                    batch_size, 
                    cursor_data={"start_position": start_position}
                )
                self.cursor_repo.save(cursor)
                
                logger.debug(f"Synced batch of {batch_size}, next position {start_position}")
                
            # Sync Complete - Clear granular cursor data
            logger.info(f"Successfully finished sync of {total_synced} {object_type.value} objects")
            
            # We need to save one last time to clear cursor_data indicating full success
            cursor.cursor_data = None
            self.cursor_repo.save(cursor)
            
            return {"count": total_synced, "has_more": False}
            
        except Exception as e:
            logger.error(f"Sync failed for {object_type.value}: {str(e)}")
            cursor.mark_failure(str(e), cursor_data={"start_position": start_position})
            self.cursor_repo.save(cursor)
            raise
    
    async def _fetch_objects_from_api(
        self,
        api_client: QuickBooksAPIClient,
        object_type: ObjectType,
        updated_since: datetime | None,
        start_position: int = 1
    ) -> List[QuickBooksObject]:
        """
        Fetch objects from QuickBooks API.
        
        Args:
            api_client: QuickBooks API client
            object_type: Type of object to fetch
            updated_since: Only fetch objects updated after this time
            start_position: Pagination start position
            
        Returns:
            List of QuickBooks objects
        """
        if object_type == ObjectType.CUSTOMER:
            return await api_client.fetch_customers(
                updated_since=updated_since,
                start_position=start_position
            )
        elif object_type == ObjectType.INVOICE:
            return await api_client.fetch_invoices(
                updated_since=updated_since,
                start_position=start_position
            )
        else:
            raise ValueError(f"Unsupported object type: {object_type}")
