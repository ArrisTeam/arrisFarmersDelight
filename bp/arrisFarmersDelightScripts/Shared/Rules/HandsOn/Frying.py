# -*- coding: utf-8 -*-
"""Frying - 煎锅的两面煎制状态机（双端）

移植自 Hands-On Delight 的 station/Frying.java（两面进度）与 station/SkilletCooking.java（sideTicks / fry / turn /
place / skilletTicks）。

手放进煎锅的食材先煎贴锅的那一面，这面熟了就等着，厨师颠锅把它翻过来，另一面熟了才算完成；
一次最多煎 BATCH 件，批越大一面越慢（按件数的平方根）。蛋这类单面煎的食材从下往上一次煎透，不用翻。
非手放的食材（FD 自己的右键）按 FD 原样一件一件煎。

时间一律是秒（原版以刻计，20 刻/秒）。每一步推进 dt 秒；进度 0..1，满 1 即这一面熟了。
煎锅每个烹饪步的调用顺序（对应 SkilletCooking.fry），批量先定、再按批量算一面的时长：

    pan.resize(min(锅里件数, BATCH))
    side = sideSeconds(skilletSeconds(营火秒数, 火焰附加), pan.batch, 配置倍率)
    if pan.step(dt, side, 是否单面食材):   # 两面都熟：食材换成成品，pan.reset()
        ...
"""
import math

from .Mth import EPS, NEVER, TICK, clamp, floorInt, reached, roundToTick

BATCH = 16               # 一锅最多煎几件
PACE = 1.5               # 比 FD 的煎锅快 1.5 倍（和锅、灶台一致）
TURN_GAP = 0.4           # 原 TURN_GAP = 8 刻：两次颠锅的最小间隔，食材还在空中
MIN_SKILLET = 3.0        # 原 60 刻（FD SkilletBlock.MINIMUM_COOKING_TIME）
DEFAULT_RECIPE = 30.0    # 原 600 刻：配方没写时间时 FD 当 600 刻算
STEPS = 16               # 原 Frying.STEPS：判断"要不要再通知客户端"的进度粒度
SYNC_STEP = 1.0 / 32.0   # 原 SkilletLogic.STEP：同步给客户端的进度粒度，外观在两档之间平滑过渡


def skilletSeconds(campfireSeconds, fireAspect=0):
    """FD 的煎锅煎一件要多久（SkilletBlock.getSkilletCookingTime）：营火时间的 20%，火焰附加每级少 5%，
    取整到整秒，夹在 3 秒到营火时间之间。营火 30 秒 -> 6 秒。"""
    base = campfireSeconds if campfireSeconds > 0 else DEFAULT_RECIPE
    reduction = 0.2 - fireAspect * 0.05 if fireAspect > 0 else 0.2
    # 加一点点：双精度下 30 * 0.1 可能是 2.9999999999999996，Java 的 float 算出来是整的
    seconds = float(int(int(base) * reduction + 1.0e-9))
    return clamp(seconds, MIN_SKILLET, campfireSeconds if campfireSeconds > 0 else DEFAULT_RECIPE)


def sideSeconds(skilletTime, batch, times=1.0, quantize=True):
    """煎熟 batch 件的一面要多久：FD 煎锅时间 * 配置倍率 * sqrt(件数) / 1.5 / 2（SkilletCooking.sideTicks）。

    quantize=True 取整到整刻（和原版逐刻累加的结果一致）；False 保留连续值。
    """
    seconds = skilletTime * times * math.sqrt(max(1, batch)) / PACE / 2.0
    return roundToTick(seconds) if quantize else max(TICK, seconds)


def syncStep(done):
    """进度同步给客户端时的量化：熟了是 1，否则向下取到 1/32 的整数倍。"""
    return 1.0 if done >= 1.0 else math.floor(done / SYNC_STEP) * SYNC_STEP


def placeCount(carried, inPan, maxStack, one=False):
    """手里 carried 件往锅里放，能放进几件（SkilletCooking.place）：整叠或单件，锅里最多 min(BATCH, 堆叠上限)。
    只管数量；是不是同一种食材、能不能煎由调用方判断。"""
    return max(0, min(1 if one else carried, min(BATCH, maxStack) - inPan))


class Frying(object):
    """煎锅里这一锅食材的进度：贴锅面 down、朝上面 up（0..1）。"""

    def __init__(self):
        self.down = 0.0
        self.up = 0.0
        self.batch = 0                   # 现在按多少件算；一面要的时间随它增长
        self.byHand = False              # 手放/手翻的：两面分开煎，等着翻。否则 FD 自己煎
        self.turnedAt = NEVER
        self._sent = -1

    def waits(self):
        """贴锅这面熟了、朝上面还生：什么都不动，等厨师翻。"""
        return self.byHand and reached(self.down) and not reached(self.up)

    def isDone(self):
        return reached(self.down) and reached(self.up)

    def layByHand(self):
        self.byHand = True

    def farmersDelightsWay(self):
        """回到 FD 自己的煎法，进度清零：右键放进来的食材，或者锅空了。"""
        self.byHand = False
        self.reset()

    def reset(self):
        self.down = 0.0
        self.up = 0.0
        self.batch = 0

    def fry(self, amount):
        self.down = min(1.0, self.down + amount)

    def fryThrough(self, amount):
        """单面煎的食材（蛋）从下往上煎透：上面和下面一起熟，不会等翻。"""
        self.down = min(1.0, self.down + amount)
        self.up = self.down

    def step(self, dt, side, oneSided=False):
        """煎 dt 秒，side 是一面的总时长(sideSeconds)。单面食材的速度减半（两面的时间一次煎完）。返回是否整锅熟了。"""
        if oneSided:
            self.fryThrough(0.5 * dt / side)
        else:
            self.fry(dt / side)
        return self.isDone()

    def turn(self, now):
        self.down, self.up = self.up, self.down
        self.turnedAt = now

    def canTurn(self, now, hasFood=True):
        """颠锅是否被接受：锅里有能煎的食材(hasFood)，且离上一次颠够久。不要求贴锅面已经熟——随时可以翻。"""
        return hasFood and now - self.turnedAt >= TURN_GAP - EPS

    def toss(self, now, hasFood=True):
        """厨师颠锅（SkilletCooking.turn）。被拒绝返回 False。FD 自己煎着的锅，颠一下就从此归厨师，从生开始重算。"""
        if not self.canTurn(now, hasFood):
            return False
        if not self.byHand:
            self.reset()
        self.byHand = True
        self.turn(now)
        return True

    def resize(self, batch):
        """按 batch 件煎了：加了生的、拿走了熟的，已经煎的进度按所需时间重新分摊（一面的时间按件数的平方根）。"""
        if self.batch > 0 and batch > 0 and batch != self.batch:
            scale = math.sqrt(float(self.batch) / batch)
            self.down = min(1.0, self.down * scale)
            self.up = min(1.0, self.up * scale)
        self.batch = batch

    def stateKey(self):
        steps = floorInt(self.down * STEPS) * (STEPS + 1) + floorInt(self.up * STEPS)
        return (steps * 31 + self.batch) * 2 + (1 if self.byHand else 0)

    def dueToSend(self):
        """要不要再告诉客户端：进度走了一格(1/16)，或批量、手放标记变了。"""
        key = self.stateKey()
        if key == self._sent:
            return False
        self._sent = key
        return True
