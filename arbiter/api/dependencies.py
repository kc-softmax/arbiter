from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.database import make_async_session


class UnitOfWork():
    async def __call__(self, session: AsyncSession = Depends(make_async_session)):
        async with session as async_session:
            try:
                yield session
                await async_session.commit()
            except Exception as e:
                await async_session.rollback()
                raise e
            
unit_of_work = UnitOfWork()