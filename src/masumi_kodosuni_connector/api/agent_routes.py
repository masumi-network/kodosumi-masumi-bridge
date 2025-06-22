from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.services.agent_service import AgentService
from masumi_kodosuni_connector.api.schemas import JobRequest, JobResponse, JobStatusResponse
from masumi_kodosuni_connector.config.settings import settings


def create_agent_router(agent_key: str) -> APIRouter:
    router = APIRouter(prefix=f"/{agent_key}", tags=[f"Agent {agent_key}"])
    
    @router.post("/jobs", response_model=JobResponse)
    async def create_job(
        job_request: JobRequest,
        db: AsyncSession = Depends(get_db)
    ):
        if agent_key not in settings.agents_config:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        service = AgentService(db)
        try:
            agent_run = await service.create_job(
                agent_key=agent_key,
                job_data=job_request.data,
                payment_amount=job_request.payment_amount
            )
            return JobResponse(
                id=agent_run.id,
                status=agent_run.status,
                payment_id=agent_run.masumi_payment_id,
                created_at=agent_run.created_at
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/jobs/{job_id}", response_model=JobStatusResponse)
    async def get_job_status(
        job_id: int = Path(..., title="Job ID"),
        db: AsyncSession = Depends(get_db)
    ):
        service = AgentService(db)
        agent_run = await service.get_job_status(job_id)
        
        if not agent_run or agent_run.agent_key != agent_key:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatusResponse(
            id=agent_run.id,
            status=agent_run.status,
            result=agent_run.result_data,
            error_message=agent_run.error_message,
            created_at=agent_run.created_at,
            updated_at=agent_run.updated_at,
            started_at=agent_run.started_at,
            completed_at=agent_run.completed_at
        )
    
    return router