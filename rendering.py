# -*- coding: utf-8 -*-
"""Pygame 字体与界面绘制函数。"""

from pathlib import Path

import pygame

from config import (BOARD_COLS, BOARD_LEFT, BOARD_ROWS, BOARD_TOP, CELL_SIZE,
                    BUTTON_RADIUS, CHINESE_FONT_PATHS, COLOR, DIRECTION_STEPS,
                    PANEL_RADIUS, UI_SHADOW_OFFSET)


def get_font(size):
    for font_path in CHINESE_FONT_PATHS:
        if Path(font_path).is_file():
            try:
                return pygame.font.Font(font_path, size)
            except pygame.error:
                continue
    for font_name in ("PingFang SC", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        font_path = pygame.font.match_font(font_name)
        if font_path:
            return pygame.font.Font(font_path, size)
    return pygame.font.Font(None, size)


def draw_text(screen, text, font, color, center):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=center))


def get_board_left(screen_width):
    """棋盘随窗口横向居中；默认尺寸时与原坐标完全一致。"""
    return (screen_width - BOARD_COLS * CELL_SIZE) // 2


def draw_panel(screen, rect):
    shadow_rect = rect.move(0, UI_SHADOW_OFFSET)
    pygame.draw.rect(screen, COLOR["shadow"], shadow_rect, border_radius=PANEL_RADIUS)
    pygame.draw.rect(screen, COLOR["panel"], rect, border_radius=PANEL_RADIUS)
    pygame.draw.rect(screen, COLOR["panel_border"], rect, width=2, border_radius=PANEL_RADIUS)


class UIButton:
    """统一按钮状态与绘制；事件层只需使用 rect.collidepoint()。"""

    def __init__(self, rect, text, style="accent", enabled=True):
        self.rect, self.text, self.style, self.enabled = rect, text, style, enabled

    def draw(self, screen, font, mouse_position):
        hovered = self.enabled and self.rect.collidepoint(mouse_position)
        pressed = hovered and pygame.mouse.get_pressed(3)[0]
        if not self.enabled:
            fill, text_color = COLOR["disabled"], COLOR["disabled_text"]
        elif self.style == "danger":
            fill = COLOR["danger_pressed"] if pressed else COLOR["danger_hover"] if hovered else COLOR["danger"]
            text_color = COLOR["text"]
        elif self.style == "secondary":
            fill = COLOR["secondary_pressed"] if pressed else COLOR["secondary_hover"] if hovered else COLOR["secondary"]
            text_color = COLOR["text"]
        elif self.style == "current_level":
            fill = COLOR["current_level_hover"] if hovered else COLOR["current_level"]
            text_color = COLOR["text"]
        else:
            fill = COLOR["accent_pressed"] if pressed else COLOR["accent_hover"] if hovered else COLOR["accent"]
            text_color = COLOR["text"]
        pygame.draw.rect(screen, COLOR["shadow"], self.rect.move(0, 3), border_radius=BUTTON_RADIUS)
        pygame.draw.rect(screen, fill, self.rect, border_radius=BUTTON_RADIUS)
        pygame.draw.rect(screen, (232, 245, 236), self.rect, width=2, border_radius=BUTTON_RADIUS)
        draw_text(screen, self.text, font, text_color, self.rect.center)


def draw_button(screen, rect, text, font, mouse_position, color_name="accent", enabled=True):
    """兼容旧调用的按钮包装器，同时提供悬停、按下和禁用状态。"""
    UIButton(rect, text, color_name, enabled and color_name != "locked").draw(screen, font, mouse_position)


