import asyncio
import uvicorn
import structlog
from contextlib import asynccontextmanager
from masumi_kodosuni_connector.api.main import app
from masumi_kodosuni_connector.services.polling_service import PollingService
from masumi_kodosuni_connector.config.settings import settings
from masumi_kodosuni_connector.config.logging import configure_logging

configure_logging()

logger = structlog.get_logger()
polling_service = PollingService()


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting Masumi Kodosuni Connector")
    
    # Initialize database
    try:
        from masumi_kodosuni_connector.database.connection import init_db
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
    
    # Resume payment monitoring for pending jobs after restart
    try:
        from masumi_kodosuni_connector.database.connection import AsyncSessionLocal
        from masumi_kodosuni_connector.services.agent_service import FlowService
        
        async with AsyncSessionLocal() as session:
            flow_service = FlowService(session)
            await flow_service.resume_payment_monitoring()
        
        logger.info("Payment monitoring recovery completed successfully")
    except Exception as e:
        logger.error("Failed to resume payment monitoring", error=str(e))
        # Don't fail startup if payment recovery fails - service can still function
    
    polling_task = asyncio.create_task(polling_service.start())
    
    try:
        yield
    finally:
        logger.info("Shutting down Masumi Kodosuni Connector") 
        polling_service.stop()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

app.router.lifespan_context = lifespan


def main():
    uvicorn.run(
        "masumi_kodosuni_connector.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()