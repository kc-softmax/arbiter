import pygame
from maenv.dusty.game_objects import GameObject
from maenv.dusty.enums import Team, Equipment
from maenv.dusty.colors import PURPLE


class Bullet(GameObject):

    def __init__(
        self,
        center_x: int,
        center_y: int,
        direction: pygame.math.Vector2,
        shooter: str,
        team: Team,
        generate_step: int,
        size: int,
        stride: float,
        bullet_type: Equipment
    ) -> None:
        super(Bullet, self).__init__(center_x, center_y, size, size)
        self.direction: pygame.math.Vector2 = direction
        self.generate_step: int = generate_step
        self.stride: float = stride
        self.shooter: str = shooter
        self.lock_on: bool = False
        self.target_id: str = None
        self.target_location: pygame.math.Vector2 = None
        self.team: Team = team
        self.bullet_type: Equipment = bullet_type
        self.actable = True

    def get_color(self):
        return PURPLE

    def set_target(self, target_id: str, target_location: pygame.math.Vector2):
        self.lock_on = True
        self.target_id = target_id
        self.target_location = target_location

    def update_target(self, target_location: pygame.math.Vector2):
        self.target_location = target_location

    def release_target(self):
        self.target_id = None
        self.target_location = None

    def act(self):
        if self.target_location:
            # 방향을 회전시켜야 한다.
            to_direction = (
                self.target_location -
                pygame.math.Vector2(self.center))
            self.direction = self.direction.lerp(
                to_direction, 0.02).normalize()

        next_point: pygame.math.Vector2 = self.center + self.direction * self.stride
        self.center = next_point
