import sys
from typing import Generic, Type, TypeVar
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import and_, column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from server.config import settings
from server.auth.models import ConsoleUser, Role


# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
connect_args = {"check_same_thread": False}

db_url = settings.RDB_CONNECTION_URL
if "pytest" in sys.modules:
    db_url = settings.TEST_RDB_CONNECTION_URL

async_engine = create_async_engine(
    db_url,
    echo=False,
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

# 우선 database에 class에 정의
T = TypeVar("T", bound=SQLModel)


class DatabaseManager(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def create(self, session: AsyncSession, obj: T) -> T:
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def get_one(self, session: AsyncSession, obj_clauses: T) -> T:
        where_clauses = self._build_where_clauses(obj_clauses)
        state = select(self.model).where(and_(*where_clauses))
        result = await session.exec(state)
        return result.first()

    async def get_all(self, session: AsyncSession, obj_clauses: T) -> list[T]:
        where_clauses = self._build_where_clauses(obj_clauses)
        state = select(self.model).where(and_(*where_clauses))
        result = await session.exec(state)
        return result.all()

    async def update(self, session: AsyncSession, obj_in: T, obj: T) -> T:
        update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            setattr(obj, field, update_data[field])
        return await self.create(session, obj)

    # delete 정리 필요
    # get_one 호출 후 사용
    async def delete_one(self, session: AsyncSession, obj: T) -> bool:
        try:
            await session.delete(obj)
            await session.commit()
        except Exception as e:
            return False
        return True

    # get_all 호출 후 사용
    async def delete_all(self, session: AsyncSession, obj_ids: list[T]) -> bool:
        try:
            for obj_id in obj_ids:
                db_obj = await session.get(self.model, obj_id)
                if not db_obj:
                    raise Exception(f"User id {obj_id} is not found")
                await session.delete(db_obj)
        except Exception as e:
            print(e)
            await session.rollback()
            return False
        await session.commit()
        return True

    # where 절 생성하는 함수
    def _build_where_clauses(self, obj_clauses: Type[T]):
        where_clauses = obj_clauses.dict(exclude_unset=True)
        return [column(key) == value for key, value in where_clauses.items()]
