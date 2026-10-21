from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


# DATABASE_URL = 'sqlite+aiosqlite:///./supplier.db'

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# SQLite 开启外键约束

if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine.sync_engine, 'connect')
    def _sqlite_fk_on(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖:每个请求都获得一个独立的session,请求结束自动关闭"""
    async with async_session_factory() as session:
        yield session
