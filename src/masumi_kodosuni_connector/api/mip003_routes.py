from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.services.mip003_service import MIP003Service
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.api.mip003_schemas import (
    StartJobRequest, StartJobResponse,
    JobStatusResponse,
    ProvideInputRequest, ProvideInputResponse,
    AvailabilityResponse,
    InputSchemaResponse
)


def create_mip003_router(flow_key: str, flow_info: dict) -> APIRouter:
    """Create MIP-003 compliant router for a specific flow."""
    
    router = APIRouter(
        prefix=f"/mip003/{flow_key}",
        tags=[f"MIP-003 {flow_info['name']}"]
    )
    
    @router.post("/start_job", response_model=StartJobResponse)
    async def start_job(
        request: StartJobRequest,
        db: AsyncSession = Depends(get_db)
    ):
        """Start a job following MIP-003 specification."""
        service = MIP003Service(db)
        
        try:
            response = await service.start_job(
                flow_key=flow_key,
                identifier_from_purchaser=request.identifier_from_purchaser,
                input_data=request.input_data,
                payment_amount=None  # TODO: Determine payment amount from flow config
            )
            return response
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            import traceback
            print(f"Start job error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    @router.get("/status", response_model=JobStatusResponse)
    async def get_job_status(
        job_id: str = Query(..., description="Job ID to check status for"),
        db: AsyncSession = Depends(get_db)
    ):
        """Check job status following MIP-003 specification."""
        service = MIP003Service(db)
        
        try:
            response = await service.get_job_status(job_id)
            return response
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.post("/provide_input", response_model=ProvideInputResponse)
    async def provide_input(
        request: ProvideInputRequest,
        db: AsyncSession = Depends(get_db)
    ):
        """Provide additional input for a job."""
        service = MIP003Service(db)
        
        try:
            success = await service.provide_input(
                job_id=request.job_id,
                input_data=request.input_data
            )
            if success:
                return ProvideInputResponse(status="success")
            else:
                raise HTTPException(status_code=400, detail="Failed to provide input")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/availability", response_model=AvailabilityResponse)
    async def check_availability():
        """Check service availability following MIP-003 specification."""
        try:
            # Check if we can reach the flow
            flows = await flow_discovery.get_available_flows()
            if flow_key in flows:
                return AvailabilityResponse(
                    status="available",
                    type="masumi-agent",
                    message=f"{flow_info['name']} is ready to accept jobs"
                )
            else:
                return AvailabilityResponse(
                    status="unavailable",
                    type="masumi-agent",
                    message=f"{flow_info['name']} is not available"
                )
        except Exception as e:
            return AvailabilityResponse(
                status="unavailable",
                type="masumi-agent",
                message=f"Service check failed: {str(e)}"
            )
    
    @router.get("/input_schema")
    async def get_input_schema(
        db: AsyncSession = Depends(get_db)
    ):
        """Get input schema following MIP-003 specification."""
        service = MIP003Service(db)
        
        try:
            input_fields = await service.get_input_schema(flow_key)
            response = InputSchemaResponse(input_data=input_fields)
            # Use custom JSON response to exclude null/unset fields
            return JSONResponse(
                content=response.model_dump(exclude_unset=True, exclude_none=True),
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to get input schema")
    
    return router


def create_global_mip003_router() -> APIRouter:
    """Create global MIP-003 endpoints that work across all flows."""
    
    router = APIRouter(prefix="/mip003", tags=["MIP-003 Global"])
    
    @router.get("/availability", response_model=AvailabilityResponse)
    async def check_global_availability():
        """Check global service availability."""
        try:
            flows = await flow_discovery.get_available_flows()
            if flows:
                return AvailabilityResponse(
                    status="available",
                    type="masumi-agent",
                    message=f"Service is available with {len(flows)} flows"
                )
            else:
                return AvailabilityResponse(
                    status="unavailable",
                    type="masumi-agent",
                    message="No flows available"
                )
        except Exception as e:
            return AvailabilityResponse(
                status="unavailable",
                type="masumi-agent",
                message=f"Service check failed: {str(e)}"
            )
    
    return router