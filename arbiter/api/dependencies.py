from contextlib import asynccontextmanager
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.database import make_async_session


class UnitOfWork:
    # for fastapi depedns
    async def __call__(self, session: AsyncSession = Depends(make_async_session)):
        async with self.transaction(session) as session:
            yield session
            
    @asynccontextmanager
    async def transaction(self, session: AsyncSession = make_async_session()):
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        

unit_of_work = UnitOfWork()