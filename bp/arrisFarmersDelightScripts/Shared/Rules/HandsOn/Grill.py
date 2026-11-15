# -*- coding: utf-8 -*-
"""Grill - 灶台六个位置的两面烧烤状态机（双端）

移植自 Hands-On Delight 的 station/Grill.java（每个位置的两面进度）与 station/StoveCooking.java
（sideTicks / tick / place / turn / farmersDelightsTime）。

规则和煎锅一致，区别：灶台有 PLACES 个位置，每位置一件，各自独立；不看批量（没有 sqrt）；
翻面间隔更短；灶台没点着(lit)时不烤。手放的食材先烤贴炉面这一面，熟了就冒烟等着翻，翻过去烤另一面，
两面都熟变成成品，留在炉上等厨师来拿。蛋这类单面食材一次烤透，不用翻。

时间一律是秒（原版以刻计，20 刻/秒）。灶台每个烹饪步，对每个手放且有东西的位置（对应 StoveCooking.tick）：

    side = sideSeconds(营火秒数, 配置倍率)
    if grill.step(place, dt, side, 是否单面食材, 灶台是否点着):   # 两面都熟：换成成品，grill.done(place)
        ...
"""
from .Frying import STEPS, syncStep
from .Mth import EPS, NEVER, TICK, floorInt, reached, roundToTick

PLACES = 6               # 灶台上最多几个位置
PACE = 1.5               # 比 FD 的灶台快 1.5 倍（和锅、煎锅一致）
TURN_GAP = 0.3           # 原 TURN_GAP = 6 刻：同一件两次翻面的最小间隔

__all__ = ["PLACES", "PACE", "TURN_GAP", "STEPS", "syncStep", "sideSeconds", "laidPlaces", "handOverSeconds", "Grill"]


def sideSeconds(recipeSeconds, times=1.0, quantize=True):
    """烤熟一面要多久：FD 灶台的配方时间 * 配置倍率 / 1.5 / 2（StoveCooking.sideTicks）。600 刻 -> 200 刻。"""
    seconds = recipeSeconds * times / PACE / 2.0
    return roundToTick(seconds) if quantize else max(TICK, seconds)


def laidPlaces(occupied, place=-1, pieces=None):
    """手里一叠食材放上灶台：place 为 -1 时每个空位放一件，直到件数 pieces 用完（None = 不限）；
    place >= 0 只放那个位置（它得是空的）。occupied 是各位置是否有东西，返回放了哪些位置。"""
    laid = []
    for at in range(len(occupied)):
        if pieces is not None and len(laid) >= pieces:
            break
        if (place >= 0 and at != place) or occupied[at]:
            continue
        laid.append(at)
    return laid


def handOverSeconds(recipeSeconds, bothSidesDone, times=1.0):
    """把一件交还给 FD 自己烤时给它的总时长：已经两面都熟的 1 刻（马上弹出）；否则配方时间 * 配置倍率。"""
    base = TICK if bothSidesDone or recipeSeconds <= 0 else recipeSeconds
    return base if base <= TICK + EPS else roundToTick(base * times)


class Grill(object):
    """灶台各位置的两面进度：down 贴炉面、up 朝上（0..1）。"""

    def __init__(self, places=PLACES):
        self.places = places
        self._down = [0.0] * places
        self._up = [0.0] * places
        self._byHand = [False] * places
        self._turnedAt = [NEVER] * places
        self._sent = -1

    def down(self, place):
        return self._down[place]

    def up(self, place):
        return self._up[place]

    def byHand(self, place):
        """手放/手翻的：两面分开烤、等着翻。否则 FD 自己烤。"""
        return self._byHand[place]

    def turnedAt(self, place):
        return self._turnedAt[place]

    def waits(self, place):
        """贴炉面熟了、朝上面还生：什么都不动，等厨师翻。"""
        return self._byHand[place] and reached(self._down[place]) and not reached(self._up[place])

    def isDone(self, place):
        return reached(self._down[place]) and reached(self._up[place])

    def layByHand(self, place):
        self._byHand[place] = True

    def farmersDelightsWay(self, place):
        """回到 FD 自己的烤法，进度清零：右键放上去的食材，或者位置空了。"""
        self._byHand[place] = False
        self._down[place] = 0.0
        self._up[place] = 0.0

    def done(self, place):
        """两面都熟，这件已经变成成品、重新开始计。"""
        self._down[place] = 0.0
        self._up[place] = 0.0

    def grill(self, place, amount):
        self._down[place] = min(1.0, self._down[place] + amount)

    def grillThrough(self, place, amount):
        """单面食材从下往上烤透：上下一起熟，不会等翻。"""
        self._down[place] = min(1.0, self._down[place] + amount)
        self._up[place] = self._down[place]

    def step(self, place, dt, side, oneSided=False, lit=True):
        """烤 dt 秒，side 是一面的总时长(sideSeconds)。灶台没点着、或正等着翻面时不动。返回这件是否两面都熟了。"""
        if lit and not self.waits(place):
            if oneSided:
                self.grillThrough(place, 0.5 * dt / side)
            else:
                self.grill(place, dt / side)
        return self.isDone(place)

    def turn(self, place, now):
        self._down[place], self._up[place] = self._up[place], self._down[place]
        self._turnedAt[place] = now

    def has(self, place):
        """place 是不是本灶台的一个位置。位置序号来自客户端：越界、负数（Python 会绕回末尾）、非整数都不算。"""
        try:
            return 0 <= place < self.places and place == int(place)
        except (TypeError, ValueError):
            return False

    def canTurn(self, place, now, hasFood=True):
        """翻面是否被接受：位置有效，这里有能烤的食材(hasFood)，且离这件上一次翻够久。"""
        return self.has(place) and hasFood and now - self._turnedAt[int(place)] >= TURN_GAP - EPS

    def toss(self, place, now, hasFood=True):
        """厨师翻 place 上的这件（StoveCooking.turn）。FD 自己烤着的，翻一下就从此归厨师，从生开始重算。"""
        if not self.canTurn(place, now, hasFood):
            return False
        place = int(place)
        if not self._byHand[place]:
            self.farmersDelightsWay(place)
            self.layByHand(place)
        self.turn(place, now)
        return True

    def stateKey(self):
        key = 0
        for place in range(self.places):
            steps = floorInt(self._down[place] * STEPS) * (STEPS + 1) + floorInt(self._up[place] * STEPS)
            key = key * 31 + steps * 2 + (1 if self._byHand[place] else 0)
        return key

    def dueToSend(self):
        """要不要再告诉客户端：某件进度走了一格(1/16)，或手放标记变了。"""
        key = self.stateKey()
        if key == self._sent:
            return False
        self._sent = key
        return True
