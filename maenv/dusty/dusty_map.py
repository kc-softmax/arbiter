import math
import random
import pygame
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, List
from maenv.dusty.grid_objects import LargeGrid, MiddleGrid, Tree
from maenv.dusty.dataclasses import DustyMapConfig
from maenv.dusty.enums import Team
from maenv.dusty.colors import (
    BLACK,
    BLUE_DUSTY_GRID,
    YELLOW_DUSTY_GRID,
    WHITE,
)


class DustyMap(object):

    def __init__(
        self,
        np_random: np.random.Generator,
        map_config: DustyMapConfig,
    ) -> None:
        # we only using isometric map
        self.np_random: np.random.Generator = np_random
        self.grid_cols: int = map_config.grid_cols
        self.grid_rows: int = map_config.grid_rows
        self.grid_width: int = map_config.grid_width
        self.grid_height: int = map_config.grid_height
        self.grid_scale: int = map_config.grid_scale
        self.map_width: int = self.grid_cols * self.grid_width
        self.map_height: int = self.grid_rows * self.grid_height
        self.valid_grid_count: int = 0
        self.large_grids: List[LargeGrid] = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                self.large_grids.append(
                    LargeGrid(
                        col,
                        row,
                        self.grid_width,
                        self.grid_height,
                        self.grid_scale,
                        row == 0 or row == self.grid_rows - 1
                    )
                )
        self.reset(self.np_random)

    def generate_trees(self, tree_count_in_grid: int = 4) -> int:
        all_tree_count: int = 0
        used_grid_count: int = 0
        for large_grid in self.large_grids:
            if large_grid.unused:
                continue
            tree_count = self.np_random.integers(1, tree_count_in_grid)
            for _ in range(tree_count):
                available_middle_grids = large_grid.get_available_child_grids()
                select_grid: MiddleGrid = available_middle_grids[self.np_random.integers(
                    0, len(available_middle_grids))]
                select_grid.used = True
                large_grid.trees.append(Tree(
                    select_grid.grid_left,
                    select_grid.grid_top,
                    select_grid.grid_width,
                    select_grid.grid_height,
                    col=select_grid.col,
                    row=select_grid.row,
                    address=select_grid.address
                ))
            used_grid_count += self.grid_scale * self.grid_scale
            all_tree_count += tree_count
        return used_grid_count - all_tree_count

    def get_grid_address(self, x: int, y: int) -> List[Tuple[int, int]]:
        col = math.floor(x / (self.grid_width / self.grid_scale))
        row = math.floor(y / (self.grid_height / self.grid_scale))
        return col, row

    def get_grid_index_by_location(self, x: int, y: int) -> int:
        col = math.floor(x / self.grid_width)
        row = math.floor(y / self.grid_height)
        return row * self.grid_cols + col

    def get_respwan_points(
        self,
        team: Team,
        num_of_points,
    ) -> List[Tuple[int, int]]:
        if num_of_points <= 0:
            return []
        # blue respwan grid col index 0
        # yellow respwan grid col index self.grid_cols - 1
        valid_col = 0 if team == Team.BLUE else self.grid_cols - 1
        valid_middle_col = 0 if team == Team.BLUE else self.grid_scale - 1

        valid_large_grid_indexs = [
            i for i, large_grid in enumerate(self.large_grids)
            if large_grid.col == valid_col and not large_grid.unused]

        select_grid_indexes: List[int] = self.np_random.choice(
            valid_large_grid_indexs,
            num_of_points,
            replace=False)

        points = []
        for select_grid_index in select_grid_indexes:
            large_grid = self.large_grids[select_grid_index]

            available_middle_grids = large_grid.get_available_child_grids(
                col=valid_middle_col)

            select_grid = available_middle_grids[self.np_random.integers(
                0, len(available_middle_grids))]

            points.append(
                (select_grid.centerx, select_grid.centery))
            return points

    def get_random_points(
        self,
        expect_num_of_points,
        except_grid_indexes: List[int] = []
    ) -> List[Tuple[int, int]]:
        # get available cells
        available_grid_indexes: List[int] = [
            i for i, grid in enumerate(self.large_grids)
            if not grid.unused or (except_grid_indexes and i not in except_grid_indexes)]
        if expect_num_of_points > len(available_grid_indexes):
            num_of_points = len(available_grid_indexes)
        else:
            num_of_points = expect_num_of_points
            # raise ValueError(
            #     f'num_of_points({num_of_points}) is larger than available_grid_indexes({len(available_grid_indexes)})')
        select_grid_indexes: List[int] = self.np_random.choice(
            available_grid_indexes,
            num_of_points,
            replace=False)
        points = []
        for select_grid_index in select_grid_indexes:
            large_grid = self.large_grids[select_grid_index]
            available_middle_grids = large_grid.get_available_child_grids()
            select_grid = available_middle_grids[self.np_random.integers(
                0, len(available_middle_grids))]

            offset_x = self.np_random.integers(
                -math.floor(select_grid.width * 0.5), math.floor(select_grid.width * 0.5))
            offset_y = self.np_random.integers(
                -math.floor(select_grid.height * 0.5), math.floor(select_grid.height * 0.5))
            points.append(
                (select_grid.centerx + offset_x, select_grid.centery + offset_y))

        return points

    def get_compressed_surface(self) -> pygame.Surface:
        surface: pygame.Surface = pygame.Surface(
            (self.grid_cols * self.grid_scale, self.grid_rows * self.grid_scale)
        )
        surface.fill(BLACK)

        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                large_grid = self.large_grids[row * self.grid_cols + col]
                if large_grid.unused:
                    pygame.draw.rect(surface, WHITE, pygame.Rect(
                        col * self.grid_scale,
                        row * self.grid_scale,
                        self.grid_scale,
                        self.grid_scale))
                else:
                    pygame.draw.rect(surface, BLACK, pygame.Rect(
                        col * self.grid_scale,
                        row * self.grid_scale,
                        self.grid_scale,
                        self.grid_scale))
                    for middle_grid in large_grid.child_grids:
                        if middle_grid.occupier_team:
                            color = BLUE_DUSTY_GRID if middle_grid.occupier_team == Team.BLUE else YELLOW_DUSTY_GRID
                            pygame.draw.rect(
                                surface, color, pygame.Rect(
                                    col * self.grid_scale + middle_grid.col,
                                    row * self.grid_scale + middle_grid.row,
                                    1, 1
                                ))

                for tree in large_grid.trees:
                    pygame.draw.rect(
                        surface, tree.get_color(), pygame.Rect(
                            col * self.grid_scale + tree.col,
                            row * self.grid_scale + tree.row,
                            1, 1
                        ))
        return surface

    def get_surface(self) -> pygame.Surface:
        surface: pygame.Surface = pygame.Surface(
            (self.map_width, self.map_height)
        )
        surface.fill(BLACK)
        for grid in self.large_grids:
            if grid.unused:
                pygame.draw.rect(surface, WHITE, grid)
            else:
                pygame.draw.rect(surface, BLACK, grid)
                for middle_grid in grid.child_grids:
                    if middle_grid.occupier_team:
                        if middle_grid.occupier_team == Team.BLUE:
                            pygame.draw.rect(
                                surface, BLUE_DUSTY_GRID, middle_grid)
                        elif middle_grid.occupier_team == Team.YELLOW:
                            pygame.draw.rect(
                                surface, YELLOW_DUSTY_GRID, middle_grid)

            for tree in grid.trees:
                pygame.draw.rect(
                    surface, tree.get_color(), tree)
                # pygame.draw.circle(surface, tree.get_color(),
                #                    tree.center, tree.width * 0.5)
        return surface

    def reset(self, np_random: np.random.Generator):
        self.np_random: np.random.Generator = np_random
        for grid in self.large_grids:
            grid.reset()
        self.valid_grid_count = self.generate_trees()