class ModalDialog:
    """统一确认弹窗：覆盖背景、拦截输入，并返回 confirm/cancel 决策。"""

    def __init__(self):
        self.action = None

    @property
    def is_open(self):
        return self.action is not None

    def open(self, action):
        self.action = action

    def close(self):
        self.action = None

    def _rects(self, screen):
        width, height = 500, 230
        panel = pygame.Rect((screen.get_width() - width) // 2, (screen.get_height() - height) // 2, width, height)
        return panel, pygame.Rect(panel.x + 50, panel.bottom - 70, 185, 46), pygame.Rect(panel.right - 235, panel.bottom - 70, 185, 46)

    def handle_event(self, event, screen):
        """弹窗打开时调用；返回 'confirm'、'cancel' 或 None。"""
        if not self.is_open:
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "cancel"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            _, confirm_rect, cancel_rect = self._rects(screen)
            if confirm_rect.collidepoint(event.pos):
                return "confirm"
            if cancel_rect.collidepoint(event.pos):
                return "cancel"
        return None

    def draw(self, screen, title_font, text_font, button_font, mouse_position):
        if not self.is_open:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 18, 28, 150))
        screen.blit(overlay, (0, 0))
        panel, confirm_rect, cancel_rect = self._rects(screen)
        is_quit = self.action == "quit"
        title = "确定退出游戏吗？" if is_quit else "返回主菜单"
        message = "确定退出游戏吗？" if is_quit else "确定返回主菜单吗？当前本局进度将结束。"
        confirm_text = "退出游戏" if is_quit else "确认返回"
        cancel_text = "取消" if is_quit else "继续游戏"
        draw_panel(screen, panel)
        draw_text(screen, title, title_font, COLOR["title"], (panel.centerx, panel.y + 54))
        draw_text(screen, message, text_font, COLOR["muted_text"], (panel.centerx, panel.y + 108))
        draw_button(screen, confirm_rect, confirm_text, button_font, mouse_position, "danger")
        draw_button(screen, cancel_rect, cancel_text, button_font, mouse_position, "secondary")


def draw_arrow(screen, arrow, fill_color, highlighted=False):
    board_left = get_board_left(screen.get_width())
    center_x = board_left + arrow["col"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_x"]
    center_y = BOARD_TOP + arrow["row"] * CELL_SIZE + CELL_SIZE // 2 + arrow["offset_y"]
    if highlighted:
        pygame.draw.circle(screen, (255, 234, 154), (round(center_x), round(center_y)), 27)
    base_points = [(0, -24), (17, -3), (8, -3), (8, 23), (-8, 23), (-8, -3), (-17, -3)]
    points = []
    for point_x, point_y in base_points:
        direction = arrow["direction"]
        if direction.name == "DOWN": point_x, point_y = -point_x, -point_y
        elif direction.name == "LEFT": point_x, point_y = point_y, -point_x
        elif direction.name == "RIGHT": point_x, point_y = -point_y, point_x
        points.append((center_x + point_x, center_y + point_y))
    pygame.draw.polygon(screen, fill_color, points)
    pygame.draw.polygon(screen, COLOR["arrow_outline"], points, width=2)


def draw_board(screen, arrows, feedback_arrow=None, hovered_arrow=None, hint_arrow=None):
    board_left = get_board_left(screen.get_width())
    board_rect = pygame.Rect(board_left, BOARD_TOP, BOARD_COLS * CELL_SIZE, BOARD_ROWS * CELL_SIZE)
    pygame.draw.rect(screen, COLOR["shadow"], board_rect.inflate(16, 16).move(0, 5), border_radius=14)
    pygame.draw.rect(screen, (28, 45, 58), board_rect.inflate(12, 12), border_radius=12)
    pygame.draw.rect(screen, COLOR["board"], board_rect, border_radius=8)
    for row in range(BOARD_ROWS + 1):
        y = BOARD_TOP + row * CELL_SIZE
        pygame.draw.line(screen, COLOR["grid"], (board_left, y), (board_left + BOARD_COLS * CELL_SIZE, y), 2)
    for col in range(BOARD_COLS + 1):
        x = board_left + col * CELL_SIZE
        pygame.draw.line(screen, COLOR["grid"], (x, BOARD_TOP), (x, BOARD_TOP + BOARD_ROWS * CELL_SIZE), 2)
    for arrow in arrows:
        if not arrow["eliminated"]:
            is_hint = arrow is hint_arrow
            color = COLOR["danger"] if arrow is feedback_arrow else COLOR["arrow_hover"] if is_hint else COLOR["arrow"]
            draw_arrow(screen, arrow, color, arrow is hovered_arrow or is_hint)


def arrow_at_position(arrows, mouse_position, screen_width=None):
    mouse_x, mouse_y = mouse_position
    board_left = BOARD_LEFT if screen_width is None else get_board_left(screen_width)
    col = (mouse_x - board_left) // CELL_SIZE
    row = (mouse_y - BOARD_TOP) // CELL_SIZE
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return None
    return next((arrow for arrow in arrows if not arrow["eliminated"] and arrow["row"] == row and arrow["col"] == col), None)
