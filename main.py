"""“一箭又一箭”Pygame 单文件小游戏。运行前：python3 -m pip install pygame"""

import copy
import math
import sys
from enum import Enum, auto

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


# 每关都有至少一个通关顺序，坐标从 (0, 0) 开始。
LEVELS = [
    {
        "name": "第 1 关", "max_mistakes": 3,
        "arrows": [
            {"row": 3, "col": 1, "direction": Direction.RIGHT},
            {"row": 3, "col": 5, "direction": Direction.RIGHT},
            {"row": 6, "col": 7, "direction": Direction.DOWN},
        ],
        # 通关顺序：(3, 5) → (3, 1) → (6, 7)
    },
    {
        "name": "第 2 关", "max_mistakes": 3,
        "arrows": [
            {"row": 1, "col": 3, "direction": Direction.DOWN},
            {"row": 6, "col": 3, "direction": Direction.DOWN},
            {"row": 4, "col": 7, "direction": Direction.RIGHT},
        ],
        # 通关顺序：(6, 3) → (1, 3) → (4, 7)
    },
    {
        "name": "第 3 关", "max_mistakes": 4,
        "arrows": [
            {"row": 0, "col": 4, "direction": Direction.UP},
            {"row": 2, "col": 4, "direction": Direction.UP},
            {"row": 5, "col": 1, "direction": Direction.LEFT},
            {"row": 5, "col": 5, "direction": Direction.LEFT},
            {"row": 6, "col": 7, "direction": Direction.DOWN},
        ],
        # 通关顺序：(0, 4) → (2, 4) → (5, 1) → (5, 5) → (6, 7)
    },
]


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


def get_font(size):
    for name in ("PingFang SC", "Microsoft YaHei", "SimHei"):
        font = pygame.font.SysFont(name, size)
        if font:
            return font
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


