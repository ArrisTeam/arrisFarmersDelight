# -*- coding: utf-8 -*-
"""BoardMotion - 板上东西的动作：放下时落下、拿走时抬起融掉、板不收时弹回、一层层叠起来、做成时融掉再弹出（双端）

移植自 Hands-On Delight 的 client/BoardBehavior.java：land / landFromPlayer / taken / pulledOut / bounced / pop 和各个时间常量
（56-208、560-570、595-608、654-727、1620-1652），Diegesis 的 Tween（impl/client/anim/Tween.java：inOutCubic 缓动，hop 在中途
加一道 sin 的弧）。每个东西一个 Mover：位置、缩放、看得见不；move / hop / scaleTo / after 排动作，update(dt) 推进，和 HoD 的节点一样。
时间一律是秒，位置是场景像素（原点在板面中心上方 0 = 板面），客户端把它换成道具的位置。
"""
import math

from .Mth import clamp

LAND_TIME = 0.2            # 手放下的一叠落到位用这么久
LAND_HOP = 0.8             # 落下时的弧高（像素）
SETTLE_TIME = 0.12         # 落定后再弹一下
SETTLE_HOP = 0.25
DROP_HEIGHT = 3.0          # 从光标上方这么高落下来
FROM_CURSOR = 10.0         # 光标离落点超过这么远，从这么远处落下
PLAYER_LAND_TIME = 0.32    # 书里一次放的几层从玩家（屏幕底边）飞来
LAYER_STAGGER = 0.16       # 它们依次出发，隔这么久
LIFT_TIME = 0.1            # 拿走的东西抬起来
LIFT_HEIGHT = 2.5
AWAY_TIME = 0.2           # 再往上一点、缩没
BOUNCE_DOWN = 0.09         # 板不收的东西：落到板顶
BOUNCE_UP = 0.22           # 弹回手上
PULL_HEIGHT = 5.0          # 插着的工具往外拔
PULL_TIME = 0.18
CARVED_Y = 0.23 * 16.0 - 1.01   # FD 把插着的工具画在方块中间、0.23 格高（从放东西的高度算起）
CARVED_SCALE = 0.6
MELT_TIME = 0.28           # 层沉进一道菜
POP_TIME = 0.35            # 做好的菜弹出来
POP_HEIGHT = 1.6
GONE_TIME = 0.25           # 最后一刀：切开的食物往上飘、缩没
GONE_LIFT = 2.5
LAYER_STEP = 0.65          # 层与层相隔
PILE_LIFT = 0.65           # 一叠不止一个时，上面那个抬高这么多


def inOutCubic(t):
    """Easing.inOutCubic。"""
    t = clamp(t, 0.0, 1.0)
    return 4.0 * t * t * t if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def layerTurn(layer):
    """手放的一层转一点、偏一点，不会两层一样（turn / jitterX / jitterZ，560-570）：层号的固定函数。"""
    return 0.0 if layer == 0 else ((layer * 7919) % 31 - 15) * 1.1


def layerJitter(layer):
    """(x, z) 的偏移，像素。"""
    return (((layer * 4513) % 7 - 3) * 0.12, ((layer * 2971) % 7 - 3) * 0.12)


def itemHeight(count, isBlock=False, itemSize=10.0, blockSize=5.2):
    """等着切的东西的顶面离板面多高（itemHeight，1063-1068）：方块是它的边长，图标一叠不止一个时再抬 PILE_LIFT。"""
    if isBlock:
        return blockSize
    return (PILE_LIFT if count > 1 else 0.0) + itemSize / 16.0


class Mover(object):
    """一个东西的位置和缩放（Diegesis 的 NodeInstance 里的 offset / scale 两个 Tween 加上 after 的排程）。"""

    def __init__(self, x=0.0, y=0.0, z=0.0, scale=1.0, visible=True):
        self.pos = (x, y, z)
        self.scale = scale
        self.visible = visible
        self._from, self._to, self._age, self._seconds, self._arc = self.pos, self.pos, 0.0, 0.0, 0.0
        self._scaleFrom, self._scaleTo, self._scaleAge, self._scaleSeconds = scale, scale, 0.0, 0.0
        self._clock = 0.0
        self._steps = []

    def move(self, x, y, z, seconds=0.0, hop=0.0):
        """从现在的位置往 (x, y, z) 走 seconds 秒（0 = 跳过去）；hop 是走到一半时多出来的高度（弧）。"""
        self._from, self._to, self._age, self._seconds, self._arc = self.pos, (x, y, z), 0.0, max(0.0, seconds), hop
        if self._seconds == 0.0:
            self.pos = self._to

    def scaleTo(self, factor, seconds=0.0):
        self._scaleFrom, self._scaleTo, self._scaleAge, self._scaleSeconds = self.scale, factor, 0.0, max(0.0, seconds)
        if self._scaleSeconds == 0.0:
            self.scale = factor

    def after(self, seconds, run):
        """seconds 秒之后做 run（HoD 的 after / Step）。"""
        self._steps.append((self._clock + seconds, run))

    @property
    def moving(self):
        return self._age < self._seconds or self._scaleAge < self._scaleSeconds

    def update(self, dt):
        self._clock += dt
        if self._age < self._seconds:
            self._age = min(self._age + dt, self._seconds)
            t = inOutCubic(self._age / self._seconds)
            self.pos = tuple(a + (b - a) * t for a, b in zip(self._from, self._to))
            if self._arc:
                self.pos = (self.pos[0], self.pos[1] + self._arc * math.sin(math.pi * self._age / self._seconds), self.pos[2])
        if self._scaleAge < self._scaleSeconds:
            self._scaleAge = min(self._scaleAge + dt, self._scaleSeconds)
            self.scale = self._scaleFrom + (self._scaleTo - self._scaleFrom) * inOutCubic(self._scaleAge / self._scaleSeconds)
        due = [step for step in self._steps if step[0] <= self._clock]
        self._steps = [step for step in self._steps if step[0] > self._clock]
        for _at, run in due:
            run()


