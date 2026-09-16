# -*- coding: utf-8 -*-
"""“一箭又一箭”Pygame 游戏运行循环。"""

import copy
import math
import sys
from enum import Enum, auto
from pathlib import Path

import pygame


# ---------- 可配置的界面与玩法常量 ----------
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

# 明确指定含中文字符的字体文件，避免 SysFont 找不到字体时静默回退为
# Pygame 默认字体，进而将中文渲染为方块或乱码。按当前系统依次尝试。
CHINESE_FONT_PATHS = (
    "/System/Library/Fonts/STHeiti Light.ttc",       # macOS
    "/System/Library/Fonts/Hiragino Sans GB.ttc",    # macOS
    "/Library/Fonts/Arial Unicode.ttf",              # macOS（部分设备）
    "C:/Windows/Fonts/msyh.ttc",                     # Windows 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",                   # Windows 黑体
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # 常见 Linux 中文字体
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
}


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GameState(Enum):
    START = auto()
    PLAYING = auto()
    FLYING = auto()
    WIN = auto()
    LOSE = auto()
    ALL_CLEAR = auto()


DIRECTION_STEPS = {
    Direction.UP: (-1, 0), Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1), Direction.RIGHT: (0, 1),
}


# 关卡数据只在 config.py 维护。这里转换 Direction 类型，以复用运行器原有绘制和路径判断。
from config import LEVELS as CONFIG_LEVELS

LEVELS = copy.deepcopy(CONFIG_LEVELS)
for _level in LEVELS:
    for _arrow in _level["arrows"]:
        _arrow["direction"] = Direction(_arrow["direction"].value)


def is_blocked(arrow, arrows, rows, cols):
    """检查箭头前方到边界间是否有未消除箭头；按坐标查找，不依赖列表顺序。"""
    row_step, col_step = DIRECTION_STEPS[arrow["direction"]]
    active_positions = {
        (item["row"], item["col"])
        for item in arrows if not item.get("eliminated", False)
    }
    check_row, check_col = arrow["row"] + row_step, arrow["col"] + col_step
    while 0 <= check_row < rows and 0 <= check_col < cols:
        if (check_row, check_col) in active_positions:
            return True
        check_row, check_col = check_row + row_step, check_col + col_step
    return False


def create_level_arrows(level_index):
    """深拷贝关卡数据，重开或切关不会保留旧箭头的动画/消除状态。"""
    arrows = copy.deepcopy(LEVELS[level_index]["arrows"])
    for arrow in arrows:
        arrow.update(eliminated=False, offset_x=0.0, offset_y=0.0)
    return arrows


def find_available_arrow(arrows):
    """复用 is_blocked 找到任意一支当前可飞出的箭头；找不到则返回 None。"""
    for arrow in arrows:
        if not arrow["eliminated"] and not is_blocked(arrow, arrows, BOARD_ROWS, BOARD_COLS):
            return arrow
    return None


def get_font(size):
    """加载具有中文字形的字体文件；最后才尝试系统字体名称。"""
    for font_path in CHINESE_FONT_PATHS:
        if Path(font_path).is_file():
            try:
                return pygame.font.Font(font_path, size)
            except pygame.error:
                # 个别系统可能不支持某种字体集合格式，继续尝试下一项。
                continue

    # match_font 返回真实文件路径，优于 SysFont 的无提示默认字体回退。
    for font_name in ("PingFang SC", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        font_path = pygame.font.match_font(font_name)
        if font_path:
            return pygame.font.Font(font_path, size)

    # 极少数未安装中文字体的环境只能显示英文；提示用户安装字体。
    return pygame.font.Font(None, size)


def draw_text(screen, text, font, color, center):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=center))


def draw_panel(screen, rect):
    pygame.draw.rect(screen, COLOR["panel"], rect, border_radius=PANEL_RADIUS)
    pygame.draw.rect(screen, COLOR["panel_border"], rect, width=2, border_radius=PANEL_RADIUS)


