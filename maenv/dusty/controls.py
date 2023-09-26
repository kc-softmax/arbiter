from __future__ import annotations
from enum import Enum
import pygame


class EightDirection(Enum):
    """Enum for the 8 directions of the D-pad."""
    UP = (1, pygame.math.Vector2(0, -1).normalize())
    UP_RIGHT = (2, pygame.math.Vector2(1, -1).normalize())
    RIGHT = (3, pygame.math.Vector2(1, 0).normalize())
    DOWN_RIGHT = (4, pygame.math.Vector2(1, 1).normalize())
    DOWN = (5, pygame.math.Vector2(0, 1).normalize())
    DOWN_LEFT = (6, pygame.math.Vector2(-1, 1).normalize())
    LEFT = (7, pygame.math.Vector2(-1, 0).normalize())
    UP_LEFT = (8, pygame.math.Vector2(-1, -1).normalize())

    def next(self, direction: EightDirection) -> EightDirection:
        if self.value[0] == direction.value[0]:
            return self
        clockwise = direction.value[0] - self.value[0] > 0
        value = self.value[0] - 1
        value = (value + 1) % 8 if clockwise else (value - 1) % 8
        return list(self.__class__)[value]

    @classmethod
    def get_direction_by_value(cls, value: int) -> EightDirection:
        """Get the next direction in the D-pad."""
        for direction in EightDirection:
            if direction.value[0] == value:
                return direction
        return None
