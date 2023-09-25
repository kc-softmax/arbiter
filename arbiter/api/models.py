from sqlmodel import Field, SQLModel
from sqlmodel.main import SQLModelMetaclass
from datetime import datetime
from typing import Any


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
