from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient, KodosumyFlowStatus, interpret_kodosumi_status
from masumi_kodosuni_connector.clients.masumi_client import MasumiClient
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery


class FlowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = FlowRunRepository(session)
        self.kodosumi_client = KodosumyClient()
        # MasumiClient will be created per-flow when needed
    
    async def create_flow_run(
        self, 
        flow_key: str, 
        inputs: Dict[str, Any], 
        identifier_from_purchaser: str,
        payment_amount: Optional[float] = None
    ) -> FlowRun:
        # Get flow info from discovery service
        flows = await flow_discovery.get_available_flows()
        flow_info = flows.get(flow_key)
        
        if not flow_info:
            raise ValueError(f"Unknown flow: {flow_key}")
        
        # Create flow run first to get job_id
        flow_run = await self.repository.create(
            flow_path=flow_info["url"],
            flow_name=flow_info["name"],
            inputs=inputs,
            masumi_payment_id=None  # Will be set after payment creation
        )
        
        # Create MasumiClient for this specific flow
        try:
            masumi_client = MasumiClient(flow_key)
        except ValueError as e:
            # If no agent identifier is configured, mark as error
            await self.repository.update_error(flow_run.id, str(e))
            raise
        
        # Always create a payment request (payment is required)
        try:
            payment_response = await masumi_client.create_payment_request(
                identifier_from_purchaser=identifier_from_purchaser,
                input_data=inputs,
                job_id=flow_run.id
            )
            
            # Update flow run with payment ID
            masumi_payment_id = payment_response["data"]["blockchainIdentifier"]
            await self.repository.update_payment_id(flow_run.id, masumi_payment_id)
            
            # Store payment response data in flow run for MIP-003 response
            await self.repository.update_payment_response(flow_run.id, payment_response)
            flow_run.payment_response = payment_response  # Also set in memory for immediate use
            print(f"DEBUG: Stored payment_response: {payment_response}")
            print(f"DEBUG: Payment response type: {type(payment_response)}")
            
            # Start payment monitoring
            await self._start_payment_monitoring(flow_run.id, masumi_client)
            
        except Exception as e:
            # If payment creation fails, mark flow run as error
            await self.repository.update_error(flow_run.id, f"Payment creation failed: {str(e)}")
            raise
        
        return flow_run
    
    async def get_flow_run_status(self, run_id: str) -> Optional[FlowRun]:
        return await self.repository.get_by_id(run_id)
    
    async def _start_payment_monitoring(self, job_id: str, masumi_client: MasumiClient) -> None:
        """Start monitoring payment status for a job."""
        async def payment_callback(payment_id: str):
            await self._handle_payment_confirmation(job_id, payment_id, masumi_client)
        
        try:
            await masumi_client.start_payment_monitoring(job_id, payment_callback)
        except Exception as e:
            await self.repository.update_error(job_id, f"Payment monitoring failed: {str(e)}")
    
    async def _handle_payment_confirmation(self, job_id: str, payment_id: str, masumi_client: MasumiClient) -> None:
        """Handle payment confirmation and start Kodosumi job."""
        try:
            # Get flow run
            flow_run = await self.repository.get_by_id(job_id)
            if not flow_run:
                return
            
            # Update status to payment confirmed
            await self.repository.update_status(job_id, FlowRunStatus.PAYMENT_CONFIRMED)
            
            # Launch Kodosumi flow
            await self._launch_kodosumi_flow(flow_run)
            
        except Exception as e:
            await self.repository.update_error(job_id, f"Payment confirmation handling failed: {str(e)}")
    
    async def process_payment_confirmation(self, payment_id: str) -> bool:
        """Legacy method for backward compatibility."""
        flow_run = await self.repository.get_by_masumi_payment_id(payment_id)
        if not flow_run:
            return False
        
        # For legacy support, we'll need to determine the flow_key from the flow_run
        # This is a simplified approach - in practice, we might store flow_key in the database
        flow_key = flow_run.flow_path.strip('/').replace('/', '_').replace('-', '_')
        try:
            masumi_client = MasumiClient(flow_key)
            is_confirmed = await masumi_client.verify_payment(flow_run.id)
        except ValueError:
            # Agent not configured
            return False
        if is_confirmed:
            await self.repository.update_status(flow_run.id, FlowRunStatus.PAYMENT_CONFIRMED)
            await self._launch_kodosumi_flow(flow_run)
            return True
        
        return False
    
    async def _launch_kodosumi_flow(self, flow_run: FlowRun) -> None:
        try:
            kodosumi_run_id = await self.kodosumi_client.launch_flow(
                flow_run.flow_path,
                flow_run.inputs
            )
            
            if kodosumi_run_id:
                await self.repository.update_status(
                    flow_run.id,
                    FlowRunStatus.STARTING,
                    kodosumi_run_id=kodosumi_run_id
                )
        except Exception as e:
            await self.repository.update_error(flow_run.id, str(e))
    
    async def update_flow_run_from_kodosumi(self, flow_run: FlowRun) -> None:
        if not flow_run.kodosumi_run_id:
            print(f"DEBUG: No kodosumi_run_id for flow_run {flow_run.id}")
            return
        
        try:
            print(f"DEBUG: Updating flow_run {flow_run.id} from Kodosumi")
            print(f"DEBUG: Current status: {flow_run.status}")
            print(f"DEBUG: Kodosumi run ID: {flow_run.kodosumi_run_id}")
            
            # Get current status
            status_data = await self.kodosumi_client.get_flow_status(flow_run.flow_path, flow_run.kodosumi_run_id)
            print(f"DEBUG: Kodosumi status_data keys: {list(status_data.keys()) if status_data else 'None'}")
            
            kodosumi_status = interpret_kodosumi_status(status_data)
            print(f"DEBUG: Interpreted Kodosumi status: {kodosumi_status}")
            
            # Map Kodosumi status to our status
            if kodosumi_status == KodosumyFlowStatus.RUNNING and flow_run.status == FlowRunStatus.STARTING:
                print(f"DEBUG: Updating status from STARTING to RUNNING")
                await self.repository.update_status(flow_run.id, FlowRunStatus.RUNNING)
            elif kodosumi_status == KodosumyFlowStatus.FINISHED:
                print(f"DEBUG: Job finished in Kodosumi, getting results")
                
                # Get final result and events
                result_data = await self.kodosumi_client.get_flow_result(flow_run.flow_path, flow_run.kodosumi_run_id)
                events = await self.kodosumi_client.get_flow_events(flow_run.flow_path, flow_run.kodosumi_run_id)
                
                print(f"DEBUG: Result data type: {type(result_data)}")
                print(f"DEBUG: Result data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'Not a dict'}")
                print(f"DEBUG: Events count: {len(events) if events else 0}")
                
                await self.repository.update_result(flow_run.id, result_data)
                await self.repository.update_events(flow_run.id, events)
                await self.repository.update_status(flow_run.id, FlowRunStatus.FINISHED)
                
                print(f"DEBUG: Updated flow_run {flow_run.id} to FINISHED with results")
                
                # Complete the payment with Masumi
                if flow_run.masumi_payment_id:
                    try:
                        await self.masumi_client.complete_payment(
                            flow_run.id, 
                            flow_run.masumi_payment_id, 
                            result_data
                        )
                        # Stop payment monitoring
                        self.masumi_client.stop_payment_monitoring(flow_run.id)
                    except Exception as e:
                        # Log error but don't fail the job completion
                        logger = __import__('structlog').get_logger()
                        logger.error(f"Failed to complete payment for job {flow_run.id}: {str(e)}")
            elif kodosumi_status == KodosumyFlowStatus.ERROR:
                # Try to get error details from events
                events = await self.kodosumi_client.get_flow_events(flow_run.flow_path, flow_run.kodosumi_run_id)
                error_msg = "Flow execution failed"
                
                # Look for error events
                for event in reversed(events):
                    if event.get("event") == "error":
                        error_msg = event.get("data", {}).get("message", error_msg)
                        break
                
                await self.repository.update_events(flow_run.id, events)
                await self.repository.update_error(flow_run.id, error_msg)
        except Exception as e:
            print(f"DEBUG: Exception in update_flow_run_from_kodosumi: {e}")
            print(f"DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            await self.repository.update_error(flow_run.id, f"Failed to update from Kodosumi: {str(e)}")