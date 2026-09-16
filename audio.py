# -*- coding: utf-8 -*-
"""可选的本地音效；任何音频初始化或资源失败都静默降级。"""

from pathlib import Path

import pygame


class SoundManager:
    """只加载 assets/sounds 中的免版权或自制音效，不依赖外部服务。"""

    FILENAMES = {
        "button": "button.ogg",
        "fly": "fly.ogg",
        "blocked": "blocked.ogg",
        "win": "win.ogg",
        "lose": "lose.ogg",
    }

    def __init__(self, asset_dir=None):
        self.enabled = True
        self.available = False
        self.sounds = {}
        asset_dir = Path(asset_dir or Path(__file__).parent / "assets" / "sounds")
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self.available = True
            for name, filename in self.FILENAMES.items():
                path = asset_dir / filename
                if path.is_file():
                    try:
                        self.sounds[name] = pygame.mixer.Sound(str(path))
                    except pygame.error:
                        pass
        except (pygame.error, OSError, AttributeError):
            # 没有音频设备、驱动不可用或混音器初始化失败时，游戏仍正常运行。
            self.enabled = False

    def play(self, name):
        if self.enabled and self.available:
            sound = self.sounds.get(name)
            if sound is not None:
                try:
                    sound.play()
                except (pygame.error, AttributeError):
                    pass

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
