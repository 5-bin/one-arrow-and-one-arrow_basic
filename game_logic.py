# -*- coding: utf-8 -*-
"""与 Pygame 无关的游戏规则和关卡数据处理。"""

import copy

from config import BOARD_COLS, BOARD_ROWS, LEVELS


def is_blocked(arrow, arrows, rows, cols):
    """检查箭头前方到边界间是否有未消除箭头。"""
    steps = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
    row_step, col_step = steps[arrow["direction"].value]
    active_positions = {(item["row"], item["col"]) for item in arrows if not item.get("eliminated", False)}
    check_row, check_col = arrow["row"] + row_step, arrow["col"] + col_step
    while 0 <= check_row < rows and 0 <= check_col < cols:
        if (check_row, check_col) in active_positions:
            return True
        check_row, check_col = check_row + row_step, check_col + col_step
    return False


def create_level_arrows(level_index):
    """创建不带旧动画或消除状态的关卡箭头副本。"""
    arrows = copy.deepcopy(LEVELS[level_index]["arrows"])
    for arrow in arrows:
        arrow.update(eliminated=False, offset_x=0.0, offset_y=0.0)
    return arrows


def find_available_arrow(arrows):
    """返回任意一支当前可飞出的箭头，或 None。"""
    return next((arrow for arrow in arrows if not arrow["eliminated"] and not is_blocked(arrow, arrows, BOARD_ROWS, BOARD_COLS)), None)
