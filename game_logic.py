# -*- coding: utf-8 -*-
"""与 Pygame 无关的游戏规则和关卡数据处理。"""

import copy

from config import BOARD_COLS, BOARD_ROWS, LEVELS, STAR_THRESHOLDS


class SearchLimitExceeded(RuntimeError):
    """DFS 为保护满格关卡而提前停止时抛出。"""


def _arrow_label(arrow):
    """返回适合日志和人工核对的、不可变的箭头标识。"""
    return (arrow["row"], arrow["col"], arrow["direction"].value)


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


def solve_level(arrows, rows=BOARD_ROWS, cols=BOARD_COLS, max_nodes=200_000):
    """用 DFS + 回溯寻找一条清空 ``arrows`` 的合法顺序。

    状态使用“仍存在箭头的索引位掩码”编码。箭头的位置和方向在一次求解中
    不变，因此相同位掩码必然拥有相同的后续选择；``visited`` 可安全剪枝。
    返回 ``[(row, col, direction), ...]``，无解返回 ``None``。

    输入列表及其中的字典绝不修改：搜索仅在深拷贝后的 ``working_arrows`` 上
    临时切换 ``eliminated``。达到 ``max_nodes`` 时抛出 SearchLimitExceeded，
    调用者可以据此给出友好提示，而不会让满格关卡无限搜索。
    """
    if max_nodes <= 0:
        raise ValueError("max_nodes 必须是正整数")

    working_arrows = copy.deepcopy(arrows)
    active_mask = 0
    for index, arrow in enumerate(working_arrows):
        arrow.setdefault("eliminated", False)
        if not arrow["eliminated"]:
            active_mask |= 1 << index

    visited = set()
    searched_nodes = 0

    def dfs(state):
        nonlocal searched_nodes
        searched_nodes += 1
        if searched_nodes > max_nodes:
            raise SearchLimitExceeded(
                f"搜索已访问 {searched_nodes} 个节点，超过上限 {max_nodes}；"
                "请提高 max_nodes 或简化关卡布局。"
            )
        if state == 0:
            return []
        if state in visited:
            return None
        visited.add(state)

        for index, arrow in enumerate(working_arrows):
            if not state & (1 << index):
                continue
            # 只复用现有路径判断；不在验证器中重写任何阻挡逻辑。
            if is_blocked(arrow, working_arrows, rows, cols):
                continue

            arrow["eliminated"] = True
            try:
                suffix = dfs(state & ~(1 << index))
            finally:
                # 无论找到解、无解还是触发节点上限，都还原搜索分支。
                arrow["eliminated"] = False
            if suffix is not None:
                return [_arrow_label(arrow)] + suffix
        return None

    return dfs(active_mask)


def verify_preset_levels(max_nodes=200_000):
    """独立验证全部预设关卡，并打印可直接用于人工复现的结果。"""
    results = []
    for level_number, level in enumerate(LEVELS, start=1):
        arrows = level["arrows"]
        try:
            solution = solve_level(arrows, BOARD_ROWS, BOARD_COLS, max_nodes)
        except SearchLimitExceeded as error:
            print(f"第 {level_number} 关：不可通关（搜索保护触发：{error}）")
            print(f"  调试：棋盘 {BOARD_ROWS}×{BOARD_COLS}，箭头布局：{[_arrow_label(a) for a in arrows]}")
            results.append(None)
            continue

        if solution is None:
            print(f"第 {level_number} 关：不可通关")
            print(f"  调试：棋盘 {BOARD_ROWS}×{BOARD_COLS}，箭头布局：{[_arrow_label(a) for a in arrows]}")
        else:
            print(f"第 {level_number} 关：可通关")
            print(f"  解法：{solution}")
        results.append(solution)
    return results


def create_level_arrows(level_index):
    """创建不带旧动画或消除状态的关卡箭头副本。"""
    arrows = copy.deepcopy(LEVELS[level_index]["arrows"])
    for arrow in arrows:
        arrow.update(eliminated=False, offset_x=0.0, offset_y=0.0)
    return arrows


def find_available_arrow(arrows):
    """返回任意一支当前可飞出的箭头，或 None。"""
    return next((arrow for arrow in arrows if not arrow["eliminated"] and not is_blocked(arrow, arrows, BOARD_ROWS, BOARD_COLS)), None)


def calculate_stars(score, elapsed_time, arrow_count, score_per_arrow):
    """根据配置的分数比例和完成时间，返回 1 到 3 星。"""
    max_score = arrow_count * score_per_arrow
    score_ratio = score / max_score if max_score else 0.0
    for stars in (3, 2):
        rule = STAR_THRESHOLDS[stars]
        if score_ratio >= rule["min_score_ratio"] and elapsed_time <= rule["max_seconds"]:
            return stars
    return 1


if __name__ == "__main__":
    verify_preset_levels()
