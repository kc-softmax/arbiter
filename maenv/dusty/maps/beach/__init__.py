import csv
from typing import List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MapConfig:
    grid_rows: int
    grid_cols: int
    grid_height: int
    grid_width: int
    scale: int


# temp
config = MapConfig(30, 30, 64, 64, 4)


def load_map_from_csv(file_name) -> List[List[int]]:
    path = Path(__file__).with_name(file_name)
    data: List[List[int]] = []
    with open(path, newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in spamreader:
            data.append([int(x) for x in row])
    return data


full_death_zone = load_map_from_csv('new_beach_map_f_death_zone.csv')
particial_death_zone = load_map_from_csv('new_beach_map_p_death_zone.csv')
block_death_zone = load_map_from_csv(
    'new_beach_map_p_death_only_server.csv')


def is_block_death(row: int, col: int, part_row: int, part_col: int) -> bool:
    grid_id = block_death_zone[row][col]
    match grid_id:
        case 10:
            return part_row > 1 and part_col < 3
        case 4:
            # col 2 is row 3
            return (part_col == 2) and (part_row == 3)
        case 2:
            # col 2, row 2
            return (part_col == 2) and (part_row == 2)
    return False


def is_across(row: int, col: int, part_row: int, part_col: int) -> bool:
    grid_id = particial_death_zone[row][col]
    match grid_id:
        case 1 | 2 | 0:
            return part_row == 3
    return False


def is_particial_death(row: int, col: int, part_row: int, part_col: int) -> bool:
    grid_id = particial_death_zone[row][col]
    match grid_id:
        case 18 | 1 | 2 | 0:
            return part_row == 3
        case 7:
            return part_col > 1 and part_row > 0
        case 14:
            return part_row > 0
        case 20:
            return part_col < 2 and part_row > 0
    return False
