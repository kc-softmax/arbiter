from typing import Optional
from dataclasses import dataclass
from maenv.dusty.game_objects import GameObject
from maenv.dusty.grid_objects import MiddleGrid, LargeGrid
from maenv.dusty.dusty_agent import DustyAgent
from maenv.dusty.enums import CollideType


@dataclass
class Collision:
    src: DustyAgent | GameObject
    agent: Optional[DustyAgent] = None
    large_grid: Optional[LargeGrid] = None
    middle_grid: Optional[MiddleGrid] = None
    game_object: Optional[GameObject] = None
