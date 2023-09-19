from __future__ import annotations
from typing import Generic, Type, TypeVar
from sqlmodel import select, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

T = TypeVar('T')


class BaseCRUDRepository(Generic[T]):
    def __init__(self, model_cls: Type[T]) -> None:
        self._model_cls = model_cls
        self.session: AsyncSession = None

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

    async def get_list_by(self, **filters) -> list[T]:
        stmt = self._construct_where_stmt(**filters)
        return (await self.session.exec(stmt)).all()

    async def get_one_by(self, **filters) -> T | None:
        stmt = self._construct_where_stmt(**filters)
        return (await self.session.exec(stmt)).first()

    async def add(self, record: T) -> T:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: T) -> T:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, id: int) -> None:
        record = await self.get_by_id(id)
        await self.session.delete(record)
        await self.session.flush()

    async def get_by_id(self, id: int) -> T | None:
        return await self.get_one_by(id=id)