def draw_board(screen, arrows, feedback_arrow=None, hovered_arrow=None):
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
            color = COLOR["danger"] if arrow is feedback_arrow else COLOR["arrow"]
            draw_arrow(screen, arrow, color, arrow is hovered_arrow)


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
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    title_font, large_font = get_font(54), get_font(30)
    normal_font, small_font = get_font(24), get_font(20)

    state, level_index = GameState.START, 0
    arrows = create_level_arrows(level_index)
    remaining_mistakes = LEVELS[level_index]["max_mistakes"]
    flying_arrow = feedback_arrow = None
    feedback_elapsed, lose_after_feedback = 0.0, False
    message = ""

    start_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 410, BUTTON_WIDTH, BUTTON_HEIGHT)
    restart_button = pygame.Rect(WINDOW_WIDTH - PAGE_MARGIN - 155, 75, 155, 46)
    next_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)
    home_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 505, BUTTON_WIDTH, BUTTON_HEIGHT)
    retry_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)

    def load_level(new_index):
        """唯一的关卡重置入口，保证切关和重开不残留任何动画状态。"""
        nonlocal level_index, arrows, remaining_mistakes, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, message
        level_index = new_index
        arrows = create_level_arrows(level_index)
        remaining_mistakes = LEVELS[level_index]["max_mistakes"]
        flying_arrow = feedback_arrow = None
        feedback_elapsed, lose_after_feedback = 0.0, False
        message = "点击没有阻挡的箭头，让它飞出棋盘"

    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0
        mouse_position = pygame.mouse.get_pos()

        # 飞行动画期间 state 为 FLYING，所有点击均不会处理。
        if state == GameState.FLYING and flying_arrow is not None:
            row_step, col_step = DIRECTION_STEPS[flying_arrow["direction"]]
            flying_arrow["offset_x"] += col_step * FLY_SPEED * delta_time
            flying_arrow["offset_y"] += row_step * FLY_SPEED * delta_time
            center_x = BOARD_LEFT + (flying_arrow["col"] + 0.5) * CELL_SIZE + flying_arrow["offset_x"]
            center_y = BOARD_TOP + (flying_arrow["row"] + 0.5) * CELL_SIZE + flying_arrow["offset_y"]
            outside = (center_x < BOARD_LEFT - CELL_SIZE or center_x > BOARD_LEFT + BOARD_COLS * CELL_SIZE + CELL_SIZE or center_y < BOARD_TOP - CELL_SIZE or center_y > BOARD_TOP + BOARD_ROWS * CELL_SIZE + CELL_SIZE)
            if outside:
                # 身份和成员检查确保同一箭头绝不会被重复删除。
                if flying_arrow in arrows:
                    arrows.remove(flying_arrow)
                flying_arrow = None
                if not arrows:
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
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == GameState.START and start_button.collidepoint(event.pos):
                    load_level(0)
                    state = GameState.PLAYING
                elif state == GameState.PLAYING and restart_button.collidepoint(event.pos):
                    load_level(level_index)
                # 碰撞反馈仍未结束时锁定箭头输入；空白处点击安全忽略。
                elif state == GameState.PLAYING and feedback_arrow is None:
                    clicked_arrow = arrow_at_position(arrows, event.pos)
                    if clicked_arrow is not None:
                        if is_blocked(clicked_arrow, arrows, BOARD_ROWS, BOARD_COLS):
                            remaining_mistakes -= 1
                            feedback_arrow, feedback_elapsed = clicked_arrow, 0.0
                            lose_after_feedback = remaining_mistakes <= 0
                            message = "路径被阻挡，失误 -1"
                        else:
                            flying_arrow = clicked_arrow
                            state, message = GameState.FLYING, "成功飞出！"
                elif state == GameState.WIN and next_button.collidepoint(event.pos):
                    load_level(level_index + 1)
                    state = GameState.PLAYING
                elif state == GameState.LOSE:
                    if retry_button.collidepoint(event.pos):
                        load_level(level_index)
                        state = GameState.PLAYING
                    elif home_button.collidepoint(event.pos):
                        state = GameState.START
                elif state == GameState.ALL_CLEAR and home_button.collidepoint(event.pos):
                    state = GameState.START

        screen.fill(COLOR["background"])
        if state == GameState.START:
            draw_panel(screen, pygame.Rect(205, 180, 550, 330))
            draw_text(screen, "一箭又一箭", title_font, COLOR["title"], (480, 255))
            draw_text(screen, "用正确顺序让所有箭头飞出棋盘", normal_font, COLOR["muted_text"], (480, 320))
            draw_button(screen, start_button, "开始游戏", large_font, mouse_position)
        elif state in (GameState.PLAYING, GameState.FLYING):
            draw_panel(screen, pygame.Rect(PAGE_MARGIN, 20, WINDOW_WIDTH - PAGE_MARGIN * 2, HEADER_HEIGHT - 20))
            level = LEVELS[level_index]
            draw_text(screen, "一箭又一箭", large_font, COLOR["title"], (145, 58))
            draw_text(screen, f"关卡：{level['name']}", normal_font, COLOR["text"], (190, 104))
            draw_text(screen, f"剩余箭头：{len(arrows)}", normal_font, COLOR["text"], (455, 104))
            draw_text(screen, f"剩余失误：{remaining_mistakes}", normal_font, COLOR["text"], (650, 104))
            draw_button(screen, restart_button, "重新开始", small_font, mouse_position, "secondary")
            hovered_arrow = arrow_at_position(arrows, mouse_position) if state == GameState.PLAYING and feedback_arrow is None else None
            draw_board(screen, arrows, feedback_arrow, hovered_arrow)
            draw_panel(screen, pygame.Rect(214, 620, 532, 52))
            draw_text(screen, message, small_font, COLOR["muted_text"], (480, 646))
        elif state == GameState.WIN:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "第 %d 关完成" % (level_index + 1), title_font, COLOR["title"], (480, 260))
            draw_text(screen, "所有箭头已成功飞出棋盘", normal_font, COLOR["muted_text"], (480, 330))
            draw_button(screen, next_button, "下一关", large_font, mouse_position)
        elif state == GameState.LOSE:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "挑战失败", title_font, (255, 190, 180), (480, 245))
            draw_text(screen, "失误次数已用完，请调整消除顺序", normal_font, COLOR["muted_text"], (480, 315))
            draw_button(screen, retry_button, "重新开始本关", normal_font, mouse_position, "danger")
            draw_button(screen, home_button, "返回开始界面", normal_font, mouse_position, "secondary")
        elif state == GameState.ALL_CLEAR:
            draw_panel(screen, pygame.Rect(205, 180, 550, 400))
            draw_text(screen, "全部通关！", title_font, COLOR["title"], (480, 255))
            draw_text(screen, "恭喜你完成全部三个关卡", normal_font, COLOR["muted_text"], (480, 325))
            draw_button(screen, home_button, "返回开始界面", normal_font, mouse_position, "secondary")

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_game()
