from __future__ import annotations
import json
import pickle
from typing import Optional, Type
from dataclasses import dataclass, field
from arbiter.constants.enums import ArbiterMessageType


@dataclass
class ArbiterSystemRequestMessage:
    from_id: str
    type: ArbiterMessageType

    def encode(self) -> bytes:
        # Convert the dataclass to a dictionary
        data_dict = {}
        # change readable using properties
        self.from_id and data_dict.update({"from_id": self.from_id})
        self.type and data_dict.update({"type": self.type})
        return pickle.dumps(data_dict)

    @classmethod
    def decode(cls, data: bytes) -> ArbiterSystemRequestMessage:
        return cls(*pickle.loads(data).values())




@dataclass
class ArbiterSystemMessage:
    type: ArbiterMessageType
    data: bytes = field(default=b'')

    def encode(self) -> bytes:
        # Convert the dataclass to a dictionary
        data_dict = {}
        # change readable using properties
        self.type and data_dict.update({"type": self.type})
        self.data and data_dict.update({"data": self.data})
        return pickle.dumps(data_dict)

    @classmethod
    def decode(cls, data: bytes) -> ArbiterSystemMessage:
        return cls(*pickle.loads(data).values())


@dataclass(init=False)
class ArbiterMessage:
    # Variable name changes for encoding efficiency
    # id: str
    i: str
    # data: bytes
    d: Optional[bytes] = None

    def __init__(
        self,
        data: bytes,
        id: str | None = None,
    ):
        self.d = data
        self.i = id

    @property
    def id(self) -> str:
        return self.i

    @property
    def data(self) -> bytes | None:
        return self.d

    def encode(self) -> bytes:
        # Convert the dataclass to a dictionary
        data_dict = {}
        # change readable using properties
        self.d and data_dict.update({"d": self.d})
        self.i and data_dict.update({"i": self.i})
        # Serialize the filtered dictionary using pickle
        return pickle.dumps(data_dict)

    @classmethod
    def decode(cls, data: bytes) -> ArbiterMessage:
        return cls(*pickle.loads(data).values())

    def encode_to_json(self) -> str:
        # Convert the dataclass to a dictionary
        data_dict = {}
        # change readable using properties
        self.i and data_dict.update({"id": self.i})
        if self.d:
            if isinstance(self.d, bytes):
                data_dict.update({"data": self.d.decode()})
            else:
                data_dict.update({"data": self.d})

        return json.dumps(data_dict)

    @classmethod
    def decode_from_json(cls, data: str) -> ArbiterMessage:
        # Convert the JSON string to a dictionary
        data_dict = json.loads(data)
        # change readable using properties
        if value := data_dict.pop('i', None):
            data_dict.update({"id": value})
        if value := data_dict.pop('d', None):
            data_dict.update({"data": value})

        return cls(**data_dict)
