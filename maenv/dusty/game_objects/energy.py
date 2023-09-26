from maenv.dusty.game_objects import GameObject
from maenv.dusty.colors import (
    RED,
)


class Energy(GameObject):

    def __init__(
        self,
        center_x: int,
        center_y: int,
        size: int,
    ) -> None:
        super(Energy, self).__init__(
            center_x, center_y, size, size)
        self.acquirers: list[str] = []

    def get_color(self):
        return RED
