

import pygame
from typing import Tuple
from maenv.dusty.colors import WHITE
from maenv.dusty.enums import CollideType

generated_id = 1


class GameObject(pygame.Rect):

    id = 0
    id_map: dict[int] = {}

    def __init__(
        self,
        center_x: int,
        center_y: int,
        width: int,
        height: int,
    ) -> None:
        super(GameObject, self).__init__(
            center_x - (width * 0.5),
            center_y - (height * 0.5),
            width, height)
        self.position: int = self.centery << 16 | self.centerx
        self.enabled: bool = True
        self.actable: bool = False
        self.collide_type: CollideType = CollideType.DISAPPEAR

    def get_color(self) -> Tuple[int, int, int]:
        return WHITE

    def act(self):
        pass

    def __new__(cls, *args, **kwargs):
        instance = super(GameObject, cls).__new__(cls)
        global generated_id
        if generated_id > 65535:
            generated_id = 0
        else:
            generated_id += 1
        instance.id = generated_id

        while instance.id in cls.id_map:
            generated_id += 1
            instance.id = generated_id
        cls.id_map[instance.id] = instance
        return instance

    def __del__(self):
        del self.id_map[self.id]
