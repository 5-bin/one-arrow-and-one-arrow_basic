# -*- coding: utf-8 -*-
"""游戏的界面、颜色和关卡配置。"""

from enum import Enum, auto


WINDOW_WIDTH, WINDOW_HEIGHT = 960, 700
BOARD_ROWS, BOARD_COLS = 7, 8
CELL_SIZE = 64
PAGE_MARGIN = 32
HEADER_HEIGHT = 132
BOARD_LEFT = (WINDOW_WIDTH - BOARD_COLS * CELL_SIZE) // 2
BOARD_TOP = 158
PANEL_RADIUS = 16
BUTTON_WIDTH, BUTTON_HEIGHT = 210, 58
FLY_SPEED = 720
FEEDBACK_TIME = 0.30
MAX_HINTS_PER_LEVEL = 3
HINT_TIME = 1.0

CHINESE_FONT_PATHS = (
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)

COLOR = {
    "background": (35, 59, 80), "panel": (49, 79, 103),
    "panel_border": (101, 139, 163), "board": (248, 241, 220),
    "grid": (181, 163, 124), "text": (244, 248, 250),
    "muted_text": (198, 218, 230), "accent": (48, 133, 84),
    "accent_hover": (65, 157, 101), "secondary": (79, 105, 134),
    "arrow": (238, 142, 48), "arrow_outline": (105, 58, 23),
    "arrow_hover": (255, 207, 85), "danger": (213, 69, 63),
    "danger_hover": (232, 88, 81), "title": (255, 235, 177),
    "locked": (82, 91, 101), "locked_text": (175, 184, 190),
    "current_level": (215, 152, 49), "current_level_hover": (237, 177, 62),
}


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GameState(Enum):
    START = auto()
    LEVEL_SELECT = auto()
    PLAYING = auto()
    FLYING = auto()
    WIN = auto()
    LOSE = auto()
    ALL_CLEAR = auto()


DIRECTION_STEPS = {
    Direction.UP: (-1, 0), Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1), Direction.RIGHT: (0, 1),
}


LEVELS = [
    {"name": "第 1 关", "max_mistakes": 3, "arrows": [
        {"row": 3, "col": 1, "direction": Direction.RIGHT},
        {"row": 3, "col": 5, "direction": Direction.RIGHT},
        {"row": 6, "col": 7, "direction": Direction.DOWN},
    ]},
    {"name": "第 2 关", "max_mistakes": 3, "arrows": [
        {"row": 1, "col": 3, "direction": Direction.DOWN},
        {"row": 6, "col": 3, "direction": Direction.DOWN},
        {"row": 4, "col": 7, "direction": Direction.RIGHT},
    ]},
    {"name": "第 3 关", "max_mistakes": 4, "arrows": [
        {"row": 0, "col": 4, "direction": Direction.UP},
        {"row": 2, "col": 4, "direction": Direction.UP},
        {"row": 5, "col": 1, "direction": Direction.LEFT},
        {"row": 5, "col": 5, "direction": Direction.LEFT},
        {"row": 6, "col": 7, "direction": Direction.DOWN},
    ]},
    {"name": "第 4 关", "max_mistakes": 3, "arrows": [
        {"row": 3, "col": 1, "direction": Direction.RIGHT},
        {"row": 3, "col": 4, "direction": Direction.RIGHT},
        {"row": 0, "col": 2, "direction": Direction.UP},
    ]},
    {"name": "第 5 关", "max_mistakes": 4, "arrows": [
        {"row": 1, "col": 2, "direction": Direction.DOWN},
        {"row": 4, "col": 2, "direction": Direction.DOWN},
        {"row": 6, "col": 2, "direction": Direction.DOWN},
        {"row": 5, "col": 6, "direction": Direction.RIGHT},
    ]},
    {"name": "第 6 关", "max_mistakes": 4, "arrows": [
        {"row": 2, "col": 1, "direction": Direction.RIGHT},
        {"row": 2, "col": 4, "direction": Direction.RIGHT},
        {"row": 2, "col": 6, "direction": Direction.RIGHT},
        {"row": 6, "col": 3, "direction": Direction.DOWN},
        {"row": 4, "col": 0, "direction": Direction.LEFT},
    ]},
]
