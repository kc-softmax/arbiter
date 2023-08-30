from enum import Enum
from math import ceil
from typing import Generic, TypeVar
from pydantic import BaseModel, Field, parse_obj_as
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

# from server.utils import BaseRequestSchema

T = TypeVar('T')
K = TypeVar('K')


class SortType(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class PaginationRequest(BaseModel):
    # 최대(le) 최소(ge) 설정
    page: int = Field(1, ge=1)
    size: int = Field(15, ge=1, le=100)
    field: str = Field('id')
    sort: SortType = Field(SortType.DESC)


class PaginationResponse(BaseModel, Generic[K]):
    items: list[K]
    total: int
    page: int
    size: int
    pages: int


async def create_pagination(
    session: AsyncSession,
    model: type[T],
    schema: type[K],
    params: PaginationRequest,
) -> PaginationResponse[K]:
    skip = params.size * (params.page - 1)
    order_by_field = getattr(model, params.field)
    if params.sort == SortType.DESC:
        order_by_field = order_by_field.desc()

    statement = select(model).offset(skip).limit(params.size).order_by(order_by_field)
    results = await session.exec(statement)
    total = await session.scalar(select(func.count(model.id)))

    return PaginationResponse[schema](
        total=total,
        # model to schema
        items=parse_obj_as(list[schema], results.all()),
        page=params.page,
        size=params.size,
        pages=ceil(total/params.size),
    )
