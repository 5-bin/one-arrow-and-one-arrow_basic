# -*- coding: utf-8 -*-
"""游戏主入口：通过同级模块组织并启动游戏。"""

# 兼容外部代码和现有逻辑测试从 main.py 导入游戏规则及配置。
from config import (BOARD_COLS, BOARD_ROWS, DIRECTION_STEPS, Direction, GameState,
                    LEVELS)
from game_logic import (SearchLimitExceeded, calculate_stars, create_level_arrows,
                        find_available_arrow, is_blocked, solve_level,
                        verify_preset_levels)
from game_runner import run_game


if __name__ == "__main__":
    run_game()
