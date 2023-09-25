from contextlib import asynccontextmanager
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.database import make_async_session
from arbiter.api.repository import BaseCRUDRepository


class UnitOfWork():

    def __init__(self, repo_list: list[BaseCRUDRepository]) -> None:
        self.repo_list = repo_list

    async def __call__(self, session=Depends(make_async_session)):
        async with session:
            async with self.transaction(session):
                yield

    @asynccontextmanager
    async def transaction(self, session: AsyncSession):
        try:
            self.set_session_in_repository(session)
            yield
            await session.commit()
        except Exception as e:
            print(f'database transaction error: {e}')
            await session.rollback()
            raise e
        finally:
            self.set_session_in_repository(None)

    def set_session_in_repository(self, session: AsyncSession | None):
        for repository in self.repo_list:
            repository.session = session
