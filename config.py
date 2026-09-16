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
# ---------- 统一 UI 令牌：颜色、圆角、阴影、字号与间距 ----------
PANEL_RADIUS = 18
BUTTON_RADIUS = 12
UI_SHADOW_OFFSET = 5
UI_SHADOW_ALPHA = 80
UI_MARGIN = 32
UI_GAP = 16
UI_SMALL_GAP = 10
UI_CONTENT_WIDTH = 560
BUTTON_WIDTH, BUTTON_HEIGHT = 240, 52
FONT_SIZE_TITLE = 52
FONT_SIZE_LARGE = 28
FONT_SIZE_NORMAL = 23
FONT_SIZE_SMALL = 19
FONT_SIZE_TINY = 16
FLY_SPEED = 720
FEEDBACK_TIME = 0.30
MAX_HINTS_PER_LEVEL = 3
HINT_TIME = 1.0

# 计分与评价规则：每支箭头基础 100 分；误点被阻挡箭头扣 30 分（不低于 0）。
SCORE_PER_ARROW = 100
BLOCKED_ARROW_PENALTY = 30
# 三星要求高分且迅速；未达到三星、但分数和时间达到基础目标则为二星；其余为一星。
STAR_THRESHOLDS = {
    3: {"min_score_ratio": 0.90, "max_seconds": 30.0},
    2: {"min_score_ratio": 0.60, "max_seconds": 60.0},
}

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
    "background": (29, 50, 70), "panel": (48, 76, 99),
    "panel_border": (109, 147, 171), "shadow": (17, 31, 44),
    "board": (248, 241, 220),
    "grid": (181, 163, 124), "text": (244, 248, 250),
    "muted_text": (180, 204, 218), "accent": (47, 142, 89),
    "accent_hover": (66, 166, 108), "accent_pressed": (36, 115, 71),
    "secondary": (79, 111, 144), "secondary_hover": (96, 130, 164),
    "secondary_pressed": (64, 91, 119),
    "arrow": (238, 142, 48), "arrow_outline": (105, 58, 23),
    "arrow_hover": (255, 207, 85), "danger": (213, 69, 63),
    "danger_hover": (232, 88, 81), "danger_pressed": (181, 53, 49),
    "disabled": (73, 89, 102), "disabled_text": (156, 170, 180),
    "title": (255, 235, 177),
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
