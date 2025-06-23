import hashlib
import time
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.services.schema_converter import KodosumyToMIP003Converter
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from masumi_kodosuni_connector.config.settings import settings
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
        
        # Convert MIP-003 input data to Kodosumi format
        try:
            kodosumi_schema = await flow_discovery.get_flow_schema(flow_key)
            converted_inputs = self.converter.convert_mip003_to_kodosumi(input_data, kodosumi_schema)
        except Exception:
            # Fallback: use input_data as-is if conversion fails
            converted_inputs = input_data
        
        # Create the flow run with Masumi payment integration
        flow_run = await self.flow_service.create_flow_run(
            flow_key=flow_key,
            inputs=converted_inputs,
            identifier_from_purchaser=identifier_from_purchaser,
            payment_amount=payment_amount
        )
        
        # Get the real payment response data from Masumi
        payment_response = flow_run.payment_response
        print(f"DEBUG: Retrieved payment_response: {payment_response}")
        print(f"DEBUG: Retrieved payment_response type: {type(payment_response)}")
        print(f"DEBUG: payment_response keys: {payment_response.keys() if payment_response else 'None'}")
        print(f"DEBUG: input_hash in payment_response: {'input_hash' in payment_response if payment_response else 'No payment_response'}")
        payment_data = payment_response["data"]
        
        # Extract amounts from Masumi config
        amounts = [
            AmountInfo(
                amount=int(settings.payment_amount),
                unit=settings.payment_unit
            )
        ]
        
        return StartJobResponse(
            status="success",
            job_id=str(flow_run.id),
            blockchainIdentifier=payment_data["blockchainIdentifier"],
            submitResultTime=str(payment_data["submitResultTime"]),
            unlockTime=str(payment_data["unlockTime"]),
            externalDisputeUnlockTime=str(payment_data["externalDisputeUnlockTime"]),
            agentIdentifier=settings.get_agent_identifier(flow_key),
            sellerVKey=settings.seller_vkey,
            identifierFromPurchaser=identifier_from_purchaser,
            amounts=amounts,
            input_hash=payment_response.get("input_hash") or payment_response.get("data", {}).get("input_hash", hashlib.md5(str(input_data).encode()).hexdigest())
        )
    
    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get job status following MIP-003 specification."""
        
        flow_run = await self.flow_service.get_flow_run_status(job_id)
        if not flow_run:
            raise ValueError("Job not found")
        
        print(f"DEBUG: Job {job_id} status check:")
        print(f"DEBUG: FlowRun status: {flow_run.status}")
        print(f"DEBUG: FlowRun kodosumi_run_id: {flow_run.kodosumi_run_id}")
        print(f"DEBUG: FlowRun result_data: {flow_run.result_data}")
        print(f"DEBUG: FlowRun error_message: {flow_run.error_message}")
        
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
        print(f"DEBUG: Mapped to MIP-003 status: {mip003_status}")
        
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
            formatted_result = self._format_result(flow_run.result_data)
            print(f"DEBUG: Formatted result: {formatted_result[:200]}...")
            response.result = formatted_result
            response.message = "Job completed successfully"
        elif mip003_status == JobStatus.FAILED and flow_run.error_message:
            response.message = flow_run.error_message
        
        # TODO: Handle awaiting_input status for interactive flows
        # This would require checking Kodosumi events for input requests
        
        print(f"DEBUG: Final response: status={response.status}, message={response.message}, has_result={bool(response.result)}")
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
            # First try to extract the main output from Kodosumi format
            if "output" in result_data:
                return str(result_data["output"])
            elif "status" in result_data and result_data["status"] == "completed" and "elements" in result_data:
                # Extract results from Kodosumi elements (new format)
                elements = result_data["elements"]
                result_parts = []
                
                for element in elements:
                    if element.get("type") == "markdown" and element.get("text"):
                        text = element["text"]
                        # Skip the initial description/header
                        if len(text) > 200 and any(keyword in text.lower() for keyword in ["result", "analysis", "completed", "generated"]):
                            result_parts.append(text)
                    elif element.get("type") == "text" and element.get("value") and len(element["value"]) > 50:
                        # If a text field has been populated with results
                        result_parts.append(element["value"])
                
                if result_parts:
                    return "\n\n".join(result_parts)
            elif "result" in result_data:
                return str(result_data["result"])
            elif "content" in result_data:
                return str(result_data["content"])
            
            # Return formatted JSON as fallback
            import json
            return json.dumps(result_data, indent=2)
        else:
            return str(result_data)