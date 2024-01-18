from dataclasses import dataclass
from arbiter.api.auth.models import GameUser
from arbiter.api.stream.const import ArbiterSystemEvent


@dataclass
class StreamMessage:
    data: bytes
    game_user: GameUser
    event_type: ArbiterSystemEvent = None
