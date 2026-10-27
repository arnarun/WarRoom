from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL, DATABASE_SSL

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    # Pin sessions to UTC so NOW() defaults on TIMESTAMP columns are UTC
    # regardless of the server's local timezone.
    connect_args={"ssl": DATABASE_SSL, "server_settings": {"timezone": "UTC"}},
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
