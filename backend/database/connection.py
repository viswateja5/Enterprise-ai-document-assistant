import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, String, ForeignKey, DateTime, Text, Integer
from dotenv import load_dotenv

# Load env configurations
load_dotenv()

# postgresql+asyncpg://user:pass@host/db or sqlite+aiosqlite:///vector_store/chat_history.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///vector_store/chat_history.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

is_sqlite = "sqlite" in DATABASE_URL

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL,
    # SQLite-specific pool configuration (safe for single process sqlite engine)
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True
)

# Create Async Session Maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for SQLAlchemy declarative models
class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """
    Initializes database tables. Creates directory paths for SQLite databases if required.
    """
    if is_sqlite:
        db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if is_sqlite:
            # Check and alter table to add columns for backward compatibility
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN session_id VARCHAR(50) REFERENCES chat_sessions(id) ON DELETE CASCADE"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN document_id VARCHAR(100)"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN file_hash VARCHAR(64)"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN status VARCHAR(50) DEFAULT 'Ready'"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN summary TEXT"))
            except Exception:
                pass
