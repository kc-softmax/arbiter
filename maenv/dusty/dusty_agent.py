from __future__ import annotations
import math
import numpy as np
import pygame
from typing import Deque, Tuple, List, Union
from collections import deque
from maenv.dusty.dataclasses import (
    DustyScore,
    DustyStatus,
)
from maenv.dusty.enums import (
    DustyState,
    DustyActiveAction,
    DustyControlAction,
    DeathType,
    Equipment,
    RewardType,
    Team
)
from maenv.dusty.dataclasses import DustyGameConfig, DustyStepConfig
from maenv.dusty.colors import BLUE, ORANGE


class DustyAgent(object):

    def __init__(
        self,
        id: str,
        team: Team,
    ) -> None:
        self.id = id
        self.np_random: np.random.Generator = None
        self.team: Team = team
        self.alive: bool = True
        self.game_config: DustyGameConfig = None
        self.step_config: DustyStepConfig = None
        # 이거 사용해서 새로운 coliision 확인한다.
        self.last_grid_index: int = -1
        self.load_bullet: bool = False
        self.firing_reload_time: int = 0
        self.freeze_time: int = 0
        self.retry_time: int = 0
        self.score: DustyScore = DustyScore()
        self.status: DustyStatus = DustyStatus()

        self.state: DustyState = DustyState.FREEZE
        self.killer: DustyAgent = None

        # path 로 바꾸자
        self.direction: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.direction_index: int = 0
        self.target_direction_index: int = 0

        self.foot: pygame.Rect = None
        self.body: pygame.Rect = None
        # store last 10 path for history or debug
        self.paths: Deque[pygame.math.Vector2] = deque(maxlen=10)

    @property
    def anchor(self):
        return self.paths[0]

    def set_config(self, game_config: DustyGameConfig, step_config: DustyStepConfig):
        self.game_config = game_config
        self.step_config = step_config

    def get_color(self) -> Tuple[int, int, int]:
        return BLUE if self.team == Team.BLUE else ORANGE

    def add_freeze_time(self, time: int):
        if self.freeze_time:
            self.freeze_time += time

    def act(self, actions: list[DustyActiveAction | DustyControlAction]):
        def direction_index_adjustment(index: int) -> int:
            if index == 0:
                return self.game_config.total_direction
            elif index > self.game_config.total_direction:
                return 1
            return index

        if not self.alive and not self.game_config and not self.step_config:
            return
        # processing time
        if self.state == DustyState.FREEZE:
            self.freeze_time -= 1
            if self.freeze_time < 1:
                self.state = DustyState.NORMAL
        if self.firing_reload_time > 0:
            self.firing_reload_time -= 1

        filtered_actions = set(actions)
        for action in filtered_actions:
            if not action:
                continue
            if action in list(DustyControlAction):
                match action:
                    case DustyControlAction.STOP:
                        pass
                    case DustyControlAction.LEFT:
                        self.target_direction_index = self.direction_index - 1
                    case DustyControlAction.RIGHT:
                        self.target_direction_index = self.direction_index + 1
                    case DustyControlAction.BOOST:
                        if self.state == DustyState.FREEZE:
                            continue
                        if self.status.boost_reload_gague < 1:
                            self.status.boost_gague += self.step_config.boost_step
                            self.status.boost_reload_gague = self.step_config.boost_reload_step
            elif action in list(DustyActiveAction):
                if self.state == DustyState.FREEZE or self.firing_reload_time:
                    # freeze 거나 리로드 시간이면 발사 못한다.
                    continue
                reward_required = 0
                match action:
                    case DustyActiveAction.FIRING:
                        # load a bullet
                        self.equipment = Equipment.NORMAL
                    case DustyActiveAction.SHOTGUN:
                        reward_required = self.game_config.shotgun_reward_required
                        self.equipment = Equipment.SHOTGUN
                    case DustyActiveAction.GUIDED:
                        reward_required = self.game_config.guided_reward_required
                        self.equipment = Equipment.GUIDED
                    case DustyActiveAction.REMOVER:
                        reward_required = self.game_config.remover_reward_required
                        self.equipment = Equipment.REMOVER
                if self.status.reward_gague > reward_required:
                    self.status.reward_gague -= reward_required
                    # 발사 확인
                else:
                    # 발사 x
                    self.equipment = Equipment.NORMAL
                    continue
                # currently
                self.load_bullet = True
                self.firing_reload_time = self.step_config.firing_reload_step
            else:
                if action > self.game_config.total_direction or action < 0:
                    continue
                self.target_direction_index = action

        if self.target_direction_index != self.direction_index:
            target_direction_index = direction_index_adjustment(
                self.target_direction_index)
            self.direction_index = direction_index_adjustment(
                self.direction_index)

            direction_difference = (
                target_direction_index - self.direction_index) % self.game_config.total_direction
            # Check whether clockwise rotation is better than anticlockwise
            if direction_difference <= self.game_config.total_direction / 2:
                angle = self.game_config.rotate_angle
                self.direction_index += 1
            else:
                angle = -self.game_config.rotate_angle
                self.direction_index -= 1
            self.direction = self.direction.rotate_rad(angle)

        self.state != DustyState.FREEZE and self.move()
        self.state != DustyState.FREEZE and self.sync_body()

    def move(
        self,
    ):
        stride = self.game_config.dusty_stride
        if self.status.boost_gague > 0:
            # TODO match, case
            stride *= self.game_config.dusty_boost_value
            self.status.boost_gague -= 1

        if self.status.boost_reload_gague > 0:
            self.status.boost_reload_gague -= 1

        # 다음 path 를 일단 정한다.
        # path는 speed * body_interval 만큼 생긴다.
        self.paths.appendleft(self.anchor + self.direction * stride)

    def handle_collision_with_obstacle(
        self,
        obstacle: pygame.Rect = None
    ):
        # 장애물에 걸렸을때 막히는게 아니라, 어긋나게 이동해야 한다.
        if obstacle:
            # 장애물이 있다면, 마지막 포인트에서 새롭게 계산한다.
            # 하지만 진행방향과 충돌방향이 다르다면, 그냥 진행방향으로 이동한다.
            left_collide_value = self.body.right - obstacle.left
            right_collide_value = obstacle.right - self.body.left
            top_collide_value = self.body.bottom - obstacle.top
            bottom_collide_value = obstacle.bottom - self.body.top
            # 장애물 안으로 들어간 값을 찾아 body를 밖으로 이동한다.
            # 값들이 1 이하 일 경우 밀어낸다.
            # TODO refactor
            if left_collide_value <= self.game_config.dusty_width * 0.5:
                self.anchor.x -= abs(left_collide_value)
            elif right_collide_value <= self.game_config.dusty_width * 0.5:
                self.anchor.x += abs(right_collide_value)
            elif top_collide_value <= self.game_config.dusty_height * 0.5:
                self.anchor.y -= abs(top_collide_value)
            elif bottom_collide_value <= self.game_config.dusty_height * 0.5:
                self.anchor.y += abs(bottom_collide_value)
            else:
                print('error', left_collide_value, right_collide_value,
                      top_collide_value, bottom_collide_value)
        else:
            self.paths.popleft()

        self.sync_body()

    def die(self, death_type: DeathType):
        self.alive = False
        self.death_type = death_type
        self.retry_time = self.step_config.retry_step

    def reset(
        self,
        point: Tuple[int, int],
        np_random: np.random.Generator
    ):
        if self.retry_time > 0:
            self.retry_time -= 1
            return
        self.alive = True
        self.np_random: np.random.Generator = np_random
        self.score = DustyScore()
        self.status = DustyStatus()
        self.paths.clear()
        self.paths.append(
            pygame.math.Vector2(point[0], point[1])
        )
        self.body = pygame.Rect(
            self.anchor.x - self.game_config.dusty_width * 0.5,
            self.anchor.y - self.game_config.dusty_height * 0.5,
            self.game_config.dusty_width,
            self.game_config.dusty_height,
        )

        self.foot: pygame.Rect = pygame.Rect(
            self.anchor.x - self.game_config.foot_width * 0.5,
            self.anchor.y - self.game_config.foot_height * 0.5,
            self.game_config.foot_width,
            self.game_config.foot_height,
        )

        # update direction
        if self.team == Team.BLUE:
            self.direction = pygame.math.Vector2(1, 0)
            self.direction_index = self.game_config.total_direction * 0.25
            self.target_direction_index = self.game_config.total_direction * 0.25
        else:
            self.direction = pygame.math.Vector2(-1, 0)
            self.direction_index = self.game_config.total_direction * 0.75
            self.target_direction_index = self.game_config.total_direction * 0.75

        self.freeze_time = self.step_config.freeze_step
        self.state: DustyState = DustyState.FREEZE
        self.killer = None

    def earn_reward(self, reward_type: RewardType, only_score: bool = False):
        earn_reward = 0
        match reward_type:
            case RewardType.ENERGY:
                earn_reward = self.game_config.energy_reward
                self.score.eating += 1
            case RewardType.KILLING:
                earn_reward = self.game_config.killing_reward
                self.score.killing += 1
            case RewardType.DEFENCE:
                earn_reward = self.game_config.defence_reward
                self.score.defence += 1
            case RewardType.PAINTING:
                earn_reward = self.game_config.painting_reward
                self.score.territory += 1

        if only_score:
            earn_reward = 0
            # 장비 선택이 없고, 장비가 일반일 경우 경험치 증가
        self.status.reward_gague += earn_reward

        if self.status.reward_gague > self.game_config.max_reward:
            self.status.reward_gague = self.game_config.max_reward

    def set_direction(self, direction: pygame.math.Vector2):
        self.direction.x = direction.x
        self.direction.y = direction.y
        self.direction.normalize()

    def sync_body(self):
        self.foot.width = self.game_config.foot_width
        self.foot.height = self.game_config.foot_height
        self.body.center = self.anchor
        self.foot.center = self.anchor

    def get_truncated(self):
        return not self.alive

    def encode_size(self) -> int:
        return self.game_config.dusty_height << 16 | self.game_config.dusty_width

    def encode_position(self) -> int:
        # TODO if x, y bigger than 2^16, it will be truncated
        return math.floor(self.anchor.y) << 16 | math.floor(self.anchor.x)

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if isinstance(other, str):
            return self.id == other
        if isinstance(other, DustyAgent):
            return self.id == other.id
