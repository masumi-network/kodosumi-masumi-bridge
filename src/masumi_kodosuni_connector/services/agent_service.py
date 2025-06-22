from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.clients.kodosumi_client import KodosumyClient, KodosumyFlowStatus
from masumi_kodosuni_connector.clients.masumi_client import MasumiClient
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.models.agent_run import FlowRun, FlowRunStatus
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery


class FlowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = FlowRunRepository(session)
        self.kodosumi_client = KodosumyClient()
        self.masumi_client = MasumiClient()
    
    async def create_flow_run(self, flow_key: str, inputs: Dict[str, Any], payment_amount: Optional[float] = None) -> FlowRun:
        # Get flow info from discovery service
        flows = await flow_discovery.get_available_flows()
        flow_info = flows.get(flow_key)
        
        if not flow_info:
            raise ValueError(f"Unknown flow: {flow_key}")
        
        masumi_payment_id = None
        if payment_amount and payment_amount > 0:
            payment_response = await self.masumi_client.create_payment_request(
                amount=payment_amount,
                metadata={"flow_key": flow_key}
            )
            masumi_payment_id = payment_response.get("payment_id")
        
        flow_run = await self.repository.create(
            flow_path=flow_info["url"],
            flow_name=flow_info["name"],
            inputs=inputs,
            masumi_payment_id=masumi_payment_id
        )
        
        if not masumi_payment_id:
            await self._launch_kodosumi_flow(flow_run)
        
        return flow_run
    
    async def get_flow_run_status(self, run_id: int) -> Optional[FlowRun]:
        return await self.repository.get_by_id(run_id)
    
    async def process_payment_confirmation(self, payment_id: str) -> bool:
        flow_run = await self.repository.get_by_masumi_payment_id(payment_id)
        if not flow_run:
            return False
        
        is_confirmed = await self.masumi_client.verify_payment(payment_id)
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
            return
        
        try:
            # Get current status
            status_data = await self.kodosumi_client.get_flow_status(flow_run.kodosumi_run_id)
            kodosumi_status = status_data.get("status")
            
            # Map Kodosumi status to our status
            if kodosumi_status == KodosumyFlowStatus.RUNNING and flow_run.status == FlowRunStatus.STARTING:
                await self.repository.update_status(flow_run.id, FlowRunStatus.RUNNING)
            elif kodosumi_status == KodosumyFlowStatus.FINISHED:
                # Get final result and events
                result_data = await self.kodosumi_client.get_flow_result(flow_run.kodosumi_run_id)
                events = await self.kodosumi_client.get_flow_events(flow_run.kodosumi_run_id)
                
                await self.repository.update_result(flow_run.id, result_data)
                await self.repository.update_events(flow_run.id, events)
                await self.repository.update_status(flow_run.id, FlowRunStatus.FINISHED)
            elif kodosumi_status == KodosumyFlowStatus.ERROR:
                # Try to get error details from events
                events = await self.kodosumi_client.get_flow_events(flow_run.kodosumi_run_id)
                error_msg = "Flow execution failed"
                
                # Look for error events
                for event in reversed(events):
                    if event.get("event") == "error":
                        error_msg = event.get("data", {}).get("message", error_msg)
                        break
                
                await self.repository.update_events(flow_run.id, events)
                await self.repository.update_error(flow_run.id, error_msg)
        except Exception as e:
            await self.repository.update_error(flow_run.id, f"Failed to update from Kodosumi: {str(e)}")