from dataclasses import dataclass
from arbiter.api.auth.models import GameUser
from arbiter.api.stream.const import StreamSystemEvent


@dataclass
class StreamMessage:
    data: bytes
    game_user: GameUser
    event_type: StreamSystemEvent = None
