import copy
from sqlalchemy import Column
from sqlalchemy_json import mutable_json_type
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, select
from sqlmodel.main import SQLModelMetaclass
from sqlmodel.ext.asyncio.session import AsyncSession

from datetime import datetime
from typing import Any, Type, TypeVar


class SchemaMeta(SQLModelMetaclass):
    def __new__(cls, name, bases, namespaces, **kwargs):
        fields, is_pick = cls.get_fields(cls, namespaces)
        if fields:
            cls.set_new_fields(cls, bases, namespaces, fields, is_pick)
        return super().__new__(cls, name, bases, namespaces, **kwargs)

    def get_fields(cls, namespaces: dict[str, Any]):
        omit_fields = getattr(namespaces.get("Config", {}), "omit_fields", {})
        pick_fields = getattr(namespaces.get("Config", {}), "pick_fields", {})

        if not omit_fields and not pick_fields:
            return None, None
        if omit_fields and pick_fields:
            raise Exception("You should set only one fields(omit_fields or pick_fields)")
        return pick_fields if pick_fields else omit_fields, True if pick_fields else False

    def set_new_fields(cls, bases, namespaces: dict[str, Any], user_fields: Any | dict[Any, Any], is_pick: bool):
        fields = namespaces.get('__fields__', {})
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            fields.update(base.__fields__)
            annotations.update(base.__annotations__)
        merged_keys = fields.keys() & annotations.keys()
        [merged_keys.add(field) for field in fields]

        new_fields = {}
        new_annotations = {}
        for field in merged_keys:
            is_included = field in user_fields
            if not field.startswith('__') and is_included if is_pick else not is_included:
                new_annotations[field] = annotations.get(field, fields[field].type_)
                new_fields[field] = fields[field]
        namespaces['__annotations__'] = new_annotations
        namespaces['__fields__'] = new_fields


class BaseSQLModel(SQLModel, metaclass=SchemaMeta):
    pass


class PKModel(BaseSQLModel):
    id: int | None = Field(default=None, primary_key=True)


class TimestampModel(BaseSQLModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    deprecated_at: datetime | None = Field(
        nullable=True
    )


DT = TypeVar('DT', bound='BaseDocument')


class BaseDocument(PKModel, TimestampModel):
    data: dict = Field(sa_column=Column(mutable_json_type(dbtype=JSONB, nested=True)))

    @classmethod
    async def query_and(cls: Type[DT], session: AsyncSession, filters: dict[str, Any]) -> list[DT]:
        query = select(cls)
        for key, value in filters.items():
            if isinstance(value, str):
                query = query.where(cls.data[key].astext == value)
            elif isinstance(value, int):
                query = query.where(cls.data[key].as_integer() == value)
            elif isinstance(value, bool):
                query = query.where(cls.data[key].as_boolean() == value)
            else:
                query = query.where(cls.data[key] == value)
        result = (await session.exec(query)).all()
        # test
        for document in result:
            print("Queried!!!", document)
        return result

    @classmethod
    async def get_by_id(cls: Type[DT], session: AsyncSession, id: int) -> DT | None:
        return (await session.exec(select(cls).where(cls.id == id))).first()

    @classmethod
    async def add(cls: Type[DT], session: AsyncSession, data: DT) -> DT:
        session.add(data)
        await session.flush()
        await session.refresh(data)
        return data

    @classmethod
    async def update(cls: Type[DT], session: AsyncSession, id: int, **values) -> DT:
        document = await cls.get_by_id(session, id)
        assert document is not None

        document.data = copy.deepcopy(document.data)
        document.updated_at = datetime.utcnow()
        for key, value in values.items():
            document.data[key] = value

        session.add(document)
        await session.flush()
        await session.refresh(document)
        return document

    @classmethod
    async def delete(cls: Type[DT], session: AsyncSession, id: int) -> None:
        document = await cls.get_by_id(id)
        await session.delete(document)
        await session.flush()
