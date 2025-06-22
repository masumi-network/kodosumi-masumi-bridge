from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from masumi_kodosuni_connector.config.settings import settings
from masumi_kodosuni_connector.api.agent_routes import create_agent_router
from masumi_kodosuni_connector.database.connection import get_db
from masumi_kodosuni_connector.services.agent_service import AgentService
from masumi_kodosuni_connector.api.exceptions import (
    AgentServiceException,
    agent_service_exception_handler,
    general_exception_handler
)

app = FastAPI(
    title="Masumi Kodosumi Connector",
    description="Wrapper API for Kodosumi AI Agent jobs with Masumi payment integration",
    version="0.1.0"
)

app.add_exception_handler(AgentServiceException, agent_service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

for agent_key in settings.agents_config.keys():
    agent_router = create_agent_router(agent_key)
    app.include_router(agent_router)

@app.get("/")
async def root():
    return {
        "service": "Masumi Kodosumi Connector",
        "version": "0.1.0",
        "agents": list(settings.agents_config.keys())
    }

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
    
    service = AgentService(db)
    success = await service.process_payment_confirmation(payment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found or already processed")
    
    return {"status": "payment_processed"}