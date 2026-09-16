# -*- coding: utf-8 -*-
"""“一箭又一箭”Pygame 游戏运行循环。"""

import math
import sys

import pygame

from audio import SoundManager
from config import *  # noqa: F403
from game_logic import (SearchLimitExceeded, calculate_stars, create_level_arrows,
                        find_available_arrow, is_blocked, solve_level)
from rendering import (ModalDialog, arrow_at_position, draw_board, draw_button,
                       draw_panel, draw_text, get_font)


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("一箭又一箭")
    clock = pygame.time.Clock()
    sound_manager = SoundManager()
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
    auto_solution = []
    auto_playing = False
    result_elapsed = 0.0
    result_state = None
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
    restart_button = pygame.Rect(BOARD_LEFT + 8, 634, 118, 40)
    hint_button = pygame.Rect(BOARD_LEFT + 134, 634, 118, 40)
    menu_button = pygame.Rect(BOARD_LEFT + 260, 634, 118, 40)
    auto_solve_button = pygame.Rect(BOARD_LEFT + 386, 634, 118, 40)
    next_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)
    home_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 505, BUTTON_WIDTH, BUTTON_HEIGHT)
    retry_button = pygame.Rect((WINDOW_WIDTH - BUTTON_WIDTH) // 2, 430, BUTTON_WIDTH, BUTTON_HEIGHT)
    sound_button = pygame.Rect(WINDOW_WIDTH - 118, 82, 86, 32)
    def load_level(new_index):
        """唯一的关卡重置入口，保证切关和重开不残留任何动画状态。"""
        nonlocal level_index, arrows, remaining_mistakes, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, hints_remaining, hint_arrow, hint_elapsed, message
        nonlocal score, elapsed_time, earned_stars, auto_solution, auto_playing
        level_index = new_index
        arrows = create_level_arrows(level_index)
        remaining_mistakes = LEVELS[level_index]["max_mistakes"]
        score, elapsed_time, earned_stars = 0, 0.0, 0
        flying_arrow = feedback_arrow = None
        feedback_elapsed, lose_after_feedback = 0.0, False
        hints_remaining = MAX_HINTS_PER_LEVEL
        hint_arrow, hint_elapsed = None, 0.0
        auto_solution, auto_playing = [], False
        message = "点击没有阻挡的箭头，让它飞出棋盘"

    def abandon_current_round():
        """返回菜单时仅清理本局临时数据，不影响解锁和最高星级。"""
        nonlocal arrows, remaining_mistakes, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, hints_remaining, hint_arrow, hint_elapsed
        nonlocal score, elapsed_time, earned_stars, message, state, auto_solution, auto_playing
        arrows = []
        remaining_mistakes = 0
        flying_arrow = feedback_arrow = hint_arrow = None
        feedback_elapsed, hint_elapsed, lose_after_feedback = 0.0, 0.0, False
        hints_remaining, score, elapsed_time, earned_stars = 0, 0, 0.0, 0
        auto_solution, auto_playing = [], False
        message = ""
        state = GameState.START

    def start_next_auto_arrow():
        """按已验证的解法取下一支真实箭头，仍复用原有飞出动画。"""
        nonlocal flying_arrow, state, message, auto_solution, auto_playing
        if not auto_solution:
            auto_playing = False
            return
        row, col, direction = auto_solution.pop(0)
        flying_arrow = next(
            (arrow for arrow in arrows
             if arrow["row"] == row and arrow["col"] == col
             and arrow["direction"].value == direction),
            None,
        )
        if flying_arrow is None:
            # 理论上不会发生：玩家在演示期间已被锁定。保留防御性分支，
            # 防止外部修改关卡数据后出现无提示的卡死。
            auto_solution, auto_playing = [], False
            state = GameState.PLAYING
            message = "自动演示已停止：箭头状态发生变化"
            return
        state = GameState.FLYING
        message = "自动演示中…"

    def update(dt):
        """集中更新全部基于 delta time 的动画与计时状态。"""
        nonlocal elapsed_time, hint_arrow, hint_elapsed, flying_arrow, feedback_arrow
        nonlocal feedback_elapsed, lose_after_feedback, score, earned_stars
        nonlocal highest_unlocked_index, state, message, result_elapsed, result_state

        if state == GameState.PLAYING and feedback_arrow is None and not modal.is_open:
            elapsed_time += dt

        if hint_arrow is not None and not modal.is_open:
            hint_elapsed += dt
            if hint_elapsed >= HINT_TIME:
                hint_arrow, hint_elapsed = None, 0.0

        if state == GameState.FLYING and flying_arrow is not None:
            row_step, col_step = DIRECTION_STEPS[flying_arrow["direction"]]
            flying_arrow["offset_x"] += col_step * FLY_SPEED * dt
            flying_arrow["offset_y"] += row_step * FLY_SPEED * dt
            board_left = (screen.get_width() - BOARD_COLS * CELL_SIZE) // 2
            center_x = board_left + (flying_arrow["col"] + 0.5) * CELL_SIZE + flying_arrow["offset_x"]
            center_y = BOARD_TOP + (flying_arrow["row"] + 0.5) * CELL_SIZE + flying_arrow["offset_y"]
            outside = (center_x < board_left - CELL_SIZE or center_x > board_left + BOARD_COLS * CELL_SIZE + CELL_SIZE
                       or center_y < BOARD_TOP - CELL_SIZE or center_y > BOARD_TOP + BOARD_ROWS * CELL_SIZE + CELL_SIZE)
            if outside:
                if flying_arrow in arrows:
                    arrows.remove(flying_arrow)
                    score += SCORE_PER_ARROW
                    sound_manager.play("fly")
                flying_arrow = None
                hint_arrow, hint_elapsed = None, 0.0
                if not arrows:
                    earned_stars = calculate_stars(score, elapsed_time, len(LEVELS[level_index]["arrows"]), SCORE_PER_ARROW)
                    best_stars[level_index] = max(best_stars[level_index], earned_stars)
                    highest_unlocked_index = max(highest_unlocked_index, min(level_index + 1, len(LEVELS) - 1))
                    state = GameState.ALL_CLEAR if level_index == len(LEVELS) - 1 else GameState.WIN
                    sound_manager.play("win")
                else:
                    state = GameState.PLAYING
                    if auto_playing:
                        start_next_auto_arrow()
                    else:
                        message = "成功飞出！"

        if feedback_arrow is not None:
            feedback_elapsed += dt
            row_step, col_step = DIRECTION_STEPS[feedback_arrow["direction"]]
            # 正弦晃动与 dt 累积时间绑定，帧率变化时总时长和振幅仍保持一致。
            shake = math.sin(feedback_elapsed * 48) * 8
            feedback_arrow["offset_x"] = shake if col_step else 0.0
            feedback_arrow["offset_y"] = shake if row_step else 0.0
            if feedback_elapsed >= FEEDBACK_TIME:
                feedback_arrow["offset_x"] = feedback_arrow["offset_y"] = 0.0
                feedback_arrow = None
                if lose_after_feedback:
                    state = GameState.LOSE
                    sound_manager.play("lose")
                lose_after_feedback = False

        if state in (GameState.WIN, GameState.LOSE, GameState.ALL_CLEAR):
            if result_state != state:
                result_state, result_elapsed = state, 0.0
            else:
                result_elapsed = min(result_elapsed + dt, 0.35)
        else:
            result_state, result_elapsed = None, 0.0

    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0
        mouse_position = pygame.mouse.get_pos()
        layout_offset = (screen.get_width() - WINDOW_WIDTH) // 2

        def ui_rect(rect):
            return rect.move(layout_offset, 0)

        update(delta_time)

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
                if state == GameState.PLAYING and ui_rect(sound_button).collidepoint(event.pos):
                    if sound_manager.toggle():
                        sound_manager.play("button")
                elif state == GameState.START and ui_rect(start_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    load_level(0)
                    state = GameState.PLAYING
                elif state == GameState.START and ui_rect(level_select_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    state = GameState.LEVEL_SELECT
                elif state == GameState.START and ui_rect(quit_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    modal.open("quit")
                elif state == GameState.LEVEL_SELECT:
                    if ui_rect(select_home_button).collidepoint(event.pos):
                        sound_manager.play("button")
                        state = GameState.START
                    else:
                        for selected_index, button in enumerate(level_buttons):
                            if (selected_index <= highest_unlocked_index
                                    and ui_rect(button).collidepoint(event.pos)):
                                sound_manager.play("button")
                                load_level(selected_index)
                                state = GameState.PLAYING
                                break
                elif state == GameState.PLAYING and ui_rect(restart_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    load_level(level_index)
                elif state == GameState.PLAYING and ui_rect(hint_button).collidepoint(event.pos):
                    sound_manager.play("button")
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
                        sound_manager.play("button")
                        modal.open("return_menu")
                elif state == GameState.PLAYING and ui_rect(auto_solve_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    # 求解器仅对深拷贝工作集写入 eliminated；真实 arrows 在拿到
                    # 完整方案之前绝不变动，找到后才进入 FLYING 锁定所有玩法输入。
                    if len(arrows) > AUTO_SOLVE_MAX_ARROWS:
                        message = f"箭头数超过自动求解上限（{AUTO_SOLVE_MAX_ARROWS}）"
                    else:
                        try:
                            solution = solve_level(
                                arrows, BOARD_ROWS, BOARD_COLS, AUTO_SOLVE_MAX_NODES,
                            )
                        except SearchLimitExceeded:
                            message = "当前关卡未找到解法（搜索达到上限）"
                        else:
                            if solution is None:
                                message = "当前关卡未找到解法"
                            else:
                                auto_solution, auto_playing = list(solution), True
                                hint_arrow, hint_elapsed = None, 0.0
                                start_next_auto_arrow()
                # 碰撞反馈仍未结束时锁定箭头输入；空白处点击安全忽略。
                elif state == GameState.PLAYING and feedback_arrow is None:
                    clicked_arrow = arrow_at_position(arrows, event.pos, screen.get_width())
                    if clicked_arrow is not None:
                        hint_arrow, hint_elapsed = None, 0.0
                        if is_blocked(clicked_arrow, arrows, BOARD_ROWS, BOARD_COLS):
                            sound_manager.play("blocked")
                            remaining_mistakes -= 1
                            score = max(0, score - BLOCKED_ARROW_PENALTY)
                            feedback_arrow, feedback_elapsed = clicked_arrow, 0.0
                            lose_after_feedback = remaining_mistakes <= 0
                            message = "路径被阻挡，失误 -1"
                        else:
                            flying_arrow = clicked_arrow
                            state, message = GameState.FLYING, "成功飞出！"
                elif state == GameState.WIN:
                    if ui_rect(next_button).collidepoint(event.pos):
                        sound_manager.play("button")
                        load_level(level_index + 1)
                        state = GameState.PLAYING
                    elif ui_rect(home_button).collidepoint(event.pos):
                        sound_manager.play("button")
                        abandon_current_round()
                elif state == GameState.LOSE:
                    if ui_rect(retry_button).collidepoint(event.pos):
                        sound_manager.play("button")
                        load_level(level_index)
                        state = GameState.PLAYING
                    elif ui_rect(home_button).collidepoint(event.pos):
                        sound_manager.play("button")
                        abandon_current_round()
                elif state == GameState.ALL_CLEAR and ui_rect(home_button).collidepoint(event.pos):
                    sound_manager.play("button")
                    abandon_current_round()

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
            sound_label = "音效：开" if sound_manager.enabled and sound_manager.available else "音效：关"
            draw_button(screen, ui_rect(sound_button), sound_label, tiny_font, mouse_position, "secondary", state == GameState.PLAYING)
            hovered_arrow = arrow_at_position(arrows, mouse_position, screen.get_width()) if state == GameState.PLAYING and feedback_arrow is None else None
            draw_board(screen, arrows, feedback_arrow, hovered_arrow, hint_arrow)
            board_left = (screen.get_width() - BOARD_COLS * CELL_SIZE) // 2
            draw_text(screen, message, tiny_font, COLOR["muted_text"], (screen.get_width() // 2, 617))
            draw_panel(screen, pygame.Rect(board_left - 8, 626, BOARD_COLS * CELL_SIZE + 16, 58))
            # 四个底部按钮均使用较窄宽度，保证窗口默认尺寸下不重叠。
            controls_enabled = state == GameState.PLAYING
            draw_button(screen, ui_rect(restart_button), "重新开始", small_font, mouse_position, "secondary", controls_enabled)
            draw_button(screen, ui_rect(hint_button), "提示", small_font, mouse_position, "secondary", controls_enabled)
            draw_button(screen, ui_rect(menu_button), "返回主菜单", tiny_font, mouse_position, "secondary", controls_enabled)
            draw_button(screen, ui_rect(auto_solve_button), "自动求解", tiny_font, mouse_position, "accent", controls_enabled)
        elif state == GameState.WIN:
            draw_panel(screen, ui_rect(pygame.Rect(205, 180, 550, 400)))
            draw_text(screen, "第 %d 关完成" % (level_index + 1), title_font, COLOR["title"], (480 + layout_offset, 240))
            draw_text(screen, f"本关得分：{score}", normal_font, COLOR["text"], (480 + layout_offset, 310))
            draw_text(screen, f"完成用时：{elapsed_time:.1f}s", normal_font, COLOR["muted_text"], (480 + layout_offset, 350))
            draw_text(screen, "★" * earned_stars + "☆" * (3 - earned_stars), large_font, COLOR["title"], (480 + layout_offset, 395))
            draw_button(screen, ui_rect(next_button), "下一关", large_font, mouse_position)
            draw_button(screen, ui_rect(home_button), "返回主菜单", normal_font, mouse_position, "secondary")
        elif state == GameState.LOSE:
            draw_panel(screen, ui_rect(pygame.Rect(205, 180, 550, 400)))
            draw_text(screen, "挑战失败", title_font, (255, 190, 180), (480 + layout_offset, 245))
            draw_text(screen, "失误次数已用完，请调整消除顺序", normal_font, COLOR["muted_text"], (480 + layout_offset, 315))
            draw_button(screen, ui_rect(retry_button), "重新开始本关", normal_font, mouse_position, "danger")
            draw_button(screen, ui_rect(home_button), "返回主菜单", normal_font, mouse_position, "secondary")
        elif state == GameState.ALL_CLEAR:
            draw_panel(screen, ui_rect(pygame.Rect(205, 180, 550, 400)))
            draw_text(screen, "全部通关！", title_font, COLOR["title"], (480 + layout_offset, 230))
            draw_text(screen, f"本关得分：{score}    用时：{elapsed_time:.1f}s", normal_font, COLOR["text"], (480 + layout_offset, 305))
            draw_text(screen, "★" * earned_stars + "☆" * (3 - earned_stars), large_font, COLOR["title"], (480 + layout_offset, 355))
            draw_text(screen, f"恭喜你完成全部 {len(LEVELS)} 个关卡", normal_font, COLOR["muted_text"], (480 + layout_offset, 405))
            draw_button(screen, ui_rect(home_button), "返回主菜单", normal_font, mouse_position, "secondary")

        # 结算页从黑色遮罩中平滑淡入；不改变任何结算规则或按钮行为。
        if result_state is not None:
            fade_progress = min(1.0, result_elapsed / 0.35)
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, round(210 * (1.0 - fade_progress))))
            screen.blit(overlay, (0, 0))

        modal.draw(screen, large_font, small_font, small_font, mouse_position)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_game()
