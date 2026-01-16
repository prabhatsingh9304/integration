"""Temporal workflows - orchestration only, no business logic."""
from datetime import timedelta
import logging
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.domain.models.integration_account import IntegrationType
    from app.temporal.activities import run_integration_sync

logger = logging.getLogger(__name__)


@workflow.defn
class IntegrationSyncWorkflow:
    """
    Temporal workflow for continuous integration sync.
    
    One workflow instance per IntegrationAccount.
    
    Responsibilities:
    - Refresh credentials if needed
    - Sync supported object types
    - Sleep between cycles
    - Use continue_as_new() to avoid history bloat
    
    NO business logic, NO DB access, NO HTTP calls.
    """
    
    @workflow.run
    async def run(
        self,
        integration_type: str,
        external_account_id: str,
        sync_interval_minutes: int = 5
    ) -> None:
        """
        Run continuous sync workflow.
        
        Args:
            integration_type: Type of integration (e.g., 'quickbooks')
            external_account_id: External account ID
            sync_interval_minutes: Minutes between sync cycles
        """

        workflow.logger.info( f"Starting sync workflow for {integration_type} account {external_account_id}" )
        
        # Run one sync cycle
        results = {}
        try:
            # Execute sync via activity
            results = await workflow.execute_activity(
                run_integration_sync,
                args=[integration_type, external_account_id],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=5),
                    maximum_attempts=3,
                    backoff_coefficient=2.0
                )
            )
            
            workflow.logger.info(f"Sync completed: {results}")
            
        except Exception as e:
            workflow.logger.error(f"Sync failed: {str(e)}")
        
        # Check if we should sleep or fast-sync (backfill mode)
        should_sleep = True
        try:
            for res in results.values():
                if res.get("has_more", False):
                    should_sleep = False
                    workflow.logger.info("Fast Sync triggered: has_more flag detected, skipping sleep")
                    break
        except Exception:
            pass

        # Sleep between cycles if not in fast-sync mode
        if should_sleep:
            await workflow.sleep(timedelta(minutes=sync_interval_minutes))
        
        # Continue as new to avoid history bloat
        workflow.continue_as_new(
            args=[
                integration_type,
                external_account_id,
                sync_interval_minutes
            ]
        )
