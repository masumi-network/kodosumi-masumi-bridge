import asyncio
import structlog
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
from masumi_kodosuni_connector.database.repositories import AgentRunRepository
from masumi_kodosuni_connector.services.agent_service import AgentService
from masumi_kodosuni_connector.config.settings import settings

logger = structlog.get_logger()


class PollingService:
    def __init__(self):
        self.running = False
        self.polling_interval = settings.polling_interval_seconds
    
    async def start(self):
        self.running = True
        logger.info("Starting polling service", interval=self.polling_interval)
        
        while self.running:
            try:
                await self._poll_active_jobs()
            except Exception as e:
                logger.error("Error during polling cycle", error=str(e))
            
            await asyncio.sleep(self.polling_interval)
    
    def stop(self):
        self.running = False
        logger.info("Stopping polling service")
    
    async def _poll_active_jobs(self):
        async with AsyncSessionLocal() as session:
            repository = AgentRunRepository(session)
            service = AgentService(session)
            
            active_runs = await repository.get_active_runs()
            
            if active_runs:
                logger.info("Polling active jobs", count=len(active_runs))
                
                for agent_run in active_runs:
                    try:
                        await service.update_job_from_kodosumi(agent_run)
                        logger.debug(
                            "Updated job status",
                            job_id=agent_run.id,
                            kodosumi_job_id=agent_run.kodosumi_job_id,
                            status=agent_run.status
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to update job",
                            job_id=agent_run.id,
                            error=str(e)
                        )