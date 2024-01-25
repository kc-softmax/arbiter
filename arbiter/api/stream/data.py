from __future__ import annotations
import json
import pickle
from dataclasses import dataclass
from arbiter.api.stream.const import StreamSystemEvent


@dataclass
class StreamMessage:
    user_id: int
    data: bytes
    event_type: StreamSystemEvent = None

    def encode_pickle(self):
        # how to encode? this dataclass to bytes
        return pickle.dumps(self)
        # return json.dumps(dataclasses.asdict(self)).encode('utf-8')

    @classmethod
    def decode_pickle(cls, data: bytes) -> StreamMessage:
        return pickle.loads(data)

    @classmethod
    def decode(cls, data: str) -> StreamMessage:
        return cls(**json.loads(data))
