"""“一箭又一箭”小游戏。运行前：python3 -m pip install pygame"""

import math
import sys
from enum import Enum, auto

import pygame


WINDOW_WIDTH, WINDOW_HEIGHT = 960, 700
CELL_SIZE = 64
BOARD_ROWS, BOARD_COLS = 7, 8
BOARD_LEFT, BOARD_TOP = 224, 160
FLY_SPEED = 720                 # 像素/秒
FEEDBACK_TIME = 0.30            # 被阻挡后的红色晃动时间（秒）


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GameState(Enum):
    """START/PLAYING/FLYING/WIN/LOSE/ALL_CLEAR 是游戏唯一的主状态。"""

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


# row、col 均从 0 开始。每关均有至少一种实际通关顺序。
LEVELS = [
    {
        "name": "第 1 关", "max_mistakes": 3,
        "arrows": [
            {"row": 3, "col": 1, "direction": Direction.RIGHT},
            {"row": 3, "col": 5, "direction": Direction.RIGHT},
            {"row": 6, "col": 7, "direction": Direction.DOWN},
        ],
        # 正确顺序：(3, 5) RIGHT -> (3, 1) RIGHT -> (6, 7) DOWN
    },
    {
        "name": "第 2 关", "max_mistakes": 3,
        "arrows": [
            {"row": 1, "col": 3, "direction": Direction.DOWN},
            {"row": 6, "col": 3, "direction": Direction.DOWN},
            {"row": 4, "col": 7, "direction": Direction.RIGHT},
        ],
        # 正确顺序：(6, 3) DOWN -> (1, 3) DOWN -> (4, 7) RIGHT
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
        # 正确顺序：(0, 4) UP -> (2, 4) UP -> (5, 1) LEFT ->
        #           (5, 5) LEFT -> (6, 7) DOWN
    },
]


def is_blocked(arrow, arrows, rows, cols):
    """扫描箭头前方至边界；已消除箭头不参与阻挡，也不会越界。"""
    row_step, col_step = DIRECTION_STEPS[arrow["direction"]]
    active_positions = {
        (item["row"], item["col"])
        for item in arrows if not item.get("eliminated", False)
    }
    check_row = arrow["row"] + row_step
    check_col = arrow["col"] + col_step
    while 0 <= check_row < rows and 0 <= check_col < cols:
        if (check_row, check_col) in active_positions:
            return True
        check_row += row_step
        check_col += col_step
    return False


def create_level_arrows(level_index):
    """创建可变的运行时箭头，不修改 LEVELS 中的原始布局。"""
    return [
        {**arrow, "eliminated": False, "offset_x": 0.0, "offset_y": 0.0}
        for arrow in LEVELS[level_index]["arrows"]
    ]


def get_chinese_font(size):
    for font_name in ("PingFang SC", "Microsoft YaHei", "SimHei"):
        font = pygame.font.SysFont(font_name, size)
        if font:
            return font
    return pygame.font.Font(None, size)


def draw_text(screen, text, font, color, center):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=center))


def draw_button(screen, rect, text, font, mouse_position, color=(47, 126, 75)):
    button_color = tuple(min(255, value + 18) for value in color) if rect.collidepoint(mouse_position) else color
    pygame.draw.rect(screen, button_color, rect, border_radius=12)
    pygame.draw.rect(screen, (225, 245, 230), rect, width=2, border_radius=12)
    draw_text(screen, text, font, (255, 255, 255), rect.center)


