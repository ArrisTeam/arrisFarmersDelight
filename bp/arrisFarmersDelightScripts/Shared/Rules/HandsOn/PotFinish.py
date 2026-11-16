# -*- coding: utf-8 -*-
"""PotFinish - 一批煮好的那一刻：浮着的料胀大再缩没、冒汽，碎料等它们走完才浮上来（双端）

移植自 Hands-On Delight 的 client/PotBehavior.java：cookedThrough（956-983 行）、melt（986-1015 行）、burst（1017-1023 行），
常量见 127-135 行。时间一律是秒（Java 的刻 = 1/20 秒；这里本来就是秒）。

一批煮好、成品落进汤里的那一帧，FD 已经把料从格子里取走了：槽里原来浮着的整件料（槽空了的、不是倒进去 / 打进去 / 溶掉的）
在原来浮的地方留下一个"替身"。替身一个接一个（每个晚 MELT_STAGGER 秒）先 SWELL_TIME 秒从 1 胀到 SWELL 倍，
再按 SWELL * (1 - (age - SWELL_TIME) / (MELT_TIME - SWELL_TIME)) ** 2 缩到 0（在 MELT_TIME 秒），一边每秒下沉 SINK_SPEED 像素；
缩没的那一刻放一串汽、闪光、一圈涟漪和炸开的声音。最后一个替身之后再等 PIECES_WAIT 秒，煮好的碎料才开始浮上来。

位置的约定同 Java：料的节点原点在场景的 (8, 8, 8)，pose 里的 pos 是相对它的偏移（Java 的 itemX、液面 - ITEM_REST、itemZ），
事件里的位置是场景像素（偏移 + NODE_ORIGIN）。

    state = start([0, 2], {0: (x, y, z), 2: (x, y, z)}, now)       # 一批煮好的那一帧
    poses, events = state.step(dt)                                  # 之后每帧
"""
from .Mth import lerp
from .PotSounds import shotOf

SWELL_TIME = 0.16        # 先胀这么久
SWELL = 1.4              # 胀到这么大
MELT_TIME = 0.55         # 到这个时刻缩没
MELT_STAGGER = 0.07      # 一个接一个，各晚这么久
PIECES_WAIT = 0.25       # 最后一个缩没之后再等这么久，碎料才开始浮上来
SINK_SPEED = 0.7         # 缩的时候每秒下沉的像素（PB 1006）
NODE_ORIGIN = 8.0        # 料的节点在场景里的原点（8, 8, 8）
POT_CENTER = 8.0         # 起头那圈涟漪在锅中心（场景像素）
START_BUBBLES = 10       # 起头：从汤里冒出的气泡数
START_RIPPLE = 0.3
BURST_STEAM = 4
BURST_GLINT = 3
BURST_RIPPLE = 0.35
RISE = (0.0, 3.5, 0.0)       # 气泡的升速
PUFF_UP = (0.0, 4.0, 0.0)    # 汽和闪光的升速
GLINT_COLOR = 0xFFFFE9A0
BUBBLE_COLOR = 0xE0FFFFFF    # 没给气泡颜色时用的缺省（Java 里是汤的颜色泡开的，由汤的模块算）


def meltScale(age):
    """替身 age 秒时的缩放：age < 0 在等，1；先 1 -> SWELL（SWELL_TIME 秒），再 SWELL * (1 - 比例) 的平方缩到 0（MELT_TIME 秒）。"""
    if age < 0.0:
        return 1.0
    if age < SWELL_TIME:
        return lerp(age / SWELL_TIME, 1.0, SWELL)
    left = 1.0 - (age - SWELL_TIME) / (MELT_TIME - SWELL_TIME)
    return SWELL * left * left


def piecesWait(copies):
    """碎料要等多久（秒）才浮上来：copies 个替身 -> copies * MELT_STAGGER + MELT_TIME + PIECES_WAIT。"""
    return copies * MELT_STAGGER + MELT_TIME + PIECES_WAIT


