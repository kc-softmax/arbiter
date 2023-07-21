import asyncio
from typing import Generator

import pytest
import pytest_asyncio
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server.database import async_engine


@pytest.fixture(scope="session")
def event_loop(request) -> Generator:  # noqa: indirect usage
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# request 테스트를 위한 fixture


# @pytest_asyncio.fixture
# async def async_client():
#     async with AsyncClient(
#             app=app,
#             base_url=f"http://{settings.api_v1_prefix}"
#     ) as client:
#         yield client


@pytest_asyncio.fixture(scope="class")
async def async_session() -> AsyncSession:
    session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session() as s:
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        yield s

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        pass

    await async_engine.dispose()
