import asyncio
import pytest
import pytest_asyncio
from typing import Generator
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.database import async_engine


# event_loop fixture를 테스트 케이스마다 주입해줘야 한다. -> @pytest.mark.asyncio가 처리 해줌
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# 각 테스트마다 clena-up 및 멱등성 확보를 위해, 가장 쉬운 방법인 create & drop으로 처리
@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncSession:
    test_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_session() as session:
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await async_engine.dispose()