def draw_button(screen, rect, text, font, mouse_position, color_name="accent"):
    """按钮绘制和点击区域统一使用同一个 rect。"""
    hovered = rect.collidepoint(mouse_position)
    if color_name == "danger":
        fill = COLOR["danger_hover"] if hovered else COLOR["danger"]
    elif color_name == "secondary":
        fill = tuple(min(255, value + 18) for value in COLOR["secondary"]) if hovered else COLOR["secondary"]
    else:
        fill = COLOR["accent_hover"] if hovered else COLOR["accent"]
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, (232, 245, 236), rect, width=2, border_radius=12)
    draw_text(screen, text, font, COLOR["text"], rect.center)


def draw_arrow(screen, arrow, fill_color, highlighted=False):
    """绘制方向明确的箭头；高亮时加亮色圆形底座。"""
    center_x = BOARD_LEFT + arrow["col"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_x"]
    center_y = BOARD_TOP + arrow["row"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_y"]
    if highlighted:
        pygame.draw.circle(screen, (255, 234, 154), (round(center_x), round(center_y)), 27)

    # 以“向上”为基础形状旋转，箭头头部和杆部可清晰识别。
    base_points = [(0, -24), (17, -3), (8, -3), (8, 23), (-8, 23), (-8, -3), (-17, -3)]
    points = []
    for point_x, point_y in base_points:
        if arrow["direction"] == Direction.DOWN:
            point_x, point_y = -point_x, -point_y
        elif arrow["direction"] == Direction.LEFT:
            point_x, point_y = point_y, -point_x
        elif arrow["direction"] == Direction.RIGHT:
            point_x, point_y = -point_y, point_x
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
    """点击或悬停空白格/棋盘外时安全返回 None。"""
    mouse_x, mouse_y = mouse_position
    col = (mouse_x - BOARD_LEFT) // CELL_SIZE
    row = (mouse_y - BOARD_TOP) // CELL_SIZE
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return None
    return next((arrow for arrow in arrows if not arrow["eliminated"] and arrow["row"] == row and arrow["col"] == col), None)


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    title_font, large_font = get_font(FONT_SIZE_TITLE), get_font(FONT_SIZE_LARGE)
    normal_font, small_font, tiny_font = get_font(FONT_SIZE_NORMAL), get_font(FONT_SIZE_SMALL), get_font(FONT_SIZE_TINY)

    state, level_index = GameState.START, 0
    # 仅保存本次运行的通关进度；第 1 关始终默认解锁。
    highest_unlocked_index = 0
    best_stars = [0] * len(LEVELS)
    arrows = create_level_arrows(level_index)
    remaining_mistakes = LEVELS[level_index]["max_mistakes"]
    score, elapsed_time, earned_stars = 0, 0.0, 0
    flying_arrow = feedback_arrow = None
    feedback_elapsed, lose_after_feedback = 0.0, False
    hints_remaining = MAX_HINTS_PER_LEVEL
    hint_arrow = None
    hint_elapsed = 0.0
    message = ""
    modal = ModalDialog()

    start_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 330, BUTTON_WIDTH, BUTTON_HEIGHT)
    level_select_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 396, BUTTON_WIDTH, BUTTON_HEIGHT)
    quit_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 462, BUTTON_WIDTH, BUTTON_HEIGHT)
    select_home_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 590, BUTTON_WIDTH, 46)
    level_buttons = [
        pygame.Rect(250 + (index % 3) * 160, 245 + (index // 3) * 110, 140, 76)
        for index in range(len(LEVELS))
    ]
    restart_button = pygame.Rect(BOARD_LEFT + 20, 634, 150, 40)
    hint_button = pygame.Rect(BOARD_LEFT + 181, 634, 150, 40)
    menu_button = pygame.Rect(BOARD_LEFT + 342, 634, 150, 40)
    next_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)
    home_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 505, BUTTON_WIDTH, BUTTON_HEIGHT)
    retry_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)

    def load_level(new_index):
        """唯一的关卡重置入口，保证切关和重开不残留任何动画状态。"""
        nonlocal level_index, arrows, remaining_mistakes, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, hints_remaining, hint_arrow, hint_elapsed, message
        nonlocal score, elapsed_time, earned_stars
        level_index = new_index
        arrows = create_level_arrows(level_index)
        remaining_mistakes = LEVELS[level_index]["max_mistakes"]
        score, elapsed_time, earned_stars = 0, 0.0, 0
        flying_arrow = feedback_arrow = None
        feedback_elapsed, lose_after_feedback = 0.0, False
        hints_remaining = MAX_HINTS_PER_LEVEL
        hint_arrow, hint_elapsed = None, 0.0
        message = "点击没有阻挡的箭头，让它飞出棋盘"

    def abandon_current_round():
        """返回菜单时仅清理本局临时数据，不影响解锁和最高星级。"""
        nonlocal arrows, remaining_mistakes, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, hints_remaining, hint_arrow, hint_elapsed
        nonlocal score, elapsed_time, earned_stars, message, state
        arrows = []
        remaining_mistakes = 0
        flying_arrow = feedback_arrow = hint_arrow = None
        feedback_elapsed, hint_elapsed, lose_after_feedback = 0.0, 0.0, False
        hints_remaining, score, elapsed_time, earned_stars = 0, 0, 0.0, 0
        message = ""
        state = GameState.START

    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0
        mouse_position = pygame.mouse.get_pos()
        layout_offset = (screen.get_width() - WINDOW_WIDTH) // 2

        def ui_rect(rect):
            return rect.move(layout_offset, 0)

        # 仅允许正常可操作期间计时；飞行、碰撞反馈及结算页面均暂停。
        if state == GameState.PLAYING and feedback_arrow is None and not modal.is_open:
            elapsed_time += delta_time

        # 提示只维持一秒，不会自动消除箭头。
        if hint_arrow is not None and not modal.is_open:
            hint_elapsed += delta_time
            if hint_elapsed >= HINT_TIME:
                hint_arrow, hint_elapsed = None, 0.0

        # 飞行动画期间 state 为 FLYING，所有点击均不会处理。
        if state == GameState.FLYING and flying_arrow is not None:
            row_step, col_step = DIRECTION_STEPS[flying_arrow["direction"]]
            flying_arrow["offset_x"] += col_step * FLY_SPEED * delta_time
            flying_arrow["offset_y"] += row_step * FLY_SPEED * delta_time
            board_left = (screen.get_width() - BOARD_COLS * CELL_SIZE) // 2
            center_x = board_left + (flying_arrow["col"] + 0.5) * CELL_SIZE + flying_arrow["offset_x"]
            center_y = BOARD_TOP + (flying_arrow["row"] + 0.5) * CELL_SIZE + flying_arrow["offset_y"]
            outside = (center_x < board_left - CELL_SIZE or center_x > board_left + BOARD_COLS * CELL_SIZE + CELL_SIZE or center_y < BOARD_TOP - CELL_SIZE or center_y > BOARD_TOP + BOARD_ROWS * CELL_SIZE + CELL_SIZE)
            if outside:
                # 身份和成员检查确保同一箭头绝不会被重复删除。
                if flying_arrow in arrows:
                    arrows.remove(flying_arrow)
                    score += SCORE_PER_ARROW
                flying_arrow = None
                hint_arrow, hint_elapsed = None, 0.0
                if not arrows:
                    earned_stars = calculate_stars(
                        score, elapsed_time, len(LEVELS[level_index]["arrows"]), SCORE_PER_ARROW,
                    )
                    best_stars[level_index] = max(best_stars[level_index], earned_stars)
                    # 完成第 N 关后，开放第 N+1 关；最后一关不再增加索引。
                    highest_unlocked_index = max(
                        highest_unlocked_index,
                        min(level_index + 1, len(LEVELS) - 1),
                    )
                    state = GameState.ALL_CLEAR if level_index == len(LEVELS) - 1 else GameState.WIN
                else:
                    state = GameState.PLAYING
                message = "成功飞出！"

        # 碰撞时按箭头方向所在轴晃动，红色由 draw_board 保持到反馈结束。
        if feedback_arrow is not None:
            feedback_elapsed += delta_time
            row_step, col_step = DIRECTION_STEPS[feedback_arrow["direction"]]
            shake = math.sin(feedback_elapsed * 48) * 8
            feedback_arrow["offset_x"] = shake if col_step else 0.0
            feedback_arrow["offset_y"] = shake if row_step else 0.0
            if feedback_elapsed >= FEEDBACK_TIME:
                feedback_arrow["offset_x"] = feedback_arrow["offset_y"] = 0.0
                feedback_arrow = None
                if lose_after_feedback:
                    state = GameState.LOSE
                lose_after_feedback = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                modal.open("quit")
                continue
            elif event.type == pygame.VIDEORESIZE:
                # 保持最低设计尺寸，避免棋盘或底部操作栏被裁切。
                screen = pygame.display.set_mode(
                    (max(WINDOW_WIDTH, event.w), max(WINDOW_HEIGHT, event.h)), pygame.RESIZABLE,
                )
            if modal.is_open:
                decision = modal.handle_event(event, screen)
                if decision == "confirm":
                    if modal.action == "quit":
                        running = False
                    else:
                        abandon_current_round()
                    modal.close()
                elif decision == "cancel":
                    modal.close()
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # 动画及碰撞反馈期间不允许中断本局。
                if state in (GameState.PLAYING, GameState.LEVEL_SELECT, GameState.WIN, GameState.LOSE, GameState.ALL_CLEAR) and flying_arrow is None and feedback_arrow is None:
                    modal.open("return_menu")
                continue
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == GameState.START and ui_rect(start_button).collidepoint(event.pos):
                    load_level(0)
                    state = GameState.PLAYING
                elif state == GameState.START and ui_rect(level_select_button).collidepoint(event.pos):
                    state = GameState.LEVEL_SELECT
                elif state == GameState.START and ui_rect(quit_button).collidepoint(event.pos):
                    modal.open("quit")
                elif state == GameState.LEVEL_SELECT:
                    if ui_rect(select_home_button).collidepoint(event.pos):
                        state = GameState.START
                    else:
                        for selected_index, button in enumerate(level_buttons):
                            if (selected_index <= highest_unlocked_index
                                    and ui_rect(button).collidepoint(event.pos)):
                                load_level(selected_index)
                                state = GameState.PLAYING
                                break
                elif state == GameState.PLAYING and ui_rect(restart_button).collidepoint(event.pos):
                    load_level(level_index)
                elif state == GameState.PLAYING and ui_rect(hint_button).collidepoint(event.pos):
                    if hints_remaining <= 0:
                        message = "本关提示已用完"
                    else:
                        candidate = find_available_arrow(arrows)
                        if candidate is None:
                            message = "当前无可用提示"
                        else:
                            hints_remaining -= 1
                            hint_arrow, hint_elapsed = candidate, 0.0
                            message = "提示：高亮箭头可以飞出"
                elif state == GameState.PLAYING and ui_rect(menu_button).collidepoint(event.pos):
                    # 飞出或碰撞中无法到达此分支，避免中断动画。
                    if flying_arrow is None and feedback_arrow is None:
                        modal.open("return_menu")
                # 碰撞反馈仍未结束时锁定箭头输入；空白处点击安全忽略。
                elif state == GameState.PLAYING and feedback_arrow is None:
                    clicked_arrow = arrow_at_position(arrows, event.pos, screen.get_width())
                    if clicked_arrow is not None:
                        hint_arrow, hint_elapsed = None, 0.0
                        if is_blocked(clicked_arrow, arrows, BOARD_ROWS, BOARD_COLS):
                            remaining_mistakes -= 1
                            score = max(0, score - BLOCKED_ARROW_PENALTY)
                            feedback_arrow, feedback_elapsed = clicked_arrow, 0.0
                            lose_after_feedback = remaining_mistakes <= 0
                            message = "路径被阻挡，失误 -1"
                        else:
                            flying_arrow = clicked_arrow
                            state, message = GameState.FLYING, "成功飞出！"
                elif state == GameState.WIN and ui_rect(next_button).collidepoint(event.pos):
                    load_level(level_index + 1)
                    state = GameState.PLAYING
                elif state == GameState.LOSE:
                    if ui_rect(retry_button).collidepoint(event.pos):
                        load_level(level_index)
                        state = GameState.PLAYING
                    elif ui_rect(home_button).collidepoint(event.pos):
                        state = GameState.START
                elif state == GameState.ALL_CLEAR and ui_rect(home_button).collidepoint(event.pos):
                    state = GameState.START

        screen.fill(COLOR["background"])
        if state == GameState.START:
            draw_panel(screen, ui_rect(pygame.Rect(200, 125, 560, 430)))
            draw_text(screen, "一箭又一箭", title_font, COLOR["title"], (480 + layout_offset, 210))
            draw_text(screen, "用正确顺序让所有箭头飞出棋盘", normal_font, COLOR["muted_text"], (480 + layout_offset, 270))
            draw_button(screen, ui_rect(start_button), "开始游戏", large_font, mouse_position)
            draw_button(screen, ui_rect(level_select_button), "关卡选择", large_font, mouse_position, "secondary")
            draw_button(screen, ui_rect(quit_button), "退出游戏", large_font, mouse_position, "danger")
        elif state == GameState.LEVEL_SELECT:
            draw_panel(screen, ui_rect(pygame.Rect(170, 120, 620, 540)))
            draw_text(screen, "关卡选择", title_font, COLOR["title"], (480 + layout_offset, 185))
            draw_text(screen, "完成当前关卡即可解锁下一关", small_font, COLOR["muted_text"], (480 + layout_offset, 215))
            draw_text(screen, "金色：当前    蓝色：已解锁    灰色：未解锁", small_font, COLOR["muted_text"], (480 + layout_offset, 565))
            for selected_index, button in enumerate(level_buttons):
                if selected_index > highest_unlocked_index:
                    style = "locked"
                elif selected_index == level_index:
                    style = "current_level"
                else:
                    style = "secondary"
                stars = "★" * best_stars[selected_index] + "☆" * (3 - best_stars[selected_index])
                draw_button(screen, ui_rect(button), f"第 {selected_index + 1} 关 {stars}", tiny_font, mouse_position, style)
            draw_button(screen, ui_rect(select_home_button), "返回主菜单", small_font, mouse_position, "secondary")
        elif state in (GameState.PLAYING, GameState.FLYING):
            draw_panel(screen, pygame.Rect(PAGE_MARGIN, 20, screen.get_width() - PAGE_MARGIN * 2, HEADER_HEIGHT - 20))
            level = LEVELS[level_index]
            draw_text(screen, "一箭又一箭", large_font, COLOR["title"], (145 + layout_offset, 58))
            draw_text(screen, f"关卡：{level['name']}", normal_font, COLOR["text"], (410 + layout_offset, 58))
            draw_text(screen, f"得分：{score}", small_font, COLOR["title"], (125 + layout_offset, 105))
            draw_text(screen, f"用时：{elapsed_time:.1f}s", small_font, COLOR["text"], (300 + layout_offset, 105))
            draw_text(screen, f"剩余箭头：{len(arrows)}", small_font, COLOR["text"], (480 + layout_offset, 105))
            draw_text(screen, f"失误：{remaining_mistakes}", small_font, COLOR["text"], (650 + layout_offset, 105))
            draw_text(screen, f"提示：{hints_remaining}", small_font, COLOR["text"], (770 + layout_offset, 105))
            hovered_arrow = arrow_at_position(arrows, mouse_position, screen.get_width()) if state == GameState.PLAYING and feedback_arrow is None else None
            draw_board(screen, arrows, feedback_arrow, hovered_arrow, hint_arrow)
            board_left = (screen.get_width() - BOARD_COLS * CELL_SIZE) // 2
            draw_text(screen, message, tiny_font, COLOR["muted_text"], (screen.get_width() // 2, 617))
            draw_panel(screen, pygame.Rect(board_left - 8, 626, BOARD_COLS * CELL_SIZE + 16, 58))
            draw_button(screen, ui_rect(restart_button), "重新开始", small_font, mouse_position, "secondary")
            draw_button(screen, ui_rect(hint_button), "提示", small_font, mouse_position, "secondary")
            draw_button(screen, ui_rect(menu_button), "返回主菜单", tiny_font, mouse_position, "secondary")
        elif state == GameState.WIN:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "第 %d 关完成" % (level_index + 1), title_font, COLOR["title"], (480, 240))
            draw_text(screen, f"本关得分：{score}", normal_font, COLOR["text"], (480, 310))
            draw_text(screen, f"完成用时：{elapsed_time:.1f}s", normal_font, COLOR["muted_text"], (480, 350))
            draw_text(screen, "★" * earned_stars + "☆" * (3 - earned_stars), large_font, COLOR["title"], (480, 395))
            draw_button(screen, next_button, "下一关", large_font, mouse_position)
            draw_button(screen, home_button, "返回主菜单", normal_font, mouse_position, "secondary")
        elif state == GameState.LOSE:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "挑战失败", title_font, (255, 190, 180), (480, 245))
            draw_text(screen, "失误次数已用完，请调整消除顺序", normal_font, COLOR["muted_text"], (480, 315))
            draw_button(screen, retry_button, "重新开始本关", normal_font, mouse_position, "danger")
            draw_button(screen, home_button, "返回主菜单", normal_font, mouse_position, "secondary")
        elif state == GameState.ALL_CLEAR:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "全部通关！", title_font, COLOR["title"], (480, 230))
            draw_text(screen, f"本关得分：{score}    用时：{elapsed_time:.1f}s", normal_font, COLOR["text"], (480, 305))
            draw_text(screen, "★" * earned_stars + "☆" * (3 - earned_stars), large_font, COLOR["title"], (480, 355))
            draw_text(screen, f"恭喜你完成全部 {len(LEVELS)} 个关卡", normal_font, COLOR["muted_text"], (480, 405))
            draw_button(screen, home_button, "返回主菜单", normal_font, mouse_position, "secondary")

        modal.draw(screen, large_font, small_font, small_font, mouse_position)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