def draw_arrow(screen, arrow, color=(235, 130, 45)):
    """按箭头偏移量绘制，飞行和晃动动画都复用这一函数。"""
    center_x = BOARD_LEFT + arrow["col"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_x"]
    center_y = BOARD_TOP + arrow["row"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_y"]
    base_points = [(0, -22), (15, 0), (7, 0), (7, 22), (-7, 22), (-7, 0), (-15, 0)]
    points = []
    for point_x, point_y in base_points:
        if arrow["direction"] == Direction.DOWN:
            point_x, point_y = -point_x, -point_y
        elif arrow["direction"] == Direction.LEFT:
            point_x, point_y = point_y, -point_x
        elif arrow["direction"] == Direction.RIGHT:
            point_x, point_y = -point_y, point_x
        points.append((center_x + point_x, center_y + point_y))
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, (112, 61, 23), points, width=2)


def draw_board(screen, arrows, feedback_arrow=None):
    board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_COLS * CELL_SIZE, BOARD_ROWS * CELL_SIZE)
    pygame.draw.rect(screen, (247, 240, 218), board_rect, border_radius=8)
    for row in range(BOARD_ROWS + 1):
        y = BOARD_TOP + row * CELL_SIZE
        pygame.draw.line(screen, (183, 166, 128), (BOARD_LEFT, y), (BOARD_LEFT + BOARD_COLS * CELL_SIZE, y), 2)
    for col in range(BOARD_COLS + 1):
        x = BOARD_LEFT + col * CELL_SIZE
        pygame.draw.line(screen, (183, 166, 128), (x, BOARD_TOP), (x, BOARD_TOP + BOARD_ROWS * CELL_SIZE), 2)
    for arrow in arrows:
        if not arrow["eliminated"]:
            draw_arrow(screen, arrow, (220, 64, 58) if arrow is feedback_arrow else (235, 130, 45))


