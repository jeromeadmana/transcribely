from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import ssl

from app.core.config import settings


# SSL context for PostgreSQL
ssl_context = ssl.create_default_context()
if settings.environment == "development":
    # Disable SSL verification only in development
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_context},
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for background tasks
sync_engine = create_engine(
    settings.sync_database_url,
    echo=False,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
