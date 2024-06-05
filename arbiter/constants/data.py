from __future__ import annotations
import json
from typing import Optional
from dataclasses import dataclass, asdict
from arbiter.constants.enums import ArbiterMessageType


@dataclass
class ArbiterMessage:
    from_service_id: str
    message_type: ArbiterMessageType
    data: Optional[bytes] = None

    def encode(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def decode(cls, data: str) -> ArbiterMessage:
        return cls(**json.loads(data))