class Finish(object):
    """一批煮好的收尾：替身的姿态和那些气泡、汽、闪光、涟漪、声音。用 start() 造。"""

    def __init__(self, slots, positions, now, bubbleColor=BUBBLE_COLOR):
        self.startedAt = now
        self.age = 0.0
        self.copies = [{"slot": slot, "pos": tuple(positions[slot]), "age": -index * MELT_STAGGER}
                       for index, slot in enumerate(slots)]
        self.wait = piecesWait(len(self.copies)) if self.copies else 0.0
        self.piecesAt = now + self.wait if self.copies else None
        self._events = []
        if self.copies:
            self._events.append({"type": "bubbles", "count": START_BUBBLES, "rise": RISE, "color": bubbleColor})
            self._events.append({"type": "ripple", "x": POT_CENTER, "z": POT_CENTER, "strength": START_RIPPLE})

    @property
    def waiting(self):
        """碎料还不该浮上来（PB 的 piecesWait > 0：这期间 pieces() 什么都不做）。"""
        return self.wait > 0.0

    @property
    def done(self):
        """替身都走完了，碎料也放行了。"""
        return not self.copies and not self.waiting and not self._events

    def step(self, dt):
        """推进 dt 秒。返回 (poses, events)。

        poses：这一帧还在或刚走完的替身，[{"slot", "pos": (x, y, z), "scale", "visible"}]，按槽位升序；
        走完的那一帧 visible 为 False（调用方此时把它的节点藏起来），之后不再出现。
        events：{"type": ...}：bubbles / ripple / steam / glint / sound（burst）/ pieces（碎料等够了，现在可以浮上来）。
        """
        self.age += dt
        events, self._events = self._events, []
        poses, alive = [], []
        for copy in sorted(self.copies, key=lambda each: each["slot"]):
            copy["age"] += dt
            age = copy["age"]
            x, y, z = copy["pos"]
            if age >= MELT_TIME:
                poses.append({"slot": copy["slot"], "pos": (x, y, z), "scale": 0.0, "visible": False})
                events += self._burst(copy["slot"], x, y, z)
                continue
            alive.append(copy)
            sunk = y - max(age, 0.0) * SINK_SPEED
            poses.append({"slot": copy["slot"], "pos": (x, sunk, z), "scale": meltScale(age), "visible": True})
        self.copies = alive
        if self.wait > 0.0:
            self.wait -= dt
            if self.wait <= 0.0:
                self.wait = 0.0
                events.append({"type": "pieces"})
        return poses, events

    @staticmethod
    def _burst(slot, x, y, z):
        """替身缩没的那一刻（PB 1017-1023）：汽 x4、闪光 x3、一圈涟漪、炸开的声音。位置用没下沉的起点（Java 用 meltY）。"""
        at = (NODE_ORIGIN + x, NODE_ORIGIN + y, NODE_ORIGIN + z)
        return [{"type": "steam", "count": BURST_STEAM, "pos": at, "rise": PUFF_UP, "spread": 0.5, "color": 0},
                {"type": "glint", "count": BURST_GLINT, "pos": at, "rise": PUFF_UP, "spread": 0.9, "color": GLINT_COLOR},
                {"type": "ripple", "x": at[0], "z": at[2], "strength": BURST_RIPPLE},
                shotOf("burst", slot)]


def start(slots, positions, now, bubbleColor=BUBBLE_COLOR):
    """一批煮好了：slots 是槽里原来浮着、现在空了的槽位（按槽位升序，下标就是错开的次序），positions[槽位] 是它浮着的 (x, y, z)，
    now 是此刻的时间（秒，记在 startedAt / piecesAt 上）。slots 为空返回一个已经完事的状态（PB 里 melting == 0 什么都不发生）。"""
    return Finish(list(slots), positions, now, bubbleColor)
