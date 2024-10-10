from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Tuple

class ArbiterTaskModel(ABC):
    
    def __init__(
        self,
    ) -> None:
        super().__init__()

    @abstractmethod
    async def test(self):
        raise NotImplementedError
    