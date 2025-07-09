import asyncio
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.config.settings import settings
from masumi_kodosuni_connector.config.logging import get_logger

logger = get_logger("polling")

# Rate limiting configuration for job processing (configurable via environment)


class PollingService:
    def __init__(self):
        self.running = False
        self.polling_interval = settings.polling_interval_seconds
        self.max_concurrent_status_checks = settings.max_concurrent_status_checks
        self.batch_delay_seconds = settings.batch_delay_seconds
        self.current_cycle = 0
    
    async def start(self):
        self.running = True
        logger.info("Starting queue-based polling service", 
                   interval=self.polling_interval,
                   max_concurrent_checks=self.max_concurrent_status_checks,
                   batch_delay=self.batch_delay_seconds)
        
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
    
    def _prioritize_jobs(self, jobs):
        """Prioritize jobs for processing to handle most urgent ones first."""
        # Sort by multiple criteria:
        # 1. Jobs that are closer to timeout (more urgent)
        # 2. Newer jobs (created more recently)
        # 3. Jobs that have been waiting longer for status updates
        
        def priority_key(job):
            now = datetime.utcnow()
            
            # Calculate urgency score (lower is more urgent)
            if job.timeout_at:
                time_to_timeout = (job.timeout_at - now).total_seconds()
                # Jobs close to timeout get priority (negative for near-timeout jobs)
                urgency_score = time_to_timeout
            else:
                # Jobs without timeout get lower priority
                urgency_score = 86400  # 24 hours
            
            # Calculate recency score (newer jobs get priority)
            if job.created_at:
                age_seconds = (now - job.created_at).total_seconds()
                recency_score = age_seconds
            else:
                recency_score = 86400  # 24 hours
            
            # Calculate staleness score (jobs not updated recently get priority)
            if job.updated_at:
                staleness_seconds = (now - job.updated_at).total_seconds()
            else:
                staleness_seconds = 86400  # 24 hours
            
            # Combine scores (lower total score = higher priority)
            # Weight urgency most heavily, then staleness, then recency
            total_score = (urgency_score * 10) + (staleness_seconds * 2) + (recency_score * 1)
            
            return total_score
        
        sorted_jobs = sorted(jobs, key=priority_key)
        
        if len(jobs) > 10:  # Only log prioritization details for large job counts
            logger.info("Job prioritization applied", 
                       total_jobs=len(jobs),
                       first_job_id=sorted_jobs[0].id if sorted_jobs else None,
                       last_job_id=sorted_jobs[-1].id if sorted_jobs else None)
        
        return sorted_jobs
    
    async def _process_all_active_jobs(self):
        """Process all active jobs in batches to respect rate limits."""
        async with AsyncSessionLocal() as session:
            repository = FlowRunRepository(session)
            service = FlowService(session)
            
            # Get all active jobs at once
            active_runs = await repository.get_active_runs()
            
            if not active_runs:
                logger.debug("No active jobs to process this cycle", cycle=self.current_cycle)
                return
            
            logger.info("Processing active jobs in batches", 
                       cycle=self.current_cycle,
                       total_jobs=len(active_runs),
                       batch_size=self.max_concurrent_status_checks)
            
            # Sort jobs by priority (newer jobs first, then by urgency)
            prioritized_jobs = self._prioritize_jobs(active_runs)
            
            # Process jobs in batches to respect rate limits
            total_successful = 0
            total_failed = 0
            
            for i in range(0, len(prioritized_jobs), self.max_concurrent_status_checks):
                batch = prioritized_jobs[i:i + self.max_concurrent_status_checks]
                batch_num = (i // self.max_concurrent_status_checks) + 1
                
                logger.info("Processing batch", 
                           cycle=self.current_cycle,
                           batch_number=batch_num,
                           batch_size=len(batch),
                           total_batches=(len(prioritized_jobs) + self.max_concurrent_status_checks - 1) // self.max_concurrent_status_checks)
                
                # Process batch concurrently
                tasks = []
                for flow_run in batch:
                    task = asyncio.create_task(
                        self._process_single_job(service, flow_run),
                        name=f"job_{flow_run.id}"
                    )
                    tasks.append(task)
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count batch results
                batch_successful = sum(1 for r in results if not isinstance(r, Exception))
                batch_failed = len(results) - batch_successful
                
                total_successful += batch_successful
                total_failed += batch_failed
                
                logger.info("Batch completed",
                           cycle=self.current_cycle,
                           batch_number=batch_num,
                           batch_successful=batch_successful,
                           batch_failed=batch_failed)
                
                # Add delay between batches to respect rate limits (except for last batch)
                if i + self.max_concurrent_status_checks < len(prioritized_jobs):
                    logger.debug("Waiting between batches", 
                               cycle=self.current_cycle,
                               delay_seconds=self.batch_delay_seconds)
                    await asyncio.sleep(self.batch_delay_seconds)
            
            logger.info("Cycle processing completed",
                       cycle=self.current_cycle,
                       total_jobs=len(active_runs),
                       successful=total_successful,
                       failed=total_failed)
    
    async def _process_single_job(self, service: FlowService, flow_run):
        """Process a single job with proper error handling."""
        try:
            # Check for timeout first
            if flow_run.timeout_at and datetime.utcnow() > flow_run.timeout_at:
                logger.warning(
                    "Job timed out - marking as TIMEOUT",
                    run_id=flow_run.id,
                    kodosumi_run_id=flow_run.kodosumi_run_id,
                    timeout_at=flow_run.timeout_at.isoformat(),
                    current_time=datetime.utcnow().isoformat()
                )
                await service.mark_job_as_timeout(flow_run.id)
                return
            
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