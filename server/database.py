import sys
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from server.config import settings
from server.auth.models import ConsoleUser, Role


# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
connect_args = {"check_same_thread": False}

db_url = settings.RDB_CONNECTION_URL
if "pytest" in sys.modules:
    db_url = settings.TEST_RDB_CONNECTION_URL

async_engine = create_async_engine(
    db_url,
    echo=True,
    future=True,
    connect_args=connect_args
)


# TODO: 마이그레이션 로직 추가되면 제거
async def create_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
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
        result = await session.exec(
            # 오너 유저가 한명도 없으면, 오너 유저를 생성한다.
            select(ConsoleUser).where(ConsoleUser.role == Role.OWNER).limit(1)
        )

        if result.first() is None:
            if not settings.INITIAL_CONSOLE_USER_EMAIL:
                print('initial_console_user_email is blank')
                return
            if not settings.INITIAL_CONSOLE_USER_PASSWORD:
                print('initial_console_user_password is blank')
                return

            session.add(
                ConsoleUser(
                    email=settings.INITIAL_CONSOLE_USER_EMAIL,
                    password=settings.INITIAL_CONSOLE_USER_PASSWORD,
                    role=Role.OWNER
                )
            )
            await session.commit()
