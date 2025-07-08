from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from masumi_kodosuni_connector.config.settings import settings
from masumi_kodosuni_connector.models.agent_run import Base as ModelsBase

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    # Connection pool configuration for better concurrency
    pool_size=50,           # Number of connections to maintain in the pool
    max_overflow=100,       # Additional connections beyond pool_size
    pool_pre_ping=True,     # Validate connections before use
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_timeout=30,        # Timeout for getting connection from pool
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def init_db():
    """Initialize database tables if they don't exist."""
    # Import all models to ensure they're registered with SQLAlchemy
    from masumi_kodosuni_connector.models import agent_config  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(ModelsBase.metadata.create_all)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()