from sqlmodel.main import SQLModelMetaclass
from typing import Any


class SchemaMeta(SQLModelMetaclass):
    def __new__(cls, name, bases, namespaces, **kwargs):
        fields = cls.get_fields(cls, namespaces)

        # 따로 추가한 omit 또는 pick 필드가 없으면 원래의 SQLModel의 메타 클래스로 생성
        if fields == None:
            return super().__new__(cls, name, bases, namespaces, **kwargs)
        # 따로 추가한 필드로 셋팅
        cls.set_new_fields(cls, bases, namespaces, fields)
        return super().__new__(cls, name, bases, namespaces, **kwargs)

    def get_fields(cls, namespaces: dict[str, Any]):
        omit_fields = getattr(namespaces.get("Config", {}), "omit_fields", {})
        pick_fields = getattr(namespaces.get("Config", {}), "pick_fields", {})

        if not omit_fields and not pick_fields:
            return None
        if omit_fields and pick_fields:
            raise Exception("You should set only one fields(omit_fields or pick_fields)")

        cls.new_field_type = "omit" if omit_fields else "pick"

        return omit_fields if omit_fields else pick_fields

    def set_new_fields(cls, bases, namespaces: dict[str, Any], user_fields: Any | dict[Any, Any]):
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
            new_fields_condition = (field not in user_fields) if cls.new_field_type == "omit" else (
                field in user_fields
            )
            if not field.startswith('__') and new_fields_condition:
                new_annotations[field] = annotations.get(field, fields[field].type_)
                new_fields[field] = fields[field]
        namespaces['__annotations__'] = new_annotations
        namespaces['__fields__'] = new_fields