def arrow_at_position(arrows, mouse_position):
    """返回点击到的未消除箭头；网格外或空格子均返回 None。"""
    mouse_x, mouse_y = mouse_position
    col = (mouse_x - BOARD_LEFT) // CELL_SIZE
    row = (mouse_y - BOARD_TOP) // CELL_SIZE
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return None
    return next((a for a in arrows if not a["eliminated"] and a["row"] == row and a["col"] == col), None)


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    title_font, large_font = get_chinese_font(54), get_chinese_font(30)
    normal_font, small_font = get_chinese_font(24), get_chinese_font(20)

    state = GameState.START
    level_index = 0
    arrows = create_level_arrows(level_index)
    remaining_mistakes = LEVELS[level_index]["max_mistakes"]
    flying_arrow = None
    feedback_arrow = None
    feedback_elapsed = 0.0
    lose_after_feedback = False
    message = ""

    start_button = pygame.Rect(375, 410, 210, 62)
    restart_button = pygame.Rect(700, 75, 155, 48)
    next_button = pygame.Rect(375, 430, 210, 58)
    home_button = pygame.Rect(375, 505, 210, 58)
    retry_button = pygame.Rect(375, 430, 210, 58)

    def load_level(new_index):
        """进入或重开关卡时，彻底恢复箭头和失误数。"""
        nonlocal level_index, arrows, remaining_mistakes, flying_arrow, feedback_arrow, feedback_elapsed, lose_after_feedback, message
        level_index = new_index
        arrows = create_level_arrows(level_index)
        remaining_mistakes = LEVELS[level_index]["max_mistakes"]
        flying_arrow = feedback_arrow = None
        feedback_elapsed = 0.0
        lose_after_feedback = False
        message = "点击没有阻挡的箭头，让它飞出棋盘"

    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0
        mouse_position = pygame.mouse.get_pos()

        # FLYING：箭头沿自己的方向移动，完全离开棋盘后才从列表删除。
        if state == GameState.FLYING:
            row_step, col_step = DIRECTION_STEPS[flying_arrow["direction"]]
            flying_arrow["offset_x"] += col_step * FLY_SPEED * delta_time
            flying_arrow["offset_y"] += row_step * FLY_SPEED * delta_time
            center_x = BOARD_LEFT + flying_arrow["col"] * CELL_SIZE + CELL_SIZE / 2 + flying_arrow["offset_x"]
            center_y = BOARD_TOP + flying_arrow["row"] * CELL_SIZE + CELL_SIZE / 2 + flying_arrow["offset_y"]
            outside = center_x < BOARD_LEFT - CELL_SIZE or center_x > BOARD_LEFT + BOARD_COLS * CELL_SIZE + CELL_SIZE or center_y < BOARD_TOP - CELL_SIZE or center_y > BOARD_TOP + BOARD_ROWS * CELL_SIZE + CELL_SIZE
            if outside:
                arrows.remove(flying_arrow)
                flying_arrow = None
                if not arrows and level_index == len(LEVELS) - 1:
                    state = GameState.ALL_CLEAR
                elif not arrows:
                    state = GameState.WIN
                else:
                    state = GameState.PLAYING
                message = "箭头成功飞出棋盘！"

        # 被阻挡反馈持续 0.3 秒；期间同样锁定点击，避免状态混乱。
        if feedback_arrow is not None:
            feedback_elapsed += delta_time
            row_step, col_step = DIRECTION_STEPS[feedback_arrow["direction"]]
            shake = math.sin(feedback_elapsed * 50) * 8
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
                elif state == GameState.PLAYING and feedback_arrow is None:
                    clicked_arrow = arrow_at_position(arrows, event.pos)
                    if clicked_arrow:
                        if is_blocked(clicked_arrow, arrows, BOARD_ROWS, BOARD_COLS):
                            remaining_mistakes -= 1
                            feedback_arrow = clicked_arrow
                            feedback_elapsed = 0.0
                            lose_after_feedback = remaining_mistakes == 0
                            message = "前方有箭头阻挡！"
                        else:
                            flying_arrow = clicked_arrow
                            state = GameState.FLYING
                            message = "箭头正在飞出……"
                elif state == GameState.WIN and next_button.collidepoint(event.pos):
                    if level_index + 1 < len(LEVELS):
                        load_level(level_index + 1)
                        state = GameState.PLAYING
                    else:
                        state = GameState.ALL_CLEAR
                elif state == GameState.LOSE:
                    if retry_button.collidepoint(event.pos):
                        load_level(level_index)
                        state = GameState.PLAYING
                    elif home_button.collidepoint(event.pos):
                        state = GameState.START
                elif state == GameState.ALL_CLEAR and home_button.collidepoint(event.pos):
                    state = GameState.START

        screen.fill((40, 70, 91))
        if state == GameState.START:
            draw_text(screen, "一箭又一箭", title_font, (255, 239, 192), (480, 245))
            draw_text(screen, "用正确顺序让所有箭头飞出棋盘", normal_font, (220, 233, 240), (480, 315))
            draw_button(screen, start_button, "开始游戏", large_font, mouse_position)
        elif state in (GameState.PLAYING, GameState.FLYING):
            level = LEVELS[level_index]
            draw_text(screen, "一箭又一箭", large_font, (255, 239, 192), (145, 58))
            draw_text(screen, f"当前关卡：{level['name']}", normal_font, (255, 255, 255), (185, 112))
            draw_text(screen, f"剩余箭头：{len(arrows)}", normal_font, (255, 255, 255), (420, 112))
            draw_text(screen, f"剩余失误：{remaining_mistakes}", normal_font, (255, 255, 255), (625, 112))
            draw_button(screen, restart_button, "重新开始", small_font, mouse_position)
            draw_board(screen, arrows, feedback_arrow)
            draw_text(screen, message, small_font, (202, 218, 228), (480, 645))
        elif state == GameState.WIN:
            draw_text(screen, "本关通关！", title_font, (255, 239, 192), (480, 260))
            draw_text(screen, f"已完成 {LEVELS[level_index]['name']}", normal_font, (220, 233, 240), (480, 330))
            draw_button(screen, next_button, "下一关", large_font, mouse_position)
        elif state == GameState.LOSE:
            draw_text(screen, "挑战失败", title_font, (255, 190, 180), (480, 245))
            draw_text(screen, "失误次数已用完", normal_font, (220, 233, 240), (480, 315))
            draw_button(screen, retry_button, "重新开始本关", normal_font, mouse_position)
            draw_button(screen, home_button, "返回开始界面", normal_font, mouse_position, (83, 104, 130))
        elif state == GameState.ALL_CLEAR:
            draw_text(screen, "全部通关！", title_font, (255, 239, 192), (480, 255))
            draw_text(screen, "恭喜你完成了所有关卡", normal_font, (220, 233, 240), (480, 325))
            draw_button(screen, home_button, "返回开始界面", normal_font, mouse_position, (83, 104, 130))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_game()
