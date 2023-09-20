from __future__ import annotations
import sys
from typing import AsyncIterator
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from arbiter.api.config import settings
from arbiter.api.auth.repository import GamerUserRepository

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


def make_async_session():
    async_session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
    )
    return async_session()


class UnitOfWork():
    def __init__(self) -> None:
        self.gamer_users = GamerUserRepository()

    @asynccontextmanager
    async def transaction(self, session: AsyncSession) -> AsyncIterator[UnitOfWork]:
        try:
            self.set_session_in_repository(session)
            yield self
            await session.commit()
        except Exception as e:
            print(f'database transaction error: {e}')
            await session.rollback()
            raise e
        finally:
            self.set_session_in_repository(None)

    def set_session_in_repository(self, session: AsyncSession | None):
        self.gamer_users.session = session


unit_of_work = UnitOfWork()
