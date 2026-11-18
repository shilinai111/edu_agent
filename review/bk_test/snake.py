#!/usr/bin/env python3
"""
贪吃蛇 (Snake) —— 纯 Python 标准库实现，无需安装任何第三方依赖。

运行:
    python3 snake.py

操作:
    方向键 / WASD  移动
    空格           暂停 / 继续
    R              重新开始
    Q / Esc        退出

说明:
    使用 curses 库绘制终端界面（Linux / macOS 自带；Windows 需先 `pip install windows-curses`）。
"""

import curses
import random
import sys

# ----------------------------- 游戏配置 -----------------------------
INITIAL_SPEED = 8          # 初始速度（每秒移动格数）
SPEED_STEP = 0.35          # 每吃一个食物提升的速度
MAX_SPEED = 25             # 速度上限
MIN_WIDTH, MIN_HEIGHT = 20, 10   # 最小可玩区域

# 方向向量 (dy, dx)
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

# 按键 -> 方向
KEY_MAP = {
    curses.KEY_UP: UP, ord('w'): UP, ord('W'): UP,
    curses.KEY_DOWN: DOWN, ord('s'): DOWN, ord('S'): DOWN,
    curses.KEY_LEFT: LEFT, ord('a'): LEFT, ord('A'): LEFT,
    curses.KEY_RIGHT: RIGHT, ord('d'): RIGHT, ord('D'): RIGHT,
}


class SnakeGame:
    """贪吃蛇游戏核心逻辑（与界面无关，便于测试）。"""

    def __init__(self, height, width):
        # 可玩区域（不含边框）
        self.height = height
        self.width = width
        self.reset()

    def reset(self):
        """重置游戏状态。"""
        cy, cx = self.height // 2, self.width // 2
        # 蛇身：列表，头部在索引 0
        self.snake = [(cy, cx), (cy, cx - 1), (cy, cx - 2)]
        self.direction = RIGHT
        self.pending_direction = RIGHT
        self.score = 0
        self.speed = INITIAL_SPEED
        self.game_over = False
        self.paused = False
        self.food = self._spawn_food()

    def _spawn_food(self):
        """在空白格随机生成食物。"""
        empty = [
            (y, x)
            for y in range(self.height)
            for x in range(self.width)
            if (y, x) not in self.snake
        ]
        return random.choice(empty) if empty else None

    def set_direction(self, new_dir):
        """设置方向，禁止 180 度掉头。"""
        dy, dx = new_dir
        cy, cx = self.direction
        if (dy, dx) == (-cy, -cx):   # 反向
            return
        self.pending_direction = new_dir

    def step(self):
        """推进一帧。返回 True 表示吃到食物。"""
        if self.game_over or self.paused:
            return False

        self.direction = self.pending_direction
        dy, dx = self.direction
        hy, hx = self.snake[0]
        new_head = (hy + dy, hx + dx)

        # 撞墙
        if not (0 <= new_head[0] < self.height and 0 <= new_head[1] < self.width):
            self.game_over = True
            return False

        # 撞自己（尾巴即将移开的格子不算）
        body = self.snake[:-1] if new_head != self.food else self.snake
        if new_head in body:
            self.game_over = True
            return False

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.speed = min(MAX_SPEED, self.speed + SPEED_STEP)
            self.food = self._spawn_food()
            if self.food is None:      # 填满整个屏幕 -> 通关
                self.game_over = True
            return True

        self.snake.pop()               # 没吃到就移除尾巴
        return False


# ----------------------------- 界面绘制 -----------------------------
def draw(stdscr, game):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # 标题栏
    title = f" 贪吃蛇  |  得分: {game.score}  |  速度: {game.speed:.1f} "
    try:
        stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    # 边框
    top = 2
    left = 1
    right = left + game.width + 1
    bottom = top + game.height + 1
    if bottom >= h or right >= w:
        stdscr.addstr(1, 1, "窗口太小，请放大终端窗口后按 R 重开")
        stdscr.refresh()
        return

    for x in range(left, right + 1):
        stdscr.addch(top, x, curses.ACS_HLINE)
        stdscr.addch(bottom, x, curses.ACS_HLINE)
    for y in range(top, bottom + 1):
        stdscr.addch(y, left, curses.ACS_VLINE)
        stdscr.addch(y, right, curses.ACS_VLINE)
    stdscr.addch(top, left, curses.ACS_ULCORNER)
    stdscr.addch(top, right, curses.ACS_URCORNER)
    stdscr.addch(bottom, left, curses.ACS_LLCORNER)
    stdscr.addch(bottom, right, curses.ACS_LRCORNER)

    # 食物
    if game.food:
        fy, fx = game.food
        stdscr.addch(top + 1 + fy, left + 1 + fx, '●', curses.color_pair(2) | curses.A_BOLD)

    # 蛇
    for i, (sy, sx) in enumerate(game.snake):
        ch = '@' if i == 0 else 'o'
        attr = curses.color_pair(1) | (curses.A_BOLD if i == 0 else 0)
        stdscr.addch(top + 1 + sy, left + 1 + sx, ch, attr)

    # 底部提示
    hint = " 方向键/WASD 移动 | 空格 暂停 | R 重开 | Q 退出 "
    try:
        stdscr.addstr(bottom + 1, max(0, (w - len(hint)) // 2), hint, curses.A_DIM)
    except curses.error:
        pass

    # 覆盖层
    if game.game_over:
        msg = f" 游戏结束！得分 {game.score} —— 按 R 重新开始 "
        _center_msg(stdscr, top, bottom, left, right, msg, curses.color_pair(3) | curses.A_BOLD)
    elif game.paused:
        _center_msg(stdscr, top, bottom, left, right, " 已暂停 —— 按空格继续 ",
                    curses.color_pair(2) | curses.A_BOLD)

    stdscr.refresh()


def _center_msg(stdscr, top, bottom, left, right, msg, attr):
    y = (top + bottom) // 2
    x = left + max(0, (right - left - len(msg)) // 2)
    try:
        stdscr.addstr(y, x, msg, attr)
    except curses.error:
        pass


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)          # 非阻塞输入
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # 蛇
    curses.init_pair(2, curses.COLOR_RED, -1)     # 食物
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  # 结束提示

    h, w = stdscr.getmaxyx()
    game = SnakeGame(max(MIN_HEIGHT, h - 5), max(MIN_WIDTH, w - 4))

    while True:
        draw(stdscr, game)

        # 输入处理
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):        # 27 = Esc
            break
        elif key in (ord('r'), ord('R')):
            game.reset()
        elif key == ord(' '):
            if not game.game_over:
                game.paused = not game.paused
        elif key in KEY_MAP:
            game.set_direction(KEY_MAP[key])

        # 逻辑推进（按速度控制帧率）
        if not game.game_over and not game.paused:
            curses.napms(int(1000 / game.speed))
            game.step()
        else:
            curses.napms(30)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("感谢游玩！")
    sys.exit(0)
