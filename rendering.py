# -*- coding: utf-8 -*-
"""Pygame 字体与界面绘制函数。"""

from pathlib import Path

import pygame

from config import (BOARD_COLS, BOARD_LEFT, BOARD_ROWS, BOARD_TOP, CELL_SIZE,
                    CHINESE_FONT_PATHS, COLOR, DIRECTION_STEPS, PANEL_RADIUS)


def get_font(size):
    for font_path in CHINESE_FONT_PATHS:
        if Path(font_path).is_file():
            try:
                return pygame.font.Font(font_path, size)
            except pygame.error:
                continue
    for font_name in ("PingFang SC", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        font_path = pygame.font.match_font(font_name)
        if font_path:
            return pygame.font.Font(font_path, size)
    return pygame.font.Font(None, size)


def draw_text(screen, text, font, color, center):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=center))


def draw_panel(screen, rect):
    pygame.draw.rect(screen, COLOR["panel"], rect, border_radius=PANEL_RADIUS)
    pygame.draw.rect(screen, COLOR["panel_border"], rect, width=2, border_radius=PANEL_RADIUS)


def draw_button(screen, rect, text, font, mouse_position, color_name="accent"):
    hovered = rect.collidepoint(mouse_position)
    if color_name == "danger":
        fill = COLOR["danger_hover"] if hovered else COLOR["danger"]
    elif color_name == "current_level":
        fill = COLOR["current_level_hover"] if hovered else COLOR["current_level"]
    elif color_name == "locked":
        fill = COLOR["locked"]
    elif color_name == "secondary":
        fill = tuple(min(255, value + 18) for value in COLOR["secondary"]) if hovered else COLOR["secondary"]
    else:
        fill = COLOR["accent_hover"] if hovered else COLOR["accent"]
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, (232, 245, 236), rect, width=2, border_radius=12)
    text_color = COLOR["locked_text"] if color_name == "locked" else COLOR["text"]
    draw_text(screen, text, font, text_color, rect.center)


def draw_arrow(screen, arrow, fill_color, highlighted=False):
    center_x = BOARD_LEFT + arrow["col"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_x"]
    center_y = BOARD_TOP + arrow["row"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_y"]
    if highlighted:
        pygame.draw.circle(screen, (255, 234, 154), (round(center_x), round(center_y)), 27)
    base_points = [(0, -24), (17, -3), (8, -3), (8, 23), (-8, 23), (-8, -3), (-17, -3)]
    points = []
    for point_x, point_y in base_points:
        direction = arrow["direction"]
        if direction.name == "DOWN": point_x, point_y = -point_x, -point_y
        elif direction.name == "LEFT": point_x, point_y = point_y, -point_x
        elif direction.name == "RIGHT": point_x, point_y = -point_y, point_x
        points.append((center_x + point_x, center_y + point_y))
    pygame.draw.polygon(screen, fill_color, points)
    pygame.draw.polygon(screen, COLOR["arrow_outline"], points, width=2)


def draw_board(screen, arrows, feedback_arrow=None, hovered_arrow=None, hint_arrow=None):
    board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_COLS * CELL_SIZE, BOARD_ROWS * CELL_SIZE)
    pygame.draw.rect(screen, (28, 45, 58), board_rect.inflate(12, 12), border_radius=12)
    pygame.draw.rect(screen, COLOR["board"], board_rect, border_radius=8)
    for row in range(BOARD_ROWS + 1):
        y = BOARD_TOP + row * CELL_SIZE
        pygame.draw.line(screen, COLOR["grid"], (BOARD_LEFT, y), (BOARD_LEFT + BOARD_COLS * CELL_SIZE, y), 2)
    for col in range(BOARD_COLS + 1):
        x = BOARD_LEFT + col * CELL_SIZE
        pygame.draw.line(screen, COLOR["grid"], (x, BOARD_TOP), (x, BOARD_TOP + BOARD_ROWS * CELL_SIZE), 2)
    for arrow in arrows:
        if not arrow["eliminated"]:
            is_hint = arrow is hint_arrow
            color = COLOR["danger"] if arrow is feedback_arrow else COLOR["arrow_hover"] if is_hint else COLOR["arrow"]
            draw_arrow(screen, arrow, color, arrow is hovered_arrow or is_hint)


def arrow_at_position(arrows, mouse_position):
    mouse_x, mouse_y = mouse_position
    col = (mouse_x - BOARD_LEFT) // CELL_SIZE
    row = (mouse_y - BOARD_TOP) // CELL_SIZE
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return None
    return next((arrow for arrow in arrows if not arrow["eliminated"] and arrow["row"] == row and arrow["col"] == col), None)
