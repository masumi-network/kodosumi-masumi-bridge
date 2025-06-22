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