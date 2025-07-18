from typing import Dict, Any, Optional
import json
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient, KodosumyFlowStatus, interpret_kodosumi_status
from masumi_kodosuni_connector.clients.masumi_client import MasumiClient
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.config.logging import get_logger
from masumi_kodosuni_connector.config.settings import settings

# Get the dedicated flow submission logger
flow_logger = get_logger("flow_submission")


def cardano_slot_to_unix_timestamp(slot_number: int, network: str = "preprod") -> int:
    """Convert Cardano slot number to Unix timestamp.
    
    Args:
        slot_number: Cardano slot number
        network: Network type ("mainnet" or "preprod")
        
    Returns:
        Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)
    """
    # First check if this looks like a timestamp in milliseconds
    # Unix timestamp in milliseconds would be around 1.7 trillion for current time
    current_time_ms = int(time.time() * 1000)
    if slot_number > current_time_ms / 2 and slot_number < current_time_ms * 10:
        # This looks like a timestamp in milliseconds, convert to seconds
        return slot_number // 1000
    
    # Check if this is already a Unix timestamp in seconds
    current_time_s = int(time.time())
    if slot_number > current_time_s / 2 and slot_number < current_time_s * 10:
        # This is already a Unix timestamp in seconds
        return slot_number
    
    # Otherwise, treat as a Cardano slot number
    if network.lower() == "mainnet":
        # Cardano mainnet genesis: 2017-09-23 21:44:51 UTC (slot 0)
        genesis_time = 1506203091
        slot_length = 1
    else:  # preprod or any other network defaults to preprod
        # Cardano preprod genesis: 2022-06-01 00:00:00 UTC (slot 0)
        genesis_time = 1654041600
        slot_length = 1
    
    return genesis_time + (slot_number * slot_length)


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
        flow_logger.info(f"=== FLOW SUBMISSION STARTED ===")
        flow_logger.info(f"Flow Key: {flow_key}")
        flow_logger.info(f"Inputs: {json.dumps(inputs, indent=2)}")
        flow_logger.info(f"Identifier: {identifier_from_purchaser}")
        flow_logger.info(f"Payment Amount: {payment_amount}")
        
        # Get flow info from discovery service
        flows = await flow_discovery.get_available_flows()
        flow_info = flows.get(flow_key)
        flow_logger.info(f"Available flows: {list(flows.keys())}")
        
        if not flow_info:
            flow_logger.error(f"Unknown flow: {flow_key}")
            raise ValueError(f"Unknown flow: {flow_key}")
        
        flow_logger.info(f"Flow info found: {json.dumps(flow_info, indent=2)}")
        
        # Create flow run first to get job_id
        flow_run = await self.repository.create(
            flow_path=flow_info["url"],
            flow_name=flow_info["name"],
            inputs=inputs,
            masumi_payment_id=None  # Will be set after payment creation
        )
        flow_logger.info(f"Flow run created with ID: {flow_run.id}")
        
        # Create MasumiClient for this specific flow
        try:
            masumi_client = MasumiClient(flow_key)
            flow_logger.info(f"MasumiClient created successfully for flow_key: {flow_key}")
        except ValueError as e:
            flow_logger.error(f"Failed to create MasumiClient: {str(e)}")
            # If no agent identifier is configured, mark as error
            await self.repository.update_error(flow_run.id, str(e))
            raise
        
        # Always create a payment request (payment is required)
        try:
            flow_logger.info(f"Creating payment request for flow run {flow_run.id}")
            payment_response = await masumi_client.create_payment_request(
                identifier_from_purchaser=identifier_from_purchaser,
                input_data=inputs,
                job_id=flow_run.id
            )
            flow_logger.info(f"Payment response received: {json.dumps(payment_response, indent=2)}")
            
            # Update flow run with payment ID
            masumi_payment_id = payment_response["data"]["blockchainIdentifier"]
            await self.repository.update_payment_id(flow_run.id, masumi_payment_id)
            flow_logger.info(f"Updated flow run with payment ID: {masumi_payment_id}")
            
            # Store payment response data in flow run for MIP-003 response
            # Also store the agent identifier for later use in completion
            payment_response_with_agent = payment_response.copy()
            payment_response_with_agent['agent_identifier'] = masumi_client.agent_identifier
            payment_response_with_agent['flow_key'] = flow_key
            
            await self.repository.update_payment_response(flow_run.id, payment_response_with_agent)
            flow_run.payment_response = payment_response_with_agent  # Also set in memory for immediate use
            flow_logger.info(f"Stored payment response with agent identifier in database")
            
            # Store submitResultTime as timeout_at for job timeout handling
            submit_result_time = payment_response["data"]["submitResultTime"]
            if isinstance(submit_result_time, str):
                submit_result_time = int(submit_result_time)
            
            # Convert Cardano slot to Unix timestamp if needed
            # Check if this looks like a slot number (very large number compared to current time)
            current_time = datetime.utcnow().timestamp()
            if submit_result_time > current_time * 10:  # If more than 10x current time, likely a slot number
                submit_result_time = cardano_slot_to_unix_timestamp(submit_result_time, settings.network)
                flow_logger.info(f"Converted Cardano slot to Unix timestamp: {submit_result_time}")
            
            timeout_at = datetime.utcfromtimestamp(submit_result_time)
            await self.repository.update_timeout(flow_run.id, timeout_at)
            flow_logger.info(f"Set job timeout to {timeout_at.isoformat()} based on submitResultTime")
            
            # Start payment monitoring
            flow_logger.info(f"Starting payment monitoring for flow run {flow_run.id}")
            await self._start_payment_monitoring(flow_run.id, masumi_client)
            
        except Exception as e:
            flow_logger.error(f"Payment creation failed for flow run {flow_run.id}: {str(e)}")
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
        flow_logger.info(f"=== PAYMENT CONFIRMATION RECEIVED ===")
        flow_logger.info(f"Job ID: {job_id}")
        flow_logger.info(f"Payment ID: {payment_id}")
        
        try:
            # Get flow run
            flow_run = await self.repository.get_by_id(job_id)
            if not flow_run:
                flow_logger.error(f"Flow run not found for job_id: {job_id}")
                return
            
            flow_logger.info(f"Flow run found: {flow_run.flow_name}")
            
            # Update status to payment confirmed
            await self.repository.update_status(job_id, FlowRunStatus.PAYMENT_CONFIRMED)
            flow_logger.info(f"Updated status to PAYMENT_CONFIRMED")
            
            # Launch Kodosumi flow
            flow_logger.info(f"Launching Kodosumi flow...")
            await self._launch_kodosumi_flow(flow_run)
            
        except Exception as e:
            flow_logger.error(f"Payment confirmation handling failed: {str(e)}")
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
        flow_logger.info(f"=== LAUNCHING KODOSUMI FLOW ===")
        flow_logger.info(f"Flow run ID: {flow_run.id}")
        flow_logger.info(f"Flow path: {flow_run.flow_path}")
        flow_logger.info(f"Flow inputs: {json.dumps(flow_run.inputs, indent=2)}")
        
        try:
            kodosumi_run_id = await self.kodosumi_client.launch_flow(
                flow_run.flow_path,
                flow_run.inputs
            )
            flow_logger.info(f"Kodosumi launch response: {kodosumi_run_id}")
            
            if kodosumi_run_id:
                await self.repository.update_status(
                    flow_run.id,
                    FlowRunStatus.STARTING,
                    kodosumi_run_id=kodosumi_run_id
                )
                flow_logger.info(f"Updated flow run status to STARTING with kodosumi_run_id: {kodosumi_run_id}")
            else:
                flow_logger.error(f"No kodosumi_run_id returned from launch")
                await self.repository.update_error(flow_run.id, "Kodosumi launch failed: No run ID returned")
        except Exception as e:
            flow_logger.error(f"Failed to launch Kodosumi flow: {str(e)}")
            await self.repository.update_error(flow_run.id, str(e))
    
    async def update_flow_run_from_kodosumi(self, flow_run: FlowRun) -> None:
        if not flow_run.kodosumi_run_id:
            flow_logger.debug(f"No kodosumi_run_id for flow_run {flow_run.id}")
            return
        
        try:
            flow_logger.info(f"=== UPDATING FLOW FROM KODOSUMI ===")
            flow_logger.info(f"Flow run ID: {flow_run.id}")
            flow_logger.info(f"Current status: {flow_run.status}")
            flow_logger.info(f"Kodosumi run ID: {flow_run.kodosumi_run_id}")
            
            # Get current status
            status_data = await self.kodosumi_client.get_flow_status(flow_run.flow_path, flow_run.kodosumi_run_id)
            flow_logger.info(f"Kodosumi status_data: {json.dumps(status_data, indent=2) if status_data else 'None'}")
            
            kodosumi_status = interpret_kodosumi_status(status_data)
            flow_logger.info(f"Interpreted Kodosumi status: {kodosumi_status}")
            
            # Map Kodosumi status to our status
            if kodosumi_status == KodosumyFlowStatus.RUNNING and flow_run.status == FlowRunStatus.STARTING:
                flow_logger.info(f"Updating status from STARTING to RUNNING")
                await self.repository.update_status(flow_run.id, FlowRunStatus.RUNNING)
            elif kodosumi_status == KodosumyFlowStatus.FINISHED:
                flow_logger.info(f"=== JOB FINISHED IN KODOSUMI - GETTING RESULTS ===")
                
                # Get final result and events
                result_data = await self.kodosumi_client.get_flow_result(flow_run.flow_path, flow_run.kodosumi_run_id)
                events = await self.kodosumi_client.get_flow_events(flow_run.flow_path, flow_run.kodosumi_run_id)
                
                flow_logger.info(f"Result data received: {json.dumps(result_data, indent=2) if result_data else 'None'}")
                flow_logger.info(f"Events count: {len(events) if events else 0}")
                if events:
                    flow_logger.info(f"Events: {json.dumps(events, indent=2)}")
                
                await self.repository.update_result(flow_run.id, result_data)
                await self.repository.update_events(flow_run.id, events)
                await self.repository.update_status(flow_run.id, FlowRunStatus.FINISHED)
                
                flow_logger.info(f"=== FLOW COMPLETED SUCCESSFULLY ===")
                flow_logger.info(f"Updated flow_run {flow_run.id} to FINISHED with results")
                
                # Complete the payment with Masumi
                if flow_run.masumi_payment_id:
                    flow_logger.info(f"=== MASUMI SUBMISSION STARTING ===")
                    flow_logger.info(f"Flow run ID: {flow_run.id}")
                    flow_logger.info(f"Masumi payment ID: {flow_run.masumi_payment_id}")
                    
                    try:
                        # Extract agent identifier and flow_key from stored payment response
                        agent_identifier = None
                        saved_flow_key = None
                        blockchain_identifier = None
                        identifier_from_purchaser = None
                        
                        if hasattr(flow_run, 'payment_response') and flow_run.payment_response:
                            payment_data = flow_run.payment_response.get('data', {}) if flow_run.payment_response else {}
                            blockchain_identifier = payment_data.get('blockchainIdentifier') if payment_data else None
                            identifier_from_purchaser = payment_data.get('identifierFromPurchaser') if payment_data else None
                            agent_identifier = flow_run.payment_response.get('agent_identifier') if flow_run.payment_response else None
                            saved_flow_key = flow_run.payment_response.get('flow_key') if flow_run.payment_response else None
                            
                            flow_logger.info(f"Retrieved from stored payment_response:")
                            flow_logger.info(f"  - blockchain_identifier: {blockchain_identifier}")
                            flow_logger.info(f"  - identifier_from_purchaser: {identifier_from_purchaser}")
                            flow_logger.info(f"  - agent_identifier: {agent_identifier}")
                            flow_logger.info(f"  - saved_flow_key: {saved_flow_key}")
                        else:
                            flow_logger.warning(f"No payment_response found in flow_run")
                        
                        if not agent_identifier:
                            flow_logger.error(f"No agent_identifier found in payment_response for job {flow_run.id}")
                            flow_logger.error(f"Cannot complete Masumi submission without agent identifier")
                            raise ValueError(f"Missing agent_identifier in payment_response")
                        
                        try:
                            # Create MasumiClient with the saved agent identifier directly
                            masumi_client = MasumiClient.with_agent_identifier(agent_identifier)
                            flow_logger.info(f"MasumiClient created with saved agent_identifier: {agent_identifier}")
                            
                            if not blockchain_identifier:
                                # Fallback: use masumi_payment_id as blockchain_identifier
                                blockchain_identifier = flow_run.masumi_payment_id
                                flow_logger.info(f"Using fallback blockchain_identifier: {blockchain_identifier}")
                            
                            if not identifier_from_purchaser:
                                flow_logger.error(f"Missing identifier_from_purchaser for job {flow_run.id}")
                                # Try to extract from original request or use a fallback
                                identifier_from_purchaser = f"fallback_{flow_run.id}"
                                flow_logger.info(f"Using fallback identifier_from_purchaser: {identifier_from_purchaser}")
                            
                            flow_logger.info(f"=== CALLING MASUMI COMPLETE_PAYMENT ===")
                            flow_logger.info(f"Parameters:")
                            flow_logger.info(f"  - job_id: {flow_run.id}")
                            flow_logger.info(f"  - blockchain_identifier: {blockchain_identifier}")
                            flow_logger.info(f"  - identifier_from_purchaser: {identifier_from_purchaser}")
                            flow_logger.info(f"  - result_data type: {type(result_data)}")
                            flow_logger.info(f"  - result_data keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'Not a dict'}")
                            
                            await masumi_client.complete_payment(
                                flow_run.id, 
                                blockchain_identifier, 
                                result_data,
                                identifier_from_purchaser
                            )
                            
                            flow_logger.info(f"=== MASUMI SUBMISSION SUCCESSFUL ===")
                            flow_logger.info(f"Payment completion succeeded for job {flow_run.id}")
                            
                            # Stop payment monitoring
                            masumi_client.stop_payment_monitoring(flow_run.id)
                            flow_logger.info(f"Payment monitoring stopped for job {flow_run.id}")
                            
                        except ValueError as e:
                            # Agent not configured for payment, skip completion
                            flow_logger.warning(f"=== MASUMI SUBMISSION SKIPPED ===")
                            flow_logger.warning(f"Cannot create MasumiClient: {str(e)}")
                            flow_logger.warning(f"Skipping payment completion for job {flow_run.id}")
                            
                    except Exception as e:
                        # Log error but don't fail the job completion
                        flow_logger.error(f"=== MASUMI SUBMISSION FAILED ===")
                        flow_logger.error(f"Failed to complete payment for job {flow_run.id}")
                        flow_logger.error(f"Error type: {type(e).__name__}")
                        flow_logger.error(f"Error message: {str(e)}")
                        flow_logger.error(f"Full error details: {repr(e)}")
                else:
                    flow_logger.warning(f"=== NO MASUMI PAYMENT ID ===")
                    flow_logger.warning(f"No masumi_payment_id found for flow_run {flow_run.id}, skipping Masumi submission")
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
    
    async def mark_job_as_timeout(self, flow_run_id: str):
        """Mark a job as timed out and stop processing it."""
        # Update status to TIMEOUT and set error message and completion time
        from sqlalchemy import update
        result = await self.repository.session.execute(
            update(FlowRun)
            .where(FlowRun.id == flow_run_id)
            .values(
                status=FlowRunStatus.TIMEOUT,
                error_message="Job timed out based on submitResultTime",
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.repository.session.commit()
    
    async def resume_payment_monitoring(self) -> None:
        """Resume payment monitoring for all pending payment jobs after service restart."""
        flow_logger.info("=== RESUMING PAYMENT MONITORING ===")
        
        try:
            # Get all jobs waiting for payment
            pending_jobs = await self.repository.get_pending_payment_runs()
            
            if not pending_jobs:
                flow_logger.info("No pending payment jobs found to resume monitoring for")
                return
            
            flow_logger.info(f"Found {len(pending_jobs)} pending payment jobs to resume monitoring")
            
            recovery_count = 0
            error_count = 0
            
            for flow_run in pending_jobs:
                try:
                    flow_logger.info(f"Resuming payment monitoring for job {flow_run.id}")
                    
                    # Extract flow_key from stored payment response or derive from flow_path
                    flow_key = None
                    if hasattr(flow_run, 'payment_response') and flow_run.payment_response:
                        flow_key = flow_run.payment_response.get('flow_key')
                    
                    if not flow_key:
                        # Fallback: derive flow_key from flow_path
                        flow_key = flow_run.flow_path.strip('/').replace('/', '_').replace('-', '_')
                        flow_logger.info(f"Derived flow_key from flow_path: {flow_key}")
                    
                    # Create MasumiClient for this flow
                    try:
                        masumi_client = MasumiClient(flow_key)
                        flow_logger.info(f"Created MasumiClient for flow_key: {flow_key}")
                    except ValueError as e:
                        flow_logger.error(f"Failed to create MasumiClient for job {flow_run.id}: {str(e)}")
                        # Mark job as error if agent identifier is not configured
                        await self.repository.update_error(flow_run.id, f"Payment monitoring recovery failed: {str(e)}")
                        error_count += 1
                        continue
                    
                    # Resume payment monitoring
                    await self._start_payment_monitoring(flow_run.id, masumi_client)
                    recovery_count += 1
                    
                    flow_logger.info(f"Successfully resumed payment monitoring for job {flow_run.id}")
                    
                except Exception as e:
                    flow_logger.error(f"Failed to resume payment monitoring for job {flow_run.id}: {str(e)}")
                    # Mark job as error
                    await self.repository.update_error(flow_run.id, f"Payment monitoring recovery failed: {str(e)}")
                    error_count += 1
            
            flow_logger.info(f"Payment monitoring recovery completed: {recovery_count} successful, {error_count} errors")
            
        except Exception as e:
            flow_logger.error(f"Payment monitoring recovery failed: {str(e)}")
            raise