from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient
from masumi_kodosuni_connector.clients.masumi_client import MasumiClient
from masumi_kodosuni_connector.database.repositories import AgentRunRepository
from masumi_kodosuni_connector.models.agent_run import AgentRun, AgentRunStatus
from masumi_kodosuni_connector.config.settings import settings


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AgentRunRepository(session)
        self.kodosumi_client = KodosumyClient()
        self.masumi_client = MasumiClient()
    
    async def create_job(self, agent_key: str, job_data: Dict[str, Any], payment_amount: Optional[float] = None) -> AgentRun:
        if agent_key not in settings.agents_config:
            raise ValueError(f"Unknown agent: {agent_key}")
        
        masumi_payment_id = None
        if payment_amount and payment_amount > 0:
            payment_response = await self.masumi_client.create_payment_request(
                amount=payment_amount,
                metadata={"agent_key": agent_key}
            )
            masumi_payment_id = payment_response.get("payment_id")
        
        agent_run = await self.repository.create(
            agent_key=agent_key,
            request_data=job_data,
            masumi_payment_id=masumi_payment_id
        )
        
        if not masumi_payment_id:
            await self._start_kodosumi_job(agent_run)
        
        return agent_run
    
    async def get_job_status(self, run_id: int) -> Optional[AgentRun]:
        return await self.repository.get_by_id(run_id)
    
    async def process_payment_confirmation(self, payment_id: str) -> bool:
        agent_run = await self.repository.get_by_masumi_payment_id(payment_id)
        if not agent_run:
            return False
        
        is_confirmed = await self.masumi_client.verify_payment(payment_id)
        if is_confirmed:
            await self.repository.update_status(agent_run.id, AgentRunStatus.PAYMENT_CONFIRMED)
            await self._start_kodosumi_job(agent_run)
            return True
        
        return False
    
    async def _start_kodosumi_job(self, agent_run: AgentRun) -> None:
        agent_config = settings.agents_config[agent_run.agent_key]
        
        try:
            job_response = await self.kodosumi_client.start_job(
                agent_config.kodosumi_agent_id,
                agent_run.request_data
            )
            
            kodosumi_job_id = job_response.get("job_id")
            if kodosumi_job_id:
                await self.repository.update_status(
                    agent_run.id,
                    AgentRunStatus.RUNNING,
                    kodosumi_job_id=kodosumi_job_id
                )
        except Exception as e:
            await self.repository.update_error(agent_run.id, str(e))
    
    async def update_job_from_kodosumi(self, agent_run: AgentRun) -> None:
        if not agent_run.kodosumi_job_id:
            return
        
        try:
            job_status = await self.kodosumi_client.get_job_status(agent_run.kodosumi_job_id)
            kodosumi_status = job_status.get("status")
            
            if kodosumi_status == "completed":
                result_data = await self.kodosumi_client.get_job_result(agent_run.kodosumi_job_id)
                await self.repository.update_result(agent_run.id, result_data)
                await self.repository.update_status(agent_run.id, AgentRunStatus.COMPLETED)
            elif kodosumi_status == "failed":
                error_msg = job_status.get("error", "Job failed")
                await self.repository.update_error(agent_run.id, error_msg)
        except Exception as e:
            await self.repository.update_error(agent_run.id, f"Failed to update from Kodosumi: {str(e)}")