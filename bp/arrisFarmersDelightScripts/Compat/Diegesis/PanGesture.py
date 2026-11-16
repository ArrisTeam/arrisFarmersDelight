# -*- coding: utf-8 -*-
"""PanGesture - 煎锅站点的手势：在锅上按住往上一甩 = 颠锅，点一下 = 取出（客户端，纯逻辑）

对应 Hands-On Delight：client/SkilletBehavior.java 按住锅柄往上甩的判定（简化：锅上任何地方按住都行）。
坐标是界面坐标（y 往下增大），时间是秒。甩 = 最近 TOSS_WITHIN 秒里指针最低处到现在往上挪了至少 TOSS_RISE；
按住不放时先停一会儿再甩也算，一按里可以甩好几次，但两次之间至少隔 TOSS_COOLDOWN
（服务端两次颠锅至少隔 0.4 秒；实机：一甩里连着过了三次门槛，后两次被拒、提示"还在空中"）。
"""
import math

TOSS_RISE = 18.0          # 窗口里往上甩这么多（界面单位）算一次颠锅
TOSS_WITHIN = 0.3         # 窗口长度（秒）：至少每秒 60 单位，慢慢往上挪不算
FULL_RISE = 60.0          # 甩这么多算全力
TOSS_COOLDOWN = 0.45      # 颠过一次后这么久里不再算（比服务端的 Frying.TURN_GAP 0.4 秒略长）
CLICK_SECONDS = 0.3       # 比这短、几乎没挪的按一下算"点"
CLICK_TRAVEL = 6.0


class PanGesture(object):
    def __init__(self):
        self.pressed = False
        self.pressedAt = 0.0
        self.recent = []              # 最近 TOSS_WITHIN 秒的 (时刻, y)
        self.last = None
        self.travel = 0.0
        self.tossed = False           # 这一按里颠过锅
        self.tossedAt = None          # 上一次颠锅的时刻

    def press(self, screen, now):
        self.pressed, self.pressedAt = True, now
        self.recent, self.last = [(now, screen[1])], screen
        self.travel, self.tossed = 0.0, False

    def move(self, screen, now):
        """按着挪动：够快够远地往上甩返回力度（0..1），否则 None。"""
        if not self.pressed or screen is None:
            return None
        self.travel += math.hypot(screen[0] - self.last[0], screen[1] - self.last[1])
        self.last = screen
        self.recent = [(at, y) for at, y in self.recent if now - at <= TOSS_WITHIN] + [(now, screen[1])]
        if self.tossedAt is not None and now - self.tossedAt < TOSS_COOLDOWN:
            return None
        rise = max(y for _, y in self.recent) - screen[1]
        if rise < TOSS_RISE:
            return None
        self.tossed, self.tossedAt, self.recent = True, now, [(now, screen[1])]
        return min(1.0, rise / FULL_RISE)

    def release(self, screen, now):
        """松手：这一按是"点一下"返回 True。"""
        if not self.pressed:
            return False
        self.move(screen, now)
        self.pressed = False
        return not self.tossed and now - self.pressedAt < CLICK_SECONDS and self.travel < CLICK_TRAVEL
