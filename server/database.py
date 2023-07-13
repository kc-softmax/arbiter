from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from server.auth.models import ConsoleUser, Role


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


# TODO: 마이그레이션 로직 추가되면 제거
async def create_db_and_tables():
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        await set_default_console_user()


def make_async_session():
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()


async def get_async_session() -> AsyncSession:
    async with make_async_session() as session:
        yield session


# TODO: 마이그레이션 로직 추가되면 마이그레이션 로직으로 이동
async def set_default_console_user():
    async with make_async_session() as session:
        email = "initial@default.com"
        state = select(ConsoleUser).where(ConsoleUser.email == email)
        result = await session.exec(state)
        if result.first() is None:
            session.add(
                ConsoleUser(
                    email=email,
                    password="password",
                    role=Role.OWNER
                )
            )
            await session.commit()
