from typing import Optional
from dataclasses import dataclass


@dataclass
class Log:
    pass


@dataclass
class NewDustyLog(Log):
    dusty_id: int


@dataclass
class RemoveDustyLog(Log):
    dusty_id: int


@dataclass
class NewEnergyLog(Log):
    energy_id: int
    position: int


@dataclass
class RemoveEnergyLog(Log):
    energy_id: int
    dusty_id: Optional[str]


@dataclass
class NewBulletLog(Log):
    bullet_id: int
    direction_x: float
    direction_y: float
    stride: float
    size: int
    position: int
    bullet_type: int
    is_blue: bool


@dataclass
class UpdateBulletLog(Log):
    bullet_id: int
    target_id: str


@dataclass
class RemoveBulletLog(Log):
    bullet_id: int
    collide_type: int


@dataclass
class ChangeGridLog(Log):
    grid_address: int
    occupier_id: str
    occupier_team: int


@dataclass
class NewTreeLog(Log):
    dusty_id: int


@dataclass
class NewDustyLog(Log):
    dusty_id: int
