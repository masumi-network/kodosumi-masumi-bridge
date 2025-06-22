from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.api.agent_routes import create_flow_router
from masumi_kodosuni_connector.api.mip003_routes import create_mip003_router, create_global_mip003_router
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.api.schemas import FlowListResponse, FlowInfo
from masumi_kodosuni_connector.api.exceptions import (
    AgentServiceException,
    agent_service_exception_handler,
    general_exception_handler
)

app = FastAPI(
    title="Masumi Kodosumi Connector",
    description="Wrapper API for Kodosumi Flow execution with Masumi payment integration",
    version="0.1.0"
)

app.add_exception_handler(AgentServiceException, agent_service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add global MIP-003 router
app.include_router(create_global_mip003_router())

# We'll dynamically add flow routes on startup
_flow_routers_added = False

async def add_flow_routes():
    global _flow_routers_added
    if _flow_routers_added:
        return
    
    try:
        flows = await flow_discovery.get_available_flows()
        for flow_key, flow_info in flows.items():
            # Add original flow router
            flow_router = create_flow_router(flow_key, flow_info)
            app.include_router(flow_router)
            
            # Add MIP-003 compliant router
            mip003_router = create_mip003_router(flow_key, flow_info)
            app.include_router(mip003_router)
        
        _flow_routers_added = True
    except Exception as e:
        # Don't fail startup if flows can't be discovered initially
        print(f"Warning: Could not discover flows on startup: {e}")

@app.get("/")
async def root():
    await add_flow_routes()
    flows = await flow_discovery.get_available_flows()
    return {
        "service": "Masumi Kodosumi Connector",
        "version": "0.1.0",
        "flows": list(flows.keys())
    }

@app.get("/flows", response_model=FlowListResponse)
async def list_flows():
    await add_flow_routes()
    flows = await flow_discovery.get_available_flows()
    flow_list = [
        FlowInfo(
            key=flow_key,
            name=flow_info["name"],
            description=flow_info["description"],
            version=flow_info["version"],
            author=flow_info["author"],
            tags=flow_info["tags"]
        )
        for flow_key, flow_info in flows.items()
    ]
    return FlowListResponse(flows=flow_list)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhooks/masumi/payment")
async def masumi_payment_webhook(
    payment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    payment_id = payment_data.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="Missing payment_id")
    
    service = FlowService(db)
    success = await service.process_payment_confirmation(payment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found or already processed")
    
    return {"status": "payment_processed"}