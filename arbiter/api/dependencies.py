import asyncio
from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from arbiter.api.auth.models import User

from arbiter.api.database import make_async_session, unit_of_work


async def get_uow(session: AsyncSession = Depends(make_async_session)):
    async with session:
        async with unit_of_work.transaction(session) as uow:
            yield uow
