from dataclasses import dataclass
from typing import Any, ClassVar, Generic, Optional, Sequence

from fastapi.params import Query
from fastapi_pagination.bases import AbstractPage, AbstractParams, CursorRawParams
from fastapi_pagination.types import Cursor, ParamsType
from fastapi_pagination.cursor import decode_cursor, encode_cursor, T, CursorPage
from pydantic import BaseModel, Field


@dataclass
class CustomCursorRawParams(CursorRawParams):
    current_page: int
    target_page: int


class CustomCursorParams(BaseModel, AbstractParams):
    cursor: Optional[str] = Query(None, description="Cursor for the next page")
    size: int = Query(20, ge=0, description="Page offset")
    current_page: int = Query(0, ge=0, description="Current page")
    target_page: int = Query(1, ge=0, description="Target page")

    str_cursor: ClassVar[bool] = True

    def to_raw_params(self) -> CustomCursorRawParams:
        return CustomCursorRawParams(
            cursor=decode_cursor(self.cursor, to_str=self.str_cursor),
            size=self.size,
            current_page=self.current_page,
            target_page=self.target_page,
        )


class CustomCursorPage(AbstractPage[T], Generic[T]):
    items: Sequence[T]
    previous_page: Optional[str] = Field(None, description="Cursor for the previous page")
    next_page: Optional[str] = Field(None, description="Cursor for the next page")
    total: Optional[int] = Field(None, description="Total number of items")

    __params_type__ = CustomCursorParams

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        params: AbstractParams,
        *,
        next_: Optional[Cursor] = None,
        previous: Optional[Cursor] = None,
        **kwargs: Any,
    ) -> CursorPage[T]:
        return cls(
            total=0,
            items=items,
            next_page=encode_cursor(next_),
            previous_page=encode_cursor(previous),
            **kwargs,
        )
