import sys
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

from arbiter.api.config import settings

# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
connect_args = {"check_same_thread": False}

db_url = settings.RDB_CONNECTION_URL
if "pytest" in sys.modules:
    db_url = settings.TEST_RDB_CONNECTION_URL

async_engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    connect_args=connect_args,
)


# SQLite는 기본적으로 외래키 제약 조건이 비활성화되어 있기 때문에 활성화를 해준다.
@event.listens_for(async_engine.sync_engine, "connect")
def engine_connect(connection, record):
    connection.execute('pragma foreign_keys=ON')


# TODO: 마이그레이션 로직 추가되면 제거
async def create_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


def make_async_session():
    async_session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    return async_session()
