from fastapi import APIRouter, Depends, HTTPException, Path
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.api.schemas import (
    FlowRunRequest, FlowRunResponse, FlowRunStatusResponse,
    FlowInfo, FlowListResponse, FlowSchemaResponse
)

# Get the dedicated flow submission logger
flow_logger = logging.getLogger("flow_submission")


def create_flow_router(flow_key: str, flow_info: dict) -> APIRouter:
    router = APIRouter(prefix=f"/{flow_key}", tags=[f"Flow {flow_info['name']}"])
    
    @router.post("/runs", response_model=FlowRunResponse)
    async def create_flow_run(
        run_request: FlowRunRequest,
        db: AsyncSession = Depends(get_db)
    ):
        flow_logger.info(f"=== API ENDPOINT: CREATE FLOW RUN ===")
        flow_logger.info(f"Flow Key: {flow_key}")
        flow_logger.info(f"Request: {json.dumps(run_request.dict(), indent=2)}")
        
        service = FlowService(db)
        try:
            flow_run = await service.create_flow_run(
                flow_key=flow_key,
                inputs=run_request.inputs,
                identifier_from_purchaser=run_request.identifier_from_purchaser,
                payment_amount=run_request.payment_amount
            )
            response = FlowRunResponse(
                id=flow_run.id,
                status=flow_run.status,
                payment_id=flow_run.masumi_payment_id,
                created_at=flow_run.created_at
            )
            flow_logger.info(f"API Response: {response.dict()}")
            return response
        except ValueError as e:
            flow_logger.error(f"API ValueError: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            flow_logger.error(f"API Exception: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/runs/{run_id}", response_model=FlowRunStatusResponse)
    async def get_flow_run_status(
        run_id: str = Path(..., title="Run ID"),
        db: AsyncSession = Depends(get_db)
    ):
        service = FlowService(db)
        flow_run = await service.get_flow_run_status(run_id)
        
        if not flow_run or flow_discovery.get_flow_key_from_path(flow_run.flow_path) != flow_key:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return FlowRunStatusResponse(
            id=flow_run.id,
            status=flow_run.status,
            result=flow_run.result_data,
            events=flow_run.events,
            error_message=flow_run.error_message,
            created_at=flow_run.created_at,
            updated_at=flow_run.updated_at,
            started_at=flow_run.started_at,
            completed_at=flow_run.completed_at
        )
    
    @router.get("/schema", response_model=FlowSchemaResponse)
    async def get_flow_schema():
        try:
            schema = await flow_discovery.get_flow_schema(flow_key)
            return FlowSchemaResponse(flow_schema=schema)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to get flow schema")
    
    return router