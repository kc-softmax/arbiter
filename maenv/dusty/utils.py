import math
import pygame


def get_distance(src: pygame.Rect, dst: pygame.Rect):
    return math.hypot(
        src.centerx - dst.centerx,
        src.centery - dst.centery)
