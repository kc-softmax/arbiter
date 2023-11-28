from datetime import datetime
from typing import Generic, Type, TypeVar
from sqlmodel import select, and_, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from arbiter.api.models import BaseSQLModel

T = TypeVar('T', bound=BaseSQLModel)


class BaseCRUDRepository(Generic[T]):
    def __init__(self, model_cls: Type[T]) -> None:
        self._model_cls = model_cls

    def _construct_where_stmt(self, **filters) -> SelectOfScalar:
        stmt = select(self._model_cls)
        where_clauses = []
        for c, v in filters.items():
            if not hasattr(self._model_cls, c):
                raise ValueError(f"Invalid column name {c}")
            where_clauses.append(getattr(self._model_cls, c) == v)

        if len(where_clauses) == 1:
            stmt = stmt.where(where_clauses[0])
        elif len(where_clauses) > 1:
            stmt = stmt.where(and_(*where_clauses))
        return stmt

    async def get_list_by(self, session: AsyncSession, **filters) -> list[T]:
        stmt = self._construct_where_stmt(**filters)
        return (await session.exec(stmt)).all()

    async def get_one_by(self, session: AsyncSession, **filters) -> T | None:
        stmt = self._construct_where_stmt(**filters)
        return (await session.exec(stmt)).first()

    async def add(self, session:AsyncSession, record: T) -> T:
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def update(self, session: AsyncSession, record: T) -> T:
        record.updated_at = datetime.utcnow()
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def delete(self, session: AsyncSession, id: int) -> None:
        record = await self.get_by_id(id)
        await session.delete(record)
        await session.flush()

    async def get_by_id(self, session: AsyncSession, id: int) -> T | None:
        return await self.get_one_by(session, id=id)
