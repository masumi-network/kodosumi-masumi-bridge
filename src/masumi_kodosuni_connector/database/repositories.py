from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus


class FlowRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, flow_path: str, flow_name: str, inputs: Dict[str, Any], masumi_payment_id: Optional[str] = None) -> FlowRun:
        flow_run = FlowRun(
            flow_path=flow_path,
            flow_name=flow_name,
            inputs=inputs,
            masumi_payment_id=masumi_payment_id,
            status=FlowRunStatus.PENDING_PAYMENT
        )
        self.session.add(flow_run)
        await self.session.commit()
        await self.session.refresh(flow_run)
        return flow_run
    
    async def get_by_id(self, run_id: str) -> Optional[FlowRun]:
        result = await self.session.execute(
            select(FlowRun).where(FlowRun.id == run_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_kodosumi_run_id(self, run_id: str) -> Optional[FlowRun]:
        result = await self.session.execute(
            select(FlowRun).where(FlowRun.kodosumi_run_id == run_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_masumi_payment_id(self, payment_id: str) -> Optional[FlowRun]:
        result = await self.session.execute(
            select(FlowRun).where(FlowRun.masumi_payment_id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, run_id: str, status: FlowRunStatus, kodosumi_run_id: Optional[str] = None) -> bool:
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == FlowRunStatus.STARTING and kodosumi_run_id:
            update_data["kodosumi_run_id"] = kodosumi_run_id
            update_data["started_at"] = datetime.utcnow()
        elif status in [FlowRunStatus.FINISHED, FlowRunStatus.ERROR]:
            update_data["completed_at"] = datetime.utcnow()
        
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(**update_data)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_result(self, run_id: str, result_data: Dict[str, Any]) -> bool:
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(result_data=result_data, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_events(self, run_id: str, events: List[Dict[str, Any]]) -> bool:
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(events=events, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_error(self, run_id: str, error_message: str) -> bool:
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(
                error_message=error_message,
                status=FlowRunStatus.ERROR,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_active_runs(self) -> List[FlowRun]:
        result = await self.session.execute(
            select(FlowRun).where(
                FlowRun.status.in_([
                    FlowRunStatus.PAYMENT_CONFIRMED,
                    FlowRunStatus.STARTING,
                    FlowRunStatus.RUNNING
                ])
            )
        )
        return result.scalars().all()
    
    async def get_runs_by_flow(self, flow_path: str, limit: int = 50) -> List[FlowRun]:
        result = await self.session.execute(
            select(FlowRun)
            .where(FlowRun.flow_path == flow_path)
            .order_by(FlowRun.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_payment_id(self, run_id: str, payment_id: str) -> bool:
        """Update the Masumi payment ID for a flow run."""
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(masumi_payment_id=payment_id, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_payment_response(self, run_id: str, payment_response: Dict[str, Any]) -> bool:
        """Update the payment response data for a flow run."""
        result = await self.session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id)
            .values(payment_response=payment_response, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0