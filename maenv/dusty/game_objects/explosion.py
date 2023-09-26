import pygame
from maenv.dusty.game_objects import GameObject
from maenv.dusty.enums import Team


class Explosion(GameObject):

    def __init__(
        self,
        center_x: int,
        center_y: int,
        width: int,
        height: int,
        bomber: str,
        team: Team,
        generate_step: int,
    ) -> None:
        super(Explosion, self).__init__(center_x, center_y, width, height)
        self.generate_step: int = generate_step
        self.bomber: str = bomber
        self.team: Team = team
