"""Temporal worker - executes workflows and activities."""
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.temporal.workflows import IntegrationSyncWorkflow
from app.temporal.activities import run_integration_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Temporal worker."""
    logger.info(f"Connecting to Temporal server at {settings.temporal_host}")
    
    # Connect to Temporal server
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace
    )
    
    logger.info(f"Starting worker on task queue: {settings.temporal_task_queue}")
    
    # Create worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[IntegrationSyncWorkflow],
        activities=[run_integration_sync]
    )
    
    # Run worker
    logger.info("Worker started, waiting for tasks...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
