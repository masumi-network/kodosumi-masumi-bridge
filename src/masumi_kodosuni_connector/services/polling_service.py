import asyncio
import structlog
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.config.settings import settings

logger = structlog.get_logger()


class PollingService:
    def __init__(self):
        self.running = False
        self.polling_interval = settings.polling_interval_seconds
        self.current_cycle = 0
    
    async def start(self):
        self.running = True
        logger.info("Starting queue-based polling service", interval=self.polling_interval)
        
        while self.running:
            cycle_start_time = datetime.now()
            self.current_cycle += 1
            
            try:
                await self._process_all_active_jobs()
            except Exception as e:
                logger.error("Error during polling cycle", cycle=self.current_cycle, error=str(e))
            
            # Wait for the specified interval before next cycle, regardless of how long processing took
            cycle_duration = (datetime.now() - cycle_start_time).total_seconds()
            logger.info("Polling cycle completed", 
                       cycle=self.current_cycle,
                       duration_seconds=round(cycle_duration, 2))
            
            # Always wait the full interval between cycles
            await asyncio.sleep(self.polling_interval)
    
    def stop(self):
        self.running = False
        logger.info("Stopping polling service")
    
    async def _process_all_active_jobs(self):
        """Process all active jobs in this cycle, regardless of how long it takes."""
        async with AsyncSessionLocal() as session:
            repository = FlowRunRepository(session)
            service = FlowService(session)
            
            # Get all active jobs at once
            active_runs = await repository.get_active_runs()
            
            if not active_runs:
                logger.debug("No active jobs to process this cycle", cycle=self.current_cycle)
                return
            
            logger.info("Processing all active jobs in cycle", 
                       cycle=self.current_cycle,
                       job_count=len(active_runs))
            
            # Process all jobs concurrently for better performance
            tasks = []
            for flow_run in active_runs:
                task = asyncio.create_task(
                    self._process_single_job(service, flow_run),
                    name=f"job_{flow_run.id}"
                )
                tasks.append(task)
            
            # Wait for all jobs to complete (or fail)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log summary
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            logger.info("Cycle processing completed",
                       cycle=self.current_cycle,
                       total_jobs=len(active_runs),
                       successful=successful,
                       failed=failed)
    
    async def _process_single_job(self, service: FlowService, flow_run):
        """Process a single job with proper error handling."""
        try:
            await service.update_flow_run_from_kodosumi(flow_run)
            logger.debug(
                "Job processed successfully",
                cycle=self.current_cycle,
                run_id=flow_run.id,
                kodosumi_run_id=flow_run.kodosumi_run_id,
                status=flow_run.status,
                flow_path=flow_run.flow_path
            )
        except Exception as e:
            logger.error(
                "Failed to process job",
                cycle=self.current_cycle,
                run_id=flow_run.id,
                kodosumi_run_id=flow_run.kodosumi_run_id,
                error=str(e)
            )
            # Re-raise to be caught by gather() for proper accounting
            raise