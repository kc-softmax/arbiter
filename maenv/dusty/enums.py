from __future__ import annotations
import enum


class PygameRenderMode(enum.IntEnum):
    NORMAL = 1
    COMPRESS = 2


class DustyControlAction(enum.IntEnum):
    LEFT = 25
    RIGHT = 26
    STOP = 27
    BOOST = 28


class DustyActiveAction(enum.IntEnum):
    FIRING = 50
    SHOTGUN = 51
    GUIDED = 52
    REMOVER = 53


class Equipment(enum.IntEnum):
    NORMAL = 0
    SHOTGUN = 1
    GUIDED = 2
    REMOVER = 3


class Team(enum.IntEnum):
    BLUE = 501
    YELLOW = 502


class DeathType(enum.IntEnum):
    AGENT = 1
    BLOCK = 2
    BULLET = 3
    DISCONNECT = 4


class RewardType(enum.IntEnum):
    PAINTING = 1
    KILLING = 2
    DEFENCE = 3
    ENERGY = 4


class DustyState(enum.IntEnum):
    NORMAL = 1
    FREEZE = 2


class DustyEffect(enum.IntEnum):
    MAGNET = 1
    BOOSTER = 2


class CollideType(enum.IntEnum):
    OUT_OF_GRID = 1
    AGENT = 2
    COLLEAGUE = 3
    BULLET = 4
    TREE = 5
    DISAPPEAR = 6
    DEFENCE = 7
