# -*- coding: utf-8 -*-
"""PanGesture - 煎锅站点的手势：在锅上按住往上一甩 = 颠锅，点一下 = 取出（客户端，纯逻辑）

对应 Hands-On Delight：client/SkilletBehavior.java 按住锅柄往上甩的判定（简化：锅上任何地方按住都行）。
坐标是界面坐标（y 往下增大），时间是秒。按住不放时判定窗口往后滑：先停一会儿再甩也算；一按里可以甩好几次。
"""
import math

TOSS_RISE = 18.0          # 窗口里往上甩这么多（界面单位）算一次颠锅
TOSS_WITHIN = 0.3         # 窗口长度（秒）：至少每秒 60 单位，慢慢往上挪不算
FULL_RISE = 60.0          # 甩这么多算全力
CLICK_SECONDS = 0.3       # 比这短、几乎没挪的按一下算"点"
CLICK_TRAVEL = 6.0


class PanGesture(object):
    def __init__(self):
        self.pressed = False
        self.pressedAt = 0.0
        self.anchor = None            # 判定窗口的起点 (界面坐标, 时刻)
        self.last = None
        self.travel = 0.0
        self.tossed = False           # 这一按里颠过锅

    def press(self, screen, now):
        self.pressed, self.pressedAt = True, now
        self.anchor, self.last = (screen, now), screen
        self.travel, self.tossed = 0.0, False

    def move(self, screen, now):
        """按着挪动：够快够远地往上甩返回力度（0..1），否则 None。"""
        if not self.pressed or screen is None:
            return None
        self.travel += math.hypot(screen[0] - self.last[0], screen[1] - self.last[1])
        self.last = screen
        start, since = self.anchor
        if now - since > TOSS_WITHIN:
            self.anchor = (screen, now)
            return None
        rise = start[1] - screen[1]
        if rise >= TOSS_RISE:
            self.anchor, self.tossed = (screen, now), True
            return min(1.0, rise / FULL_RISE)
        return None

    def release(self, screen, now):
        """松手：这一按是"点一下"返回 True。"""
        if not self.pressed:
            return False
        self.move(screen, now)
        self.pressed = False
        return not self.tossed and now - self.pressedAt < CLICK_SECONDS and self.travel < CLICK_TRAVEL
