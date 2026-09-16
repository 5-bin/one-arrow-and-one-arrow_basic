# 一箭又一箭

“一箭又一箭”是一款使用 Python 与 Pygame 开发的单机益智小游戏。玩家需要判断箭头前方是否畅通，选择没有被其他箭头阻挡的箭头，使其飞出棋盘；清除全部箭头即可通关。

项目包含 6 个难度递增的关卡、提示与自动求解、计分和星级评价、音效开关、关卡选择及失败重开等功能，并已提供 macOS 可执行版本。

## 快速开始

### 直接运行源码

运行环境为 Python 3.13 和 Pygame 2.6.1。进入项目根目录后执行：

```bash
./.venv/bin/python main.py
```

若本地尚未安装依赖，可在自己的虚拟环境中安装 Pygame 后执行：

```bash
python -m pip install pygame
python main.py
```

### 运行打包版本

macOS 可执行程序位于：

```text
dist/一箭又一箭.app
```

也可使用命令行版本：

```text
dist/一箭又一箭/一箭又一箭
```

## 游戏规则

- 点击朝向路径上没有其他未消除箭头的箭头，箭头会沿其指向飞出棋盘。
- 若前方有箭头，当前箭头不能飞出，会显示短暂的红色晃动，并扣除一次失误机会。
- 清除本关全部箭头即可进入结算页；完成当前关后解锁下一关。
- 每关可使用最多 3 次提示；提示会高亮一支当前可飞出的箭头。
- 点击“自动求解”后，程序会使用内置 DFS 求解器演示一条合法清关顺序。
- 重新开始会恢复该关的初始箭头、分数、计时、提示次数和失误次数。

## 计分与星级

每消除一支箭头获得 100 分；点击被阻挡的箭头扣 30 分，分数最低为 0。结算星级规则如下：

| 星级 | 分数要求 | 用时要求 |
| --- | --- | --- |
| 三星 | 不低于理论满分的 90% | 不超过 30 秒 |
| 二星 | 不低于理论满分的 60% | 不超过 60 秒 |
| 一星 | 未达到以上条件 | 无额外要求 |

## 项目结构

```text
.
├── main.py                 # 程序入口，并导出核心逻辑以兼容测试
├── game_runner.py          # Pygame 事件循环、页面状态和交互编排
├── config.py               # 棋盘、界面、计分和关卡配置
├── game_logic.py           # 阻挡判断、提示选择、DFS 自动求解和星级计算
├── rendering.py            # 字体、棋盘、箭头、按钮和弹窗绘制
├── audio.py                # 本地音效加载与降级处理
├── assets/sounds/          # 音效资源及来源说明
├── tests/
│   ├── test_game_logic.py  # 19 项纯逻辑自动化测试
│   └── TEST_RECORD_TEMPLATE.md  # 人工测试记录表
├── docs/项目报告.md         # 作业提交用项目报告
└── dist/                   # PyInstaller 打包产物
```

## 测试

运行全部自动化测试：

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

当前测试覆盖路径阻挡判断、边界箭头、关卡可解性、重开深拷贝、DFS 求解保护、提示选择和星级计算等核心逻辑。人工试玩项请按 [`tests/TEST_RECORD_TEMPLATE.md`](tests/TEST_RECORD_TEMPLATE.md) 记录。

## 资源与许可

游戏音效的文件来源与许可信息见 [`assets/sounds/SOURCES.md`](assets/sounds/SOURCES.md) 和 [`assets/sounds/LICENSE-KENNEY-CC0.txt`](assets/sounds/LICENSE-KENNEY-CC0.txt)。
