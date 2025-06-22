from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from masumi_kodosuni_connector.models.agent_run import AgentRun, AgentRunStatus


class AgentRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, agent_key: str, request_data: Dict[str, Any], masumi_payment_id: Optional[str] = None) -> AgentRun:
        agent_run = AgentRun(
            agent_key=agent_key,
            request_data=request_data,
            masumi_payment_id=masumi_payment_id,
            status=AgentRunStatus.PENDING_PAYMENT
        )
        self.session.add(agent_run)
        await self.session.commit()
        await self.session.refresh(agent_run)
        return agent_run
    
    async def get_by_id(self, run_id: int) -> Optional[AgentRun]:
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_kodosumi_job_id(self, job_id: str) -> Optional[AgentRun]:
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.kodosumi_job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_masumi_payment_id(self, payment_id: str) -> Optional[AgentRun]:
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.masumi_payment_id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, run_id: int, status: AgentRunStatus, kodosumi_job_id: Optional[str] = None) -> bool:
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == AgentRunStatus.RUNNING and kodosumi_job_id:
            update_data["kodosumi_job_id"] = kodosumi_job_id
            update_data["started_at"] = datetime.utcnow()
        elif status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()
        
        result = await self.session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(**update_data)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_result(self, run_id: int, result_data: Dict[str, Any]) -> bool:
        result = await self.session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(result_data=result_data, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_error(self, run_id: int, error_message: str) -> bool:
        result = await self.session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(
                error_message=error_message,
                status=AgentRunStatus.FAILED,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_active_runs(self) -> List[AgentRun]:
        result = await self.session.execute(
            select(AgentRun).where(
                AgentRun.status.in_([
                    AgentRunStatus.PAYMENT_CONFIRMED,
                    AgentRunStatus.RUNNING
                ])
            )
        )
        return result.scalars().all()
    
    async def get_runs_by_agent(self, agent_key: str, limit: int = 50) -> List[AgentRun]:
        result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.agent_key == agent_key)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()