# 从同级模块使用已拆分的规则、渲染与配置；上方旧定义保留为兼容参考，运行时
# 统一由这些模块提供实现，便于后续分别维护。
# 配置也以 config.py 为唯一来源，避免修改后出现两份不一致的数据。
from config import *  # noqa: F403
from config import DIRECTION_STEPS as _DIRECTION_STEPS
from game_logic import (create_level_arrows as _create_level_arrows,
                        calculate_stars as _calculate_stars,
                        find_available_arrow as _find_available_arrow,
                        is_blocked as _is_blocked)
from rendering import (arrow_at_position as _arrow_at_position,
                       draw_board as _draw_board, draw_button as _draw_button,
                       draw_panel as _draw_panel, draw_text as _draw_text,
                       get_font as _get_font, ModalDialog as _ModalDialog)

DIRECTION_STEPS = _DIRECTION_STEPS
is_blocked = _is_blocked
create_level_arrows = _create_level_arrows
calculate_stars = _calculate_stars
find_available_arrow = _find_available_arrow
get_font = _get_font
draw_text = _draw_text
draw_panel = _draw_panel
draw_button = _draw_button
draw_board = _draw_board
arrow_at_position = _arrow_at_position
ModalDialog = _ModalDialog


if __name__ == "__main__":
    run_game()
