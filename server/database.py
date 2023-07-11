from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker


sqlite_file_name = "arbiter_test.db"
sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"

# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
connect_args = {"check_same_thread": False}


async_engine = create_async_engine(
    sqlite_url,
    echo=True,
    future=True,
    connect_args=connect_args
)


async def create_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def make_async_session():
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()


async def get_async_session() -> AsyncSession:
    async with make_async_session() as session:
        yield session
