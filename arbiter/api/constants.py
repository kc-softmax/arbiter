from __future__ import annotations
from uvicorn.workers import UvicornWorker

ArbiterUvicornWorker = UvicornWorker
ArbiterUvicornWorker.CONFIG_KWARGS = {"loop": "asyncio", "http": "auto"}

class SubscribeChannel:
    
    def __init__(self, channel: str, target: int | str = None):
        self.channel = channel
        self.target = target
        
    def get_channel(self):
        if self.target:
            return f"{self.channel}_{self.target}"
        return self.channel
    
    def __eq__(self, value: SubscribeChannel) -> bool:
        return self.get_channel() == value.get_channel()

    def __hash__(self):
        return self.get_channel().__hash__()