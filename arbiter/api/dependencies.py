from contextlib import asynccontextmanager
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.database import make_async_session


class UnitOfWork:
    # for fastapi depedns
    async def __call__(self, session: AsyncSession = Depends(make_async_session)):
        try:
            yield session
            await session.commit()
        except Exception as e:
            print("########## __CALL__ ERROR ############", e)
            await session.rollback()
            raise e
        
            
    @asynccontextmanager
    async def transaction(self):
        async with make_async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                print("########## TRANSACTION ERROR ############", e)
                await session.rollback()
                raise e

unit_of_work = UnitOfWork()