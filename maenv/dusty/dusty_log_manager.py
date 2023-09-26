import pygame
from typing import Dict, Tuple, List, Deque
from collections import deque
from maenv.dusty.dusty_agent import DustyAgent
from maenv.dusty.grid_objects import MiddleGrid
from maenv.dusty.game_objects import Energy, Bullet
from maenv.dusty.enums import Team, CollideType
from maenv.dusty.logs import (
    Log,
    NewDustyLog,
    RemoveDustyLog,
    NewBulletLog,
    UpdateBulletLog,
    NewEnergyLog,
    RemoveEnergyLog,
    ChangeGridLog,
    RemoveBulletLog,
)


class DustyLogManager(object):

    def __init__(
        self,
        max_logs=65535,
    ) -> None:
        self.logs: Deque[Deque[Log]] = deque(maxlen=max_logs)

    def addDusty(self, dusty: DustyAgent):
        self.logs and self.logs[-1].append(NewDustyLog(dusty.id))

    def removeDusty(self, dusty: DustyAgent):
        self.logs and self.logs[-1].append(RemoveDustyLog(dusty.id))

    def addEnergy(self, energy: Energy):
        self.logs and self.logs[-1].append(NewEnergyLog(
            energy.id, energy.position))

    def removeEnergy(self, energy: Energy):
        if not energy.acquirers:
            self.logs and self.logs[-1].append(
                RemoveEnergyLog(energy.id, None))
        for acquirer in energy.acquirers:
            self.logs and self.logs[-1].append(
                RemoveEnergyLog(energy.id, acquirer))

    def addBullet(self, bullet: Bullet):
        self.logs and self.logs[-1].append(NewBulletLog(
            bullet.id,
            bullet.direction.x,
            bullet.direction.y,
            bullet.stride,
            bullet.size,
            bullet.position,
            bullet.bullet_type,
            bullet.team == Team.BLUE))

    def updateBullet(self, bullet: Bullet):
        self.logs and self.logs[-1].append(UpdateBulletLog(
            bullet.id, bullet.target_id))

    def removeBullet(self, bullet: Bullet):
        self.logs and self.logs[-1].append(
            RemoveBulletLog(bullet.id, bullet.collide_type))

    def changeGrid(self, grid: MiddleGrid):
        self.logs and self.logs[-1].append(
            ChangeGridLog(
                grid.address,
                grid.occupier_id,
                grid.occupier_team))

    def getLastLogs(self) -> List[Log]:
        return list(self.logs[-1])

    def next_step(self):
        self.logs.append(deque())

    def clear(self):
        self.logs.clear()
