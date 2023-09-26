from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, fields, field
from maenv.dusty.enums import (
    Equipment,
)

import math


@dataclass
class DustyScore:
    killing: int = 0
    defence: int = 0
    death: int = 0
    eating: int = 0
    territory: int = 0
    score: int = 0
    firing_count: int = 0


@dataclass
class DustyStatus:
    reward_gague: int = 0
    boost_gague: int = 0
    boost_reload_gague: int = 0


@dataclass
class DustyMapConfig:
    grid_rows: int = 4
    grid_cols: int = 6
    grid_height: int = 384
    grid_width: int = 384
    grid_scale: int = 6


@dataclass
class DustyStepConfig:
    # step - frame_rate 1 기준
    game_step: int = 90  # 90sec
    boost_step: int = 2  # 2sec
    freeze_step: int = 3  # 3sec
    boost_reload_step: int = 5  # 5sec
    firing_reload_step: int = 1  # 1sec
    retry_step: int = 5  # 5sec

    def __init__(self, **kwargs):
        frame_rate = kwargs.pop('step_rate', 15)
        super(DustyStepConfig, self).__init__(**kwargs)
        for field in fields(self):
            if not isinstance(getattr(self, field.name), int):
                continue
            fixed_value = math.floor(
                getattr(self, field.name) * frame_rate)
            setattr(
                self,
                field.name,
                fixed_value)


@dataclass
class DustyGameConfig:
    map_config: DustyMapConfig = field(
        default_factory=lambda: defaultdict(DustyMapConfig))
    max_energy_in_step: int = 15

    # common game object
    default_object_size: int = 12

    # dusty default
    total_direction: int = 24
    rotate_angle: float = math.pi * 2 / total_direction

    dusty_width: int = 36
    dusty_height: int = 36
    foot_width: int = 36
    foot_height: int = 36
    dusty_stride: float = 6.0
    dusty_boost_value: int = 2

    bullet_size: int = 18
    bullet_stride: float = 15.0
    bullet_defence_distance: int = 256

    shotgun_bullet_count: int = 5
    shotgun_bullet_size: int = 12
    shotgun_bullet_stride: float = 18.0
    shotgun_bullet_angle: float = math.pi / 36
    shotgun_reward_required: int = 20

    guided_bullet_size: int = 24
    guided_bullet_stride: float = 10.0
    guided_reward_required: int = 25

    remover_bullet_size: int = 48
    remover_bullet_stride: float = 20.0
    remover_reward_required: int = 25

    max_reward: int = 100
    energy_reward: int = 2
    painting_reward: int = 3
    killing_reward: int = 20
    defence_reward: int = 20
