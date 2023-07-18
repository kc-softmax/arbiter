

from enum import Enum
from math import ceil
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

T = TypeVar('T')


class SortType(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class PaginationRequest(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1)
    field: str = Field('id')
    sort: SortType = SortType.DESC


class PaginationResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


async def create_pagination(
    session: AsyncSession,
    # hint?
    model: Any,
    params: PaginationRequest,
) -> PaginationResponse[T]:
    skip = params.size * (params.page - 1) if params.page is not None and params.size is not None else None
    sort_direction = getattr(model, params.field).desc() if params.sort == 'desc' else getattr(model, params.field)
    statement = select(model).offset(skip).limit(params.size).order_by(sort_direction)
    results = await session.exec(statement)
    items = results.all()

    total = await session.scalar(select(func.count(model.id)))

    size = params.size if params.size is not None else total
    page = params.page if params.page is not None else 1
    pages = ceil(total / params.size) if total is not None else None
    return PaginationResponse[T](
        total=total,
        items=items,
        page=page,
        size=size,
        pages=pages,
    )
