"""“一箭又一箭”纯逻辑自动化测试。

本文件刻意不启动 Pygame 窗口：只测试路径判断、边界和关卡数据重置。
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


# main.py 仅在运行游戏时才使用 pygame。若测试环境未安装 pygame，提供最小
# 占位模块，使 is_blocked 和 create_level_arrows 等纯逻辑仍可被导入测试。
if importlib.util.find_spec("pygame") is None:
    sys.modules["pygame"] = types.ModuleType("pygame")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import main  # noqa: E402


def make_arrow(row, col, direction, eliminated=False):
    """构造供单元测试使用的最小箭头数据。"""
    return {
        "row": row,
        "col": col,
        "direction": direction,
        "eliminated": eliminated,
    }


class TestBlockedLogic(unittest.TestCase):
    """覆盖 T01、T02、T03 关联的核心路径判断。"""

    def test_t01_front_clear_arrow_is_not_blocked(self):
        """T01：前方没有箭头时，is_blocked 应返回 False。"""
        arrow = make_arrow(3, 1, main.Direction.RIGHT)
        self.assertFalse(main.is_blocked(arrow, [arrow], 7, 8))

    def test_t02_front_arrow_blocks_regardless_of_list_order(self):
        """T02：同一行前方有箭头时被阻挡，且不依赖列表顺序。"""
        source = make_arrow(3, 1, main.Direction.RIGHT)
        blocker = make_arrow(3, 5, main.Direction.LEFT)
        self.assertTrue(main.is_blocked(source, [blocker, source], 7, 8))

    def test_eliminated_arrow_no_longer_blocks(self):
        """已消除箭头不应成为阻挡物。"""
        source = make_arrow(3, 1, main.Direction.RIGHT)
        blocker = make_arrow(3, 5, main.Direction.LEFT, eliminated=True)
        self.assertFalse(main.is_blocked(source, [source, blocker], 7, 8))

    def test_t03_all_outward_edge_arrows_are_safe(self):
        """T03：四个边缘朝外方向均可飞出，且不会发生数组越界。"""
        edge_arrows = [
            make_arrow(0, 4, main.Direction.UP),
            make_arrow(6, 4, main.Direction.DOWN),
            make_arrow(3, 0, main.Direction.LEFT),
            make_arrow(3, 7, main.Direction.RIGHT),
        ]
        for arrow in edge_arrows:
            with self.subTest(direction=arrow["direction"]):
                self.assertFalse(main.is_blocked(arrow, [arrow], 7, 8))

    def test_up_down_left_right_scan_only_the_forward_path(self):
        """四个方向仅检查前方；后方或侧面箭头不应阻挡。"""
        cases = [
            (make_arrow(3, 3, main.Direction.UP), make_arrow(1, 3, main.Direction.DOWN)),
            (make_arrow(3, 3, main.Direction.DOWN), make_arrow(5, 3, main.Direction.UP)),
            (make_arrow(3, 3, main.Direction.LEFT), make_arrow(3, 1, main.Direction.RIGHT)),
            (make_arrow(3, 3, main.Direction.RIGHT), make_arrow(3, 5, main.Direction.LEFT)),
        ]
        for source, blocker in cases:
            with self.subTest(direction=source["direction"]):
                self.assertTrue(main.is_blocked(source, [source, blocker], 7, 8))


class TestLevelData(unittest.TestCase):
    """验证 T04、T06 关联的关卡可解性和重置数据。"""

    SOLUTIONS = [
        [(3, 5), (3, 1), (6, 7)],
        [(6, 3), (1, 3), (4, 7)],
        [(0, 4), (2, 4), (5, 1), (5, 5), (6, 7)],
    ]

    def test_t04_every_level_has_a_valid_clear_sequence(self):
        """T04 前置条件：按给定顺序模拟消除，三关都能清空。"""
        for level_index, solution in enumerate(self.SOLUTIONS):
            arrows = main.create_level_arrows(level_index)
            for row, col in solution:
                arrow = next(item for item in arrows if item["row"] == row and item["col"] == col)
                self.assertFalse(
                    main.is_blocked(arrow, arrows, main.BOARD_ROWS, main.BOARD_COLS),
                    msg=f"第 {level_index + 1} 关坐标 {(row, col)} 不应被阻挡",
                )
                arrows.remove(arrow)
            self.assertEqual(arrows, [], f"第 {level_index + 1} 关应被完全清空")

    def test_t06_restart_creates_a_clean_deep_copy(self):
        """T06：重开后箭头位置、偏移和消除状态均恢复，且不污染原关卡。"""
        playing_arrows = main.create_level_arrows(0)
        playing_arrows[0]["eliminated"] = True
        playing_arrows[0]["offset_x"] = 123.0
        restarted_arrows = main.create_level_arrows(0)

        self.assertFalse(restarted_arrows[0]["eliminated"])
        self.assertEqual(restarted_arrows[0]["offset_x"], 0.0)
        self.assertEqual(restarted_arrows[0]["offset_y"], 0.0)
        self.assertEqual(len(restarted_arrows), len(main.LEVELS[0]["arrows"]))
        self.assertNotEqual(id(playing_arrows[0]), id(restarted_arrows[0]))

    def test_t05_each_level_has_positive_initial_mistakes(self):
        """T05 前置条件：每关均有可耗尽的正整数失误次数。"""
        for level in main.LEVELS:
            with self.subTest(level=level["name"]):
                self.assertIsInstance(level["max_mistakes"], int)
                self.assertGreater(level["max_mistakes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
