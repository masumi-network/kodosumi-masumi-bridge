import asyncio
import structlog
from typing import List
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
    
    async def start(self):
        self.running = True
        logger.info("Starting polling service", interval=self.polling_interval)
        
        while self.running:
            try:
                await self._poll_active_flow_runs()
            except Exception as e:
                logger.error("Error during polling cycle", error=str(e))
            
            await asyncio.sleep(self.polling_interval)
    
    def stop(self):
        self.running = False
        logger.info("Stopping polling service")
    
    async def _poll_active_flow_runs(self):
        async with AsyncSessionLocal() as session:
            repository = FlowRunRepository(session)
            service = FlowService(session)
            
            active_runs = await repository.get_active_runs()
            
            if active_runs:
                logger.info("Polling active flow runs", count=len(active_runs))
                
                for flow_run in active_runs:
                    try:
                        await service.update_flow_run_from_kodosumi(flow_run)
                        logger.debug(
                            "Updated flow run status",
                            run_id=flow_run.id,
                            kodosumi_run_id=flow_run.kodosumi_run_id,
                            status=flow_run.status,
                            flow_path=flow_run.flow_path
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to update flow run",
                            run_id=flow_run.id,
                            error=str(e)
                        )