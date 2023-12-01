from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from arbiter.api.config import settings
from arbiter.api.models import BaseSQLModel

db_url = settings.RDB_CONNECTION_URL

async_engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
)

def make_async_session():
    async_session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    return async_session()

async def init_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(BaseSQLModel.metadata.create_all, checkfirst=False)

# def version_schema(script_location: str):
#     """Applies alembic versioning to schema."""
#     alembic_cfg = AlembicConfig()
#     alembic_cfg.set
#     alembic_cfg.set_main_option("script_location", script_location)
#     alembic_command.stamp(alembic_cfg, "head")
