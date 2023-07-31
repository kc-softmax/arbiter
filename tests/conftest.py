import asyncio
import pytest
import pytest_asyncio
from typing import Generator
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server.database import async_engine


# event_loop fixture를 테스트 케이스마다 주입해줘야 한다. -> @pytest.mark.asyncio가 처리 해줌
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# 테스트 class마다 session을 생성하고, 테스트가 끝나면 session을 종료한다.
@pytest_asyncio.fixture(scope="class")
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
        pass

    await async_engine.dispose()