def land(mover, home, start):
    """手放下的一叠（land，595-600）：从 start（光标上方）弧着落到 home，再落定一下。"""
    mover.visible = True
    mover.move(*start)
    mover.move(home[0], home[1], home[2], LAND_TIME, LAND_HOP)
    mover.after(LAND_TIME, lambda: mover.move(home[0], home[1], home[2], SETTLE_TIME, SETTLE_HOP))


def landFromPlayer(mover, home, offset):
    """书里放的一层从玩家（屏幕底边）飞来（landFromPlayer，603-608）：offset 是玩家那一点离落点的水平偏移 (x, z)。"""
    mover.visible = True
    mover.move(home[0] + offset[0], home[1] + DROP_HEIGHT, home[2] + offset[1])
    mover.move(home[0], home[1], home[2], PLAYER_LAND_TIME, LAND_HOP * 2.5)
    mover.after(PLAYER_LAND_TIME, lambda: mover.move(home[0], home[1], home[2], SETTLE_TIME, SETTLE_HOP))


def _hide(mover):
    mover.visible = False


def lift(mover, home):
    """拿走的东西（taken，654-678）：在原位抬起 LIFT_HEIGHT，再往上一点缩没，然后不见。"""
    x, y, z = home
    mover.visible = True
    mover.scaleTo(1.0)
    mover.move(x, y, z)
    mover.move(x, y + LIFT_HEIGHT, z, LIFT_TIME)

    def away():
        mover.move(x, y + LIFT_HEIGHT + 1.0, z, AWAY_TIME)
        mover.scaleTo(0.0, AWAY_TIME)
    mover.after(LIFT_TIME, away)
    mover.after(LIFT_TIME + AWAY_TIME, lambda: _hide(mover))


def pullOut(mover, home):
    """插着的工具被拔出来（pulledOut，684-706）：抬 PULL_HEIGHT，再上去一点缩没。"""
    x, y, z = home
    mover.visible = True
    mover.scaleTo(1.0)
    mover.move(x, y, z)
    mover.move(x, y + PULL_HEIGHT, z, PULL_TIME)

    def away():
        mover.move(x, y + PULL_HEIGHT + 1.0, z, AWAY_TIME)
        mover.scaleTo(0.0, AWAY_TIME)
    mover.after(PULL_TIME, away)
    mover.after(PULL_TIME + AWAY_TIME, lambda: _hide(mover))


def bounce(mover, top, hand):
    """板不收的东西（bounced，715-727）：从手上落到板顶 top（离板面多高）、弹回手上。hand 是手的位置 (x, y, z)。"""
    mover.visible = True
    mover.scaleTo(1.0)
    mover.move(*hand)
    mover.move(hand[0] * 0.3, top, hand[2] * 0.3, BOUNCE_DOWN)
    mover.after(BOUNCE_DOWN, lambda: mover.move(hand[0], hand[1], hand[2], BOUNCE_UP, 1.2))
    mover.after(BOUNCE_DOWN + BOUNCE_UP, lambda: _hide(mover))


def melt(mover, rest):
    """一层沉进做成的菜（pop 里的各层，1621-1631）：缩到 0.1、往板中间沉（x、z 缩到 0.4，高缩到 0.08）。rest 是它躺着的位置 (x, y, z)。"""
    mover.scaleTo(0.1, MELT_TIME)
    mover.move(rest[0] * 0.4, rest[1] * 0.08, rest[2] * 0.4, MELT_TIME)


def popUp(mover, home):
    """做好的菜弹出来（pop 里的菜，1632-1637）：从 0.3 长到 1，同时跳 POP_HEIGHT。"""
    mover.visible = True
    mover.scaleTo(0.3)
    mover.scaleTo(1.0, POP_TIME)
    mover.move(home[0], home[1], home[2], POP_TIME, POP_HEIGHT)


def floatAway(mover, home):
    """最后一刀切开的食物（item_gone，1448-1449）：往上飘 GONE_LIFT、缩没，用 GONE_TIME 秒。"""
    mover.visible = True
    mover.scaleTo(1.0)
    mover.move(home[0], home[1], home[2])
    mover.move(home[0], home[1] + GONE_LIFT, home[2], GONE_TIME)
    mover.scaleTo(0.0, GONE_TIME)
    mover.after(GONE_TIME, lambda: _hide(mover))
