# -*- coding: utf-8 -*-
"""PotLiquid - 厨锅汤面的状态：水量、水位、颜色缓动、沸腾强度与气泡 / 蒸汽速率（双端）

移植自 Hands-On Delight：station/PotLogic.java 的水量（39-43, 721-729）、client/PotBehavior.java 的 frame（水位 1181、
汤色缓动 1087-1103、沸腾 1205-1226），以及 Diegesis impl/client/fx/LiquidSim.java 对水位 / 颜色 / mottle / 边沿沸腾的缓动
（update 117-170、easeColor 544-553、boil 413-422）。颜色的计算在 PotLiquidColor.py，这里再导出一份，调用方只导入本模块。

用法（每帧、每口锅）：状态变了才调 retarget()（算目标色）；每帧调 step(dt, amount, mood, current)，然后读 level / fraction /
surfaceY()（水位）、color（渲染用的 ARGB）、brothColor / bubbleColor（粒子染色）、mottle / edgeBoil / agitation（0..1）、
emitBubbles / emitSteam / emitEdge（本帧该放几个粒子）、boilCount（本帧该起几个沸腾的水波，逐个调 impulse）。
时间是秒，长度是站点像素（锅底 y = 2，满水 y = 8.5，锅沿 y = 10）。随机数由调用方注入（rand() 返回 0..1）。
"""
from .Mth import clamp, lerp, roundInt
from .PotLiquidRates import (  # noqa: F401 - 再导出：调用方只导入 PotLiquid
    AGITATIONS, BROTH_BASE, BROTH_DEPTH, BROTH_FLOOR, BROTH_PER_STACK, BUBBLE_RATES, COLD, COOKING, EDGE_BOILS,
    EDGE_BUBBLE_RATES, HOT_WATER, RIM, SOUP, SOUP_BASE, SOUP_PER_SERVING, STEAM_RATES, TANK_CAPACITY, bubbleRate,
    edgeBubbleRate, potMood, steamRate, surfaceHeight, tankAmount)
from .PotLiquidColor import (  # noqa: F401 - 再导出：调用方只导入 PotLiquid
    BUBBLE_ALPHA, BUBBLE_WHITEN, DEFAULT_BIOME_WATER, FALLBACK, NEAR_PATH, NEAR_PATH_DEEP, FAR_PATH, FAR_PATH_DEEP, OOZE_ALPHA,
    OOZE_TAKES, POURED_SHARE, RAW_TINT, SOUP_ALPHA, SOUP_WAKE_CONTRAST, SOUP_WAKE_LIFE, STEAM_COLOR, SURFACE_PATH,
    WATER_ALPHA, WATER_WAKE_CONTRAST, WATER_WAKE_LIFE, argb, blend, brothTarget, bubbleTint, clearness, mixColors,
    opacity, toUnit, wakeLook, wallLook, waterColor)

LEVEL_RATE = 3.0             # PotBehavior.level 每秒追水量：lerp(min(1, dt * 3))（1181 行）
QUICK_FILL = 0.09            # 渲染的液面追水量的半衰期，秒（LiquidSim.java:45）
FULLEST = 0.995              # 画出来的液面最高到容量的这么多（LiquidRenderer.java:83）
FRACTION_SNAP = 0.0005       # 液面离目标近于此就贴上去（LiquidSim.java:151）
RECOLOUR_RATE = 4.0          # 汤色每秒追目标色的速度：blend(shown, target, min(1, dt * 4))（PotBehavior.java:308）
COLOR_HALF_LIFE = 0.18       # LiquidSim 里颜色通道再追一次的半衰期，秒（LiquidSim.java:549-552）
COLOR_SNAP_FRACTION = 0.002  # 液面低于此时颜色直接贴上去（LiquidSim.java:545）
MOTTLE_HALF_LIFE = 0.3       # mottle 追目标的半衰期，秒（LiquidSim.java:140）
EDGE_BOIL_HALF_LIFE = 0.5    # 边沿沸腾追目标的半衰期，秒（LiquidSim.java:142）
BOIL_RATE = 26.0             # 沸腾的水波：每秒 26 * agitation 个（LiquidSim.java:417）
BOIL_STRENGTH = 0.1          # 水波高度 0.1 + 0.28 * agitation，px（LiquidSim.java:420）
BOIL_STRENGTH_PER = 0.28


