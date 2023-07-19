

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
    # 최대(le) 최소(ge) 설정
    page: int = Field(1, ge=1)
    size: int = Field(15, ge=1, le=100)
    field: str = Field('id')
    sort: SortType = Field(SortType.DESC)


class PaginationResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


async def create_pagination(
    session: AsyncSession,
    model: type[Any],  # class type
    params: PaginationRequest,
) -> PaginationResponse[T]:
    skip = params.size * (params.page - 1)
    field_desc_or_asc = getattr(model, params.field)
    if params.sort == SortType.DESC:
        field_desc_or_asc = field_desc_or_asc.desc()

    statement = select(model).offset(skip).limit(params.size).order_by(field_desc_or_asc)
    results = await session.exec(statement)
    total = await session.scalar(select(func.count(model.id)))

    return PaginationResponse[T](
        total=total,
        items=results.all(),
        page=params.page,
        size=params.size,
        pages=ceil(total/params.size),
    )
