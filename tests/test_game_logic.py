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

    def test_t04_every_level_has_a_valid_clear_sequence(self):
        """T04：反复取任一可飞箭，验证每关均可完整清空。"""
        self.assertEqual(len(main.LEVELS), 6)
        for level_index, level in enumerate(main.LEVELS):
            arrows = main.create_level_arrows(level_index)
            cleared_count = 0
            while arrows:
                arrow = next(
                    (item for item in arrows if not main.is_blocked(
                        item, arrows, main.BOARD_ROWS, main.BOARD_COLS)),
                    None,
                )
                self.assertIsNotNone(
                    arrow,
                    f"第 {level_index + 1} 关剩余箭头没有可飞出的完整解",
                )
                self.assertFalse(
                    main.is_blocked(arrow, arrows, main.BOARD_ROWS, main.BOARD_COLS),
                    msg=f"第 {level_index + 1} 关坐标 {(arrow['row'], arrow['col'])} 不应被阻挡",
                )
                arrows.remove(arrow)
                cleared_count += 1
            self.assertEqual(cleared_count, len(level["arrows"]))

    def test_level_difficulty_data_and_final_full_board(self):
        """关卡数量递增，且最终关恰好填满固定 7×8 棋盘。"""
        arrow_counts = [len(level["arrows"]) for level in main.LEVELS]
        self.assertEqual(arrow_counts, sorted(arrow_counts))
        self.assertEqual(arrow_counts[-1], main.BOARD_ROWS * main.BOARD_COLS)
        final_positions = {(arrow["row"], arrow["col"]) for arrow in main.LEVELS[-1]["arrows"]}
        self.assertEqual(len(final_positions), main.BOARD_ROWS * main.BOARD_COLS)

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


class TestLevelSolver(unittest.TestCase):
    """DFS 关卡验证器必须使用原有阻挡规则且不污染游戏数据。"""

    def test_every_preset_level_has_a_complete_dfs_solution(self):
        for level in main.LEVELS:
            with self.subTest(level=level["name"]):
                before = [dict(arrow) for arrow in level["arrows"]]
                solution = main.solve_level(level["arrows"], main.BOARD_ROWS, main.BOARD_COLS)
                self.assertIsNotNone(solution)
                self.assertEqual(len(solution), len(level["arrows"]))
                self.assertEqual(level["arrows"], before)

    def test_solver_returns_none_for_mutually_blocked_arrows(self):
        arrows = [
            make_arrow(3, 1, main.Direction.RIGHT),
            make_arrow(3, 5, main.Direction.LEFT),
        ]
        self.assertIsNone(main.solve_level(arrows, 7, 8))

    def test_solver_uses_current_remaining_arrows_without_mutating_them(self):
        """已由玩家消除的箭头不参与搜索，且真实状态保持不变。"""
        already_removed = make_arrow(3, 1, main.Direction.RIGHT, eliminated=True)
        remaining = make_arrow(3, 5, main.Direction.RIGHT)
        arrows = [already_removed, remaining]
        before = [dict(arrow) for arrow in arrows]

        self.assertEqual(main.solve_level(arrows), [(3, 5, "RIGHT")])
        self.assertEqual(arrows, before)

    def test_solver_solution_is_legal_step_by_step(self):
        """求出的每一步都是调用同一 is_blocked 规则后当前可飞的箭头。"""
        arrows = main.create_level_arrows(1)
        solution = main.solve_level(arrows)
        self.assertIsNotNone(solution)

        for row, col, direction in solution:
            arrow = next(item for item in arrows if (
                item["row"], item["col"], item["direction"].value
            ) == (row, col, direction))
            self.assertFalse(main.is_blocked(arrow, arrows, main.BOARD_ROWS, main.BOARD_COLS))
            arrows.remove(arrow)
        self.assertEqual(arrows, [])

    def test_solver_reports_search_protection_limit(self):
        arrows = [
            make_arrow(3, 2, main.Direction.RIGHT),
            make_arrow(3, 5, main.Direction.RIGHT),
        ]
        with self.assertRaises(main.SearchLimitExceeded):
            main.solve_level(arrows, 7, 8, max_nodes=1)


class TestHintLogic(unittest.TestCase):
    """提示功能只验证候选选择，动画高亮仍由人工试玩确认。"""

    def test_hint_returns_an_unblocked_remaining_arrow(self):
        blocked = make_arrow(3, 1, main.Direction.RIGHT)
        available = make_arrow(3, 5, main.Direction.RIGHT)
        hint = main.find_available_arrow([blocked, available])
        self.assertIs(hint, available)
        self.assertFalse(main.is_blocked(hint, [blocked, available], 7, 8))

    def test_hint_returns_none_when_every_arrow_is_blocked(self):
        left = make_arrow(3, 1, main.Direction.RIGHT)
        right = make_arrow(3, 5, main.Direction.LEFT)
        self.assertIsNone(main.find_available_arrow([left, right]))


class TestStarRating(unittest.TestCase):
    """星级仅依赖配置的分数比例和完成时间，便于独立验证。"""

    def test_three_stars_requires_high_score_and_fast_time(self):
        self.assertEqual(main.calculate_stars(300, 20.0, 3, 100), 3)

    def test_two_stars_when_three_star_time_is_missed(self):
        self.assertEqual(main.calculate_stars(300, 45.0, 3, 100), 2)

    def test_one_star_when_score_or_time_does_not_meet_two_stars(self):
        self.assertEqual(main.calculate_stars(150, 61.0, 3, 100), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
