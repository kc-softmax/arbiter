from __future__ import annotations
import pygame
import math

from typing import Dict, Tuple, List
from maenv.dusty.enums import Team
from maenv.dusty.colors import (
    GREEN
)


class LargeGrid(pygame.Rect):

    def __init__(
        self,
        col: int,
        row: int,
        width: int,
        height: int,
        scale: int,
        unused: bool = False,
    ) -> None:
        super(LargeGrid, self).__init__(
            col * width,
            row * height,
            width,
            height)
        self.unused: bool = unused
        self.col: int = col
        self.row: int = row
        self.address: int = row << 8 & 0xff00 | col
        self.activate_step: int = 0
        self.occupier_team: Team = None
        self.child_grids: List[MiddleGrid] = []
        self.trees: List[Tree] = []
        for col in range(scale):
            for row in range(scale):
                self.child_grids.append(
                    MiddleGrid(
                        self.address,
                        self.left,
                        self.top,
                        col,
                        row,
                        width // scale,
                        height // scale,
                    )
                )

    def collide_trees(self, rect: pygame.Rect) -> list[pygame.Rect] | None:
        # rect, tree are both squre
        collide_trees = rect.collidelistall(self.trees)
        if len(collide_trees) > 0:
            return [
                self.trees[collide_tree]
                for collide_tree in collide_trees
            ]
        else:
            return None

        # for tree in self.trees:
        #     dist = math.hypot(
        #         rect.centerx - tree.centerx,
        #         rect.centery - tree.centery)
        #     if dist < rect.width * 0.5 + tree.width * 0.5:
        #         return True
        # return False

    def get_available_child_grids(self, col=-1, row=-1) -> List[MiddleGrid]:
        grids = []
        for grid in self.child_grids:
            if grid.used:
                continue
            if row > -1 and row != grid.row:
                continue
            if col > -1 and col != grid.col:
                continue
            grids.append(grid)
        return grids

    def reset(self):
        self.occupier_id: str = None
        self.activate_step = 0
        self.trees.clear()
        for grid in self.child_grids:
            grid.reset()


class MiddleGrid(pygame.Rect):

    def __init__(
        self,
        parent_address: int,
        left: int,
        top: int,
        col: int,
        row: int,
        width: int,
        height: int,
    ) -> None:
        # TODO Const
        super(MiddleGrid, self).__init__(
            left + col * width + width * 0.5 - 16,
            top + row * height + height * 0.5 - 16,
            32,
            32,)
        self.col: int = col
        self.row: int = row
        self.grid_left: int = left + col * width
        self.grid_top: int = top + row * height
        self.grid_width: int = width
        self.grid_height: int = height
        self.used: bool = False
        self.occupyable = True
        self.address: int = parent_address << 16 | row << 8 & 0xff00 | col
        self.activate_step: int = 0
        self.occupier_id: str = None
        self.occupier_team: Team = None

    def reset(self, used=False):
        self.occupier_id: str = None
        self.occupier_team: Team = None
        self.activate_step = 0
        self.used = used


class Tree(pygame.Rect):

    def __init__(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        col: int,
        row: int,
        address: int,
    ) -> None:
        super(Tree, self).__init__(
            left,
            top,
            width,
            height)
        self.address: int = address
        self.col = col
        self.row = row

    def get_color(self):
        return GREEN