def approach(current, target, halfLife, dt):
    """按半衰期指数逼近目标（Diegesis Easing.approach）：halfLife 秒后剩余距离减半，halfLife <= 0 直接到位。"""
    if halfLife <= 0.0:
        return target
    return target + (current - target) * 0.5 ** (dt / halfLife)


class PotLiquid(object):
    """一口锅的汤面：缓动着的水位、颜色、mottle、边沿沸腾，以及按状态攒出来的粒子数。

    属性（只读）：level（PotBehavior.level 0..1，物品和勺子的高度用它）、fraction（渲染的液面 0..1）、color（渲染用 ARGB）、
    shown / brothColor / bubbleColor（粒子染色）、mottle、edgeBoil、agitation、turned（液面纹理转过的弧度）、wakeLife /
    wakeContrast（拖尾，来自最近一次 setTarget）、emitBubbles / emitSteam / emitEdge / boilCount（本帧的个数）。
    """

    def __init__(self, floor=BROTH_FLOOR, depth=BROTH_DEPTH, liquid=0):
        self.floor = floor
        self.depth = depth
        self.liquid = liquid
        self.level = 0.0                      # PotBehavior.level：新看到的锅从 0 慢慢涨上来（1181 行没有贴上去）
        self.fraction = 0.0
        self.target = waterColor(DEFAULT_BIOME_WATER, liquid)      # PotBehavior.brothTarget
        self.shown = self.target              # PotBehavior.brothShown
        self.known = False                    # PotBehavior.brothKnown：假 = 下一帧直接贴上目标色
        self.brothColor = self.target & 0xFFFFFF
        self.bubbleColor = bubbleTint(self.target)
        self.color = self.target
        self.mottleWanted = self.mottle = 0.0
        self.wakeLife, self.wakeContrast = wakeLook(0.0)
        self.edgeBoilWanted = self.edgeBoil = 0.0
        self.agitation = self.turned = 0.0
        self.bubbles = self.steam = self.edge = 0.0       # 攒着还没放的粒子
        self.emitBubbles = self.emitSteam = self.emitEdge = 0
        self.boilDebt = 0.0
        self.boilCount = 0
        self.primed = False                   # LiquidSim.primed：第一次 update 贴上水位和颜色
        self._ca = self._cr = self._cg = self._cb = 0.0   # LiquidSim.shownColor：A R G B 通道
        self._colorSet = False

    def restart(self):
        """下一次 step 直接显示当前的水位和颜色，不缓动。对应 LiquidSim.restart 与 `brothKnown = false`（PotBehavior.java:779-781）。"""
        self.primed = False
        self.known = False

    def snap(self, amount):
        """水位和颜色立刻到位（刚看到这口锅，不想看它从锅底涨上来）：amount 是水箱量 0..100。"""
        self.level = amount / 100.0
        self.fraction = min(1.0, amount / float(TANK_CAPACITY))
        self.restart()

    def setTarget(self, colour, mottle):
        """设定目标色（ARGB）与 mottle（0..1，等于煮熟程度）。对应 PotBehavior.colour 的末尾（1078-1083）。"""
        self.target = colour
        self.mottleWanted = mottle
        self.wakeLife, self.wakeContrast = wakeLook(mottle)

    def retarget(self, water, foodColors, meal, progress, dishBroth=None, poured=()):
        """算出目标色并设上：参数见 PotLiquidColor.brothTarget（liquid 用构造时给的）。状态变了才调。"""
        colour, mottle = brothTarget(water, foodColors, meal, progress, dishBroth, poured, self.liquid)
        self.setTarget(colour, mottle)

    def surfaceY(self):
        """物品、勺子站在的液面高度 y，px：floor + depth * level（PotBehavior.level，不是渲染的 fraction）。"""
        return self.floor + self.depth * self.level

    def drawnSurfaceY(self):
        """渲染出来的液面高度 y，px：floor + depth * min(fraction, 0.995)（LiquidRenderer.java:124）。"""
        return self.floor + self.depth * min(self.fraction, FULLEST)

    def step(self, dt, amount, mood=COLD, current=0.0, boil=1.0):
        """推进一帧。amount：水箱量 0..100（tankAmount）；mood：potMood 的结果；current：液面转速 rad/s（PotDrift.current）；
        boil：锅的沸腾倍率（厨锅 1）。对应 PotBehavior.frame 里的液面部分（1181, 1202-1226）与 LiquidSim.update。

        dt <= 0 或第一次 step：水位和颜色直接到位（LiquidSim.java:129-138，Java 也是这样）。
        """
        self.level = lerp(min(1.0, dt * LEVEL_RATE), self.level, amount / 100.0)
        self._showColour(dt)
        self.agitation = clamp(AGITATIONS[mood] * boil, 0.0, 1.0)
        self.edgeBoilWanted = min(1.0, EDGE_BOILS[mood] * boil)
        wanted = min(1.0, amount / float(TANK_CAPACITY))
        if not self.primed or dt <= 0.0:
            self.fraction = wanted
            self._setColor(self.shown)
            self.primed = True
            self.boilCount = 0
        else:
            self._ease(dt, wanted, current)
        self._emit(dt, mood, boil)

    def impulse(self, rand):
        """一个沸腾的水波：(u, v, 高度 px)，u、v 在 0.05..0.95 横跨水箱。LiquidSim.java:420。"""
        return (rand() * 0.9 + 0.05, rand() * 0.9 + 0.05, BOIL_STRENGTH + BOIL_STRENGTH_PER * self.agitation)

    def _showColour(self, dt):
        """PotBehavior.showColour（1087-1103）：汤色每秒追目标色 4 倍的距离，没变就不更新衍生色。"""
        was = self.shown
        if self.known:
            self.shown = blend(self.shown, self.target, min(1.0, dt * RECOLOUR_RATE))
        else:
            self.shown = self.target
        if self.known and was == self.shown:
            return
        self.known = True
        self.brothColor = self.shown & 0xFFFFFF
        self.bubbleColor = bubbleTint(self.shown)

    def _setColor(self, colour):
        self._ca = float((colour >> 24) & 0xFF)
        self._cr = float((colour >> 16) & 0xFF)
        self._cg = float((colour >> 8) & 0xFF)
        self._cb = float(colour & 0xFF)
        self._colorSet = True
        self.color = colour & 0xFFFFFFFF

    def _ease(self, dt, wanted, current):
        """LiquidSim.update 的缓动（140-157）：mottle、边沿沸腾、水位、颜色，再攒沸腾的水波。"""
        self.mottle = approach(self.mottle, self.mottleWanted, MOTTLE_HALF_LIFE, dt)
        self.edgeBoil = approach(self.edgeBoil, self.edgeBoilWanted, EDGE_BOIL_HALF_LIFE, dt)
        self.turned += current * dt
        self.fraction = approach(self.fraction, wanted, QUICK_FILL, dt)
        if abs(self.fraction - wanted) < FRACTION_SNAP:
            self.fraction = wanted
        if not self._colorSet or self.fraction < COLOR_SNAP_FRACTION:
            self._setColor(self.shown)
        else:
            shown = self.shown
            keep = 0.5 ** (dt / COLOR_HALF_LIFE)
            self._ca = ((shown >> 24) & 0xFF) + (self._ca - ((shown >> 24) & 0xFF)) * keep
            self._cr = ((shown >> 16) & 0xFF) + (self._cr - ((shown >> 16) & 0xFF)) * keep
            self._cg = ((shown >> 8) & 0xFF) + (self._cg - ((shown >> 8) & 0xFF)) * keep
            self._cb = (shown & 0xFF) + (self._cb - (shown & 0xFF)) * keep
            self.color = (roundInt(self._ca) << 24) | (roundInt(self._cr) << 16) | (roundInt(self._cg) << 8) | roundInt(self._cb)
        if self.agitation > 0.0 and self.fraction > 0.0:
            self.boilDebt += dt * self.agitation * BOIL_RATE
            self.boilCount = int(self.boilDebt)
            self.boilDebt -= self.boilCount
        else:
            self.boilCount = 0

    def _emit(self, dt, mood, boil):
        """攒粒子：每秒速率 * dt 累加，攒够 1 个就放出整数个（PotBehavior.java:1212-1226）。"""
        self.bubbles += dt * boil * BUBBLE_RATES[mood]
        self.emitBubbles = 0
        if self.bubbles >= 1.0:
            self.emitBubbles = int(self.bubbles)
            self.bubbles -= self.emitBubbles
        self.steam += dt * STEAM_RATES[mood]
        self.emitSteam = 0
        if self.steam >= 1.0:
            self.emitSteam = int(self.steam)
            self.steam -= self.emitSteam
        self.edge += dt * boil * EDGE_BUBBLE_RATES[mood]
        self.emitEdge = 0
        if self.edge >= 1.0:
            self.emitEdge = int(self.edge)
            self.edge -= self.emitEdge
