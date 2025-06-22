import hashlib
import time
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.services.schema_converter import KodosumyToMIP003Converter
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from masumi_kodosuni_connector.api.mip003_schemas import (
    JobStatus, StartJobResponse, JobStatusResponse, AmountInfo, InputField
)


class MIP003Service:
    """Service to handle MIP-003 compliant job management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.flow_service = FlowService(session)
        self.converter = KodosumyToMIP003Converter()
    
    async def start_job(
        self, 
        flow_key: str, 
        identifier_from_purchaser: str, 
        input_data: Dict[str, Any],
        payment_amount: Optional[float] = None
    ) -> StartJobResponse:
        """Start a new job following MIP-003 specification."""
        
        # Get flow info
        flows = await flow_discovery.get_available_flows()
        flow_info = flows.get(flow_key)
        
        if not flow_info:
            raise ValueError(f"Unknown flow: {flow_key}")
        
        # Create the flow run
        flow_run = await self.flow_service.create_flow_run(
            flow_key=flow_key,
            inputs=input_data,
            payment_amount=payment_amount
        )
        
        # Generate MIP-003 required fields
        current_time = int(time.time())
        blockchain_identifier = f"block_{uuid.uuid4().hex[:12]}"
        input_hash = hashlib.md5(str(input_data).encode()).hexdigest()
        
        # Calculate times (example values - adjust based on your requirements)
        submit_result_time = current_time + (24 * 60 * 60)  # 24 hours
        unlock_time = current_time + (48 * 60 * 60)  # 48 hours
        external_dispute_unlock_time = current_time + (72 * 60 * 60)  # 72 hours
        
        # Default payment amount if not specified
        if payment_amount is None:
            payment_amount = 3.0  # 3 ADA default
        
        amounts = [
            AmountInfo(
                amount=int(payment_amount * 1_000_000),  # Convert ADA to lovelace
                unit="lovelace"
            )
        ]
        
        return StartJobResponse(
            status="success",
            job_id=str(flow_run.id),
            blockchainIdentifier=blockchain_identifier,
            submitResultTime=submit_result_time,
            unlockTime=unlock_time,
            externalDisputeUnlockTime=external_dispute_unlock_time,
            agentIdentifier=flow_key,
            sellerVKey="addr1qxlkjl23k4jlksdjfl234jlksdf",  # TODO: Get from actual wallet
            identifierFromPurchaser=identifier_from_purchaser,
            amounts=amounts,
            input_hash=input_hash
        )
    
    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get job status following MIP-003 specification."""
        
        try:
            job_id_int = int(job_id)
        except ValueError:
            raise ValueError("Invalid job_id format")
        
        flow_run = await self.flow_service.get_flow_run_status(job_id_int)
        if not flow_run:
            raise ValueError("Job not found")
        
        # Map FlowRunStatus to MIP-003 JobStatus
        status_mapping = {
            FlowRunStatus.PENDING_PAYMENT: JobStatus.AWAITING_PAYMENT,
            FlowRunStatus.PAYMENT_CONFIRMED: JobStatus.PENDING,
            FlowRunStatus.STARTING: JobStatus.RUNNING,
            FlowRunStatus.RUNNING: JobStatus.RUNNING,
            FlowRunStatus.FINISHED: JobStatus.COMPLETED,
            FlowRunStatus.ERROR: JobStatus.FAILED,
            FlowRunStatus.CANCELLED: JobStatus.FAILED
        }
        
        mip003_status = status_mapping.get(flow_run.status, JobStatus.PENDING)
        
        # Prepare response
        response = JobStatusResponse(
            job_id=job_id,
            status=mip003_status
        )
        
        # Add status-specific fields
        if mip003_status == JobStatus.AWAITING_PAYMENT:
            response.message = "Waiting for payment confirmation"
        elif mip003_status == JobStatus.RUNNING:
            response.message = "Job is being processed"
        elif mip003_status == JobStatus.COMPLETED and flow_run.result_data:
            response.result = self._format_result(flow_run.result_data)
        elif mip003_status == JobStatus.FAILED and flow_run.error_message:
            response.message = flow_run.error_message
        
        # TODO: Handle awaiting_input status for interactive flows
        # This would require checking Kodosumi events for input requests
        
        return response
    
    async def provide_input(self, job_id: str, input_data: Dict[str, Any]) -> bool:
        """Provide additional input for a job (for interactive flows)."""
        # TODO: Implement input provision for interactive Kodosumi flows
        # This would involve sending the input back to Kodosumi
        return True
    
    async def get_input_schema(self, flow_key: str) -> List[InputField]:
        """Get the input schema for a flow in MIP-003 format."""
        
        try:
            # Get the Kodosumi schema
            kodosumi_schema = await flow_discovery.get_flow_schema(flow_key)
            
            # Convert to MIP-003 format
            mip003_fields = self.converter.convert_kodosumi_schema(kodosumi_schema)
            
            # If conversion failed or returned empty, create a simple default
            if not mip003_fields:
                flows = await flow_discovery.get_available_flows()
                flow_info = flows.get(flow_key, {"name": flow_key})
                mip003_fields = self.converter.create_simple_schema(flow_info["name"])
            
            return mip003_fields
            
        except Exception:
            # Fallback to simple schema on error
            flows = await flow_discovery.get_available_flows()
            flow_info = flows.get(flow_key, {"name": flow_key})
            return self.converter.create_simple_schema(flow_info["name"])
    
    def _format_result(self, result_data: Dict[str, Any]) -> str:
        """Format the result data for MIP-003 response."""
        if isinstance(result_data, dict):
            # Try to extract main result content
            if "output" in result_data:
                return str(result_data["output"])
            elif "result" in result_data:
                return str(result_data["result"])
            elif "content" in result_data:
                return str(result_data["content"])
            else:
                # Return formatted JSON
                import json
                return json.dumps(result_data, indent=2)
        else:
            return str(result_data)