from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import os
from masumi_kodosuni_connector.api.agent_routes import create_flow_router
from masumi_kodosuni_connector.api.mip003_routes import create_mip003_router, create_global_mip003_router
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.database.repositories import FlowRunRepository
from masumi_kodosuni_connector.services.agent_service import FlowService
from masumi_kodosuni_connector.services.flow_discovery_service import flow_discovery
from masumi_kodosuni_connector.api.schemas import FlowListResponse, FlowInfo
from masumi_kodosuni_connector.api.exceptions import (
    AgentServiceException,
    agent_service_exception_handler,
    general_exception_handler
)
from masumi_kodosuni_connector.config.settings import settings

app = FastAPI(
    title="Masumi Kodosumi Connector",
    description="Wrapper API for Kodosumi Flow execution with Masumi payment integration",
    version="0.1.0"
)

app.add_exception_handler(AgentServiceException, agent_service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Security setup
security = HTTPBearer(auto_error=False)

async def get_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate API key for protected endpoints."""
    if not settings.api_key:
        # If no API key is configured, allow access (for backwards compatibility)
        return True
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Add global MIP-003 router
app.include_router(create_global_mip003_router())

# We'll dynamically add flow routes on startup
_flow_routers_added = False

async def add_flow_routes(force_reload=False):
    global _flow_routers_added
    if _flow_routers_added and not force_reload:
        return
    
    try:
        flows = await flow_discovery.get_available_flows()
        for flow_key, flow_info in flows.items():
            # Only add routers for agents with configured identifiers
            if settings.is_agent_enabled(flow_key):
                # Add original flow router
                flow_router = create_flow_router(flow_key, flow_info)
                app.include_router(flow_router)
                
                # Add MIP-003 compliant router
                mip003_router = create_mip003_router(flow_key, flow_info)
                app.include_router(mip003_router)
        
        _flow_routers_added = True
        # Force regeneration of OpenAPI schema to include new routes
        app.openapi_schema = None
    except Exception as e:
        # Don't fail startup if flows can't be discovered initially
        print(f"Warning: Could not discover flows on startup: {e}")

@app.get("/")
async def root():
    # Initialize agent config cache if needed
    from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
    if not agent_config_manager._cache_valid:
        await agent_config_manager.refresh_cache()
    
    await add_flow_routes()
    flows = await flow_discovery.get_available_flows()
    enabled_flows = [flow_key for flow_key in flows.keys() if settings.is_agent_enabled(flow_key)]
    return {
        "service": "Masumi Kodosumi Connector",
        "version": "0.1.0",
        "flows": enabled_flows
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
        if settings.is_agent_enabled(flow_key)  # Only show enabled agents
    ]
    return FlowListResponse(flows=flow_list)

@app.get("/admin/flows")
async def list_all_flows_for_admin(_: bool = Depends(get_api_key)):
    """Get all flows (both registered and non-registered) for admin dashboard."""
    # Import here to avoid circular imports
    from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
    
    await add_flow_routes()
    flows = await flow_discovery.get_available_flows()
    
    # Sync discovered flows with database and refresh cache
    await agent_config_manager.sync_with_flows(flows)
    
    flow_list = []
    for flow_key, flow_info in flows.items():
        is_enabled = agent_config_manager.is_agent_enabled(flow_key)
        agent_identifier = agent_config_manager.get_agent_identifier(flow_key) if is_enabled else None
        
        flow_list.append({
            "key": flow_key,
            "name": flow_info["name"],
            "description": flow_info["description"],
            "version": flow_info["version"],
            "author": flow_info["author"],
            "tags": flow_info["tags"],
            "enabled": is_enabled,
            "agent_identifier": agent_identifier
        })
    
    return {
        "flows": flow_list,
        "total_flows": len(flow_list),
        "enabled_flows": len([f for f in flow_list if f["enabled"]]),
        "network": settings.network,
        "test_mode": settings.masumi_test_mode,
        "kodosumi_url": settings.kodosumi_base_url,
        "polling_interval_seconds": settings.polling_interval_seconds
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/admin/running-jobs")
async def get_running_jobs(db: AsyncSession = Depends(get_db), _: bool = Depends(get_api_key)):
    """Get currently running jobs with timeout information."""
    repository = FlowRunRepository(db)
    active_runs = await repository.get_active_runs()
    
    from datetime import datetime
    
    running_jobs = []
    for run in active_runs:
        # Calculate time remaining until timeout
        time_remaining = None
        timeout_status = "none"
        
        if run.timeout_at:
            current_time = datetime.utcnow()
            if current_time < run.timeout_at:
                remaining_seconds = (run.timeout_at - current_time).total_seconds()
                time_remaining = int(remaining_seconds)
                
                # Status based on remaining time
                if remaining_seconds < 300:  # Less than 5 minutes
                    timeout_status = "critical"
                elif remaining_seconds < 1800:  # Less than 30 minutes
                    timeout_status = "warning"
                else:
                    timeout_status = "normal"
            else:
                timeout_status = "expired"
        
        running_jobs.append({
            "id": run.id,
            "flow_name": run.flow_name,
            "flow_path": run.flow_path,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "timeout_at": run.timeout_at.isoformat() if run.timeout_at else None,
            "time_remaining_seconds": time_remaining,
            "timeout_status": timeout_status,
            "kodosumi_run_id": run.kodosumi_run_id,
            "masumi_payment_id": run.masumi_payment_id
        })
    
    return {
        "running_jobs": running_jobs,
        "total_running": len(running_jobs)
    }

@app.get("/admin")
async def admin_panel(_: bool = Depends(get_api_key)):
    """Serve the admin panel."""
    admin_file = os.path.join(os.path.dirname(__file__), "..", "static", "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    else:
        raise HTTPException(status_code=404, detail="Admin panel not found")

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

@app.post("/admin/agents/toggle")
async def toggle_agent(
    request: dict,
    _: bool = Depends(get_api_key)
):
    """Toggle agent enable/disable status in database."""
    # Import here to avoid circular imports
    from masumi_kodosuni_connector.services.agent_config_manager import agent_config_manager
    
    flow_key = request.get("flow_key")
    enable = request.get("enable", False)
    agent_identifier = request.get("agent_identifier")
    
    if not flow_key:
        raise HTTPException(status_code=400, detail="Missing flow_key")
    
    if enable and not agent_identifier:
        raise HTTPException(status_code=400, detail="Agent identifier is required when enabling an agent")
    
    try:
        # Get flow info for names/descriptions
        flows = await flow_discovery.get_available_flows()
        flow_info = flows.get(flow_key, {})
        
        if enable:
            # Enable agent with the provided identifier
            success = await agent_config_manager.enable_agent(
                flow_key=flow_key,
                agent_identifier=agent_identifier,
                flow_name=flow_info.get("name"),
                description=flow_info.get("description")
            )
            if success:
                return {
                    "status": "enabled",
                    "message": f"Agent {flow_key} enabled successfully.",
                    "agent_identifier": agent_identifier
                }
        else:
            # Disable agent
            success = await agent_config_manager.disable_agent(flow_key)
            if success:
                return {
                    "status": "disabled", 
                    "message": f"Agent {flow_key} disabled successfully."
                }
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update agent configuration")
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating agent configuration: {str(e)}"
        )

@app.post("/admin/reload-routes")
async def reload_routes(_: bool = Depends(get_api_key)):
    """Reload flow routes to include newly enabled agents in API docs."""
    try:
        global _flow_routers_added
        _flow_routers_added = False  # Reset the flag
        await add_flow_routes(force_reload=True)
        return {
            "status": "success",
            "message": "Flow routes reloaded successfully. New agents should now appear in API docs."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading routes: {str(e)}"
        )