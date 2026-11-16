# -*- coding: utf-8 -*-
"""PanStroke - 抓着锅柄颠锅的手势：往上猛提到多快算一颠、点一下锅柄也算、一次按住最多颠一回（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java：常量 61-64 行，stroked（735-769 行，Diegesis 的 Stroke：按住锅柄起手势，
之后每个渲染帧报一次光标落在"过锅柄原点、正对镜头的竖直平面"上的位置，松手收尾），toss 的间隔判断（772-781 行）。
时间是秒，y 是场景像素（光标射线和那张竖直平面交点的高度，往上是正）。

- 按下：锅被手拎起来一点（pan.moveTo(0, 0.5, 0.3, 0.08)）；
- 按着的每一帧：这一帧里往上的速度 (y - 上一帧的 y) / 帧间隔 超过 FLICK（30 像素每秒）就颠，力度 = 速度从 FLICK 到 HARDEST（110）线性插到 0..1；
  一次按住最多颠一回（tossedThisPress）；
- 松手：这一按没颠过、又不到 CLICK（0.35 秒），算"点一下"，用 0.4 的力度颠（"不用找手势"）；按得久了没颠，锅放回原位（0.12 秒）。
基岩版的差别：HoD 里点一下被拒（锅空着、上一颠还在空中）时锅就停在拎起来的位置，这里也放回去。
"""
from .Mth import clamp

CLICK = 0.35              # 比这短的一按算点一下（SkilletBehavior 62）
FLICK = 30.0              # 往上的速度超过这么多（像素每秒）算一颠（63）
HARDEST = 110.0           # 到这个速度是最大的力度（64）
CLICK_STRENGTH = 0.4      # 点一下 / 点食物的力度（760、726 行）
TOSS_GAP = 0.42           # 上一颠之后这么久里不再颠（773 行）
LIFT = (0.0, 0.5, 0.3)    # 抓着锅柄，锅拎起来这么多（743 行）
LIFT_TIME = 0.08
SET_DOWN_TIME = 0.12      # 放回原位（762 行）


def strengthOf(speed):
    """往上的速度 -> 颠的力度 0..1。"""
    return clamp((speed - FLICK) / (HARDEST - FLICK), 0.0, 1.0)


class Stroke(object):
    """一次按住锅柄的手势。toss(力度) 由调用方给：颠成了返回真（锅空着、上一颠没落下就是假）。"""

    def __init__(self):
        self.pressedAt = None
        self.lastY = 0.0
        self.lastMove = 0.0
        self.tossedThisPress = False

    @property
    def held(self):
        return self.pressedAt is not None

    def start(self, y, now):
        """按下：返回要不要把锅拎起来（总是真，留给调用方做动作）。"""
        self.pressedAt, self.lastY, self.lastMove, self.tossedThisPress = now, y, now, False
        return True

    def move(self, y, now, toss):
        """按着的每一帧（y 是这一帧光标在竖直平面上的高度）。"""
        dt = now - self.lastMove
        if dt > 0.0 and not self.tossedThisPress and self.pressedAt is not None:
            speed = (y - self.lastY) / dt
            if speed > FLICK:
                self.tossedThisPress = bool(toss(strengthOf(speed)))
        if dt > 0.0:
            self.lastY, self.lastMove = y, now

    def end(self, now, toss):
        """松手。返回锅要不要放回原位（颠成了的由颠锅的动作自己收回）。"""
        settle = False
        if not self.tossedThisPress and self.pressedAt is not None and now - self.pressedAt < CLICK:
            settle = not toss(CLICK_STRENGTH)
        elif not self.tossedThisPress:
            settle = True
        self.pressedAt = None
        return settle

    def cancel(self):
        self.pressedAt = None
