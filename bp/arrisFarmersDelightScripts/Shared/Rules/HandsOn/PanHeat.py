# -*- coding: utf-8 -*-
"""PanHeat - 煎着的锅怎么冒热气、溅油星、响滋滋、提醒该翻面；熟好的食物一鼓一鼓亮着（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java：常量 77-114 行，frying（504-588）、wantsTurning（594-616）、readyGlow（628-653）、
swell（656-663）、calm / outlineHandle（667-675）、hitsTheFat（678-692）、roundFood / onFood（695-708）。
锅给的信息全靠声音和粒子，不画进度条：锅热着，上面一股热浪；有食物，油在它四周冒小泡、油星溅开、淌水汽；贴锅的那面熟了，
底下冒烟、滋滋声变尖、锅柄描边、油偶尔噗一声（该翻面了）；整锅熟了，油安静下来，食物一鼓一鼓、闪一闪、冒一缕汽，不出声。
每个量是"每秒几个"，攒够一个放一个。位置是场景像素；粒子和声音都不直接放，攒成事件交给客户端（show.particles / show.sound）。
"""
import math
from functools import partial

from .Mth import TWO_PI, floorInt
from .PanLayout import EDGE, FLOOR, PIECES, height, place, size

SEETHE_RATE = 14.0          # 每秒冒几个油泡（SkilletBehavior 77）
SPIT_RATE = 5.0             # 油星
VAPOUR_RATE = 1.6           # 水汽
SMOKE_RATE = 6.0            # 贴锅面熟了之后的烟
SHIMMER_RATE = 1.2          # 热浪；空锅更多
SHIMMER_EMPTY_RATE = 2.4
WAITING_SIZZLE = 1.3        # 等着翻面时滋滋声的间隔（秒，94）
FRY_VOICE = 1.0             # 煎着时滋滋声的间隔，越熟越密（101）
WAITING_POP = 1.4           # 等着翻面时油噗的间隔（102）
POP_HOP = 0.6               # "该翻了"那一下食物跳起来多高、多久（103-104）
POP_TIME = 0.18
READY_SWELL = 0.05          # 熟好的食物胀这么多再缩回来（111）
READY_BEAT = 1.3            # 一鼓的时间（112）
READY_GLINTS = 2            # 每鼓一下闪几颗（113）
WISP_RATE = 1.4             # 熟好的食物上每秒冒几缕汽（114）
GLINT_COLOR = 0xFFFFE9A0


class Heat(object):
    def __init__(self, show):
        self.show = show
        self.spit = self.seethe = self.vapour = self.shimmer = self.smoke = self.sizzle = self.wisp = 0.0
        self.fryVoice = self.waitingPop = 0.0
        self.wasWaiting = False
        self.readySince = None

    # ---- 取点 ----

    def _randomly(self, most):
        return (self.show.rand() * 2.0 - 1.0) * most

    def roundFood(self):
        """锅底上紧挨着某块食物边上的一点，油在这里冒泡、油星从这里飞（695-701）。"""
        show = self.show
        count = max(1, show.shownPieces)
        at = place(min(count - 1, int(show.rand() * count)), count)
        angle = show.rand() * TWO_PI
        reach = size(show.shownPieces) * EDGE * (0.85 + 0.3 * show.rand())
        return (8.0 + at[0] + math.cos(angle) * reach, FLOOR + 0.15, 8.0 + at[1] + math.sin(angle) * reach)

    def onFood(self):
        """某块食物上的一点（704-708）。"""
        show = self.show
        count = max(1, show.shownPieces)
        at = place(min(count - 1, int(show.rand() * count)), count)
        spread = size(show.shownPieces) * 0.35
        return (8.0 + at[0] + self._randomly(spread), 1.6, 8.0 + at[1] + self._randomly(spread))

    # ---- 每帧 ----

    def calm(self):
        """没有东西等着翻：除了光标，锅柄不描边（667-670）。"""
        self.wasWaiting = False
        self.show.waitOutline = False

    def frying(self, dt):
        """frying（504-588）：返回 None。"""
        show = self.show
        hot, food = show.heated, show.shown is not None
        inAir = show.inAir()
        show.oil.frame(dt, hot and food)
        if not hot:
            self.sizzle = 0.0
            self.calm()
            return
        self.shimmer += dt * (SHIMMER_RATE if food else SHIMMER_EMPTY_RATE)
        while self.shimmer >= 1.0:
            self.shimmer -= 1.0
            show.particles("heat", (8.0 + self._randomly(4.5), FLOOR + 2.5 + show.rand() * 2.0, 8.0 + self._randomly(4.5)), (0.0, 3.0, 0.0), 0.3, 1, 0)
        if not food:
            self.sizzle = 0.0
            self.calm()
            return
        done = show.isShownDone()
        fullness = (0.5 + 0.5 * min(1.0, show.shownPieces / float(PIECES))) * (0.3 if done else 1.0)
        if not inAir:
            self.seethe += dt * SEETHE_RATE * fullness
            while self.seethe >= 1.0:
                self.seethe -= 1.0
                show.particles("oil_pop", self.roundFood(), (0.0, 0.6, 0.0), 0.1, 1, 0)
        if done:
            self.sizzle = 0.0
            self.calm()
            return
        self.spit += dt * SPIT_RATE * fullness
        while self.spit >= 1.0:
            self.spit -= 1.0
            self.spitOne(2.5, 3.5, 7.0, 6.0)
        waits = show.byHand and show.down >= 1.0 and show.up < 1.0 and show.tossedUp is None
        if waits and not self.wasWaiting and not inAir:
            self.wantsTurning()
        self.wasWaiting = waits
        show.waitOutline = waits and not inAir
        if not waits:
            self._browning(dt, fullness, inAir)
            return
        self.smoke += dt * SMOKE_RATE * fullness
        while self.smoke >= 1.0:
            self.smoke -= 1.0
            show.particles("pan_smoke", self.roundFood(), (self._randomly(0.5), 4.0, self._randomly(0.5)), 0.3, 1, 0)
        self.sizzle -= dt
        if self.sizzle <= 0.0:
            self.sizzle = WAITING_SIZZLE
            show.sound("sizzle", 0.3, 1.15 + show.rand() * 0.1)
        self.waitingPop -= dt
        if self.waitingPop <= 0.0:
            self.waitingPop = WAITING_POP * (0.8 + 0.4 * show.rand())
            show.sound("lava_pop", 0.18, 1.4 + show.rand() * 0.3)

    def spitOne(self, near, out, lift, lifted):
        """一颗油星：从食物边上往四周、往上溅开（546-547）。"""
        show = self.show
        angle = show.rand() * TWO_PI
        reach = near + show.rand() * out
        show.particles("fat", self.roundFood(), (math.cos(angle) * reach, lift + show.rand() * lifted, math.sin(angle) * reach), 0.1, 1, 0)

    def _browning(self, dt, fullness, inAir):
        """贴锅面还在煎：滋滋声随熟度变响变高变密，淌水汽（556-571）。"""
        show = self.show
        self.sizzle = 0.0
        down = min(1.0, max(0.0, show.down))
        self.fryVoice -= dt
        if self.fryVoice <= 0.0 and not inAir:
            self.fryVoice = FRY_VOICE * (1.0 - 0.3 * down)
            show.sound("sizzle", 0.12 + 0.28 * down, 0.85 + 0.3 * down + show.rand() * 0.05)
        self.vapour += dt * VAPOUR_RATE * fullness
        while self.vapour >= 1.0:
            self.vapour -= 1.0
            show.particles("steam", self.onFood(), (self._randomly(0.4), 2.2, self._randomly(0.4)), 0.4, 1, 0x40FFFFFF)

    def wantsTurning(self):
        """贴锅这面熟了（594-616）：油噗两声，食物各跳一下，溅一把油星，一次。"""
        show = self.show
        self.waitingPop = WAITING_POP
        show.sound("lava_pop", 0.4, 1.3)
        show.steps.after(0.09, partial(show.sound, "lava_pop", 0.35, 1.55))
        for _ in range(8):
            self.spitOne(3.0, 3.0, 8.0, 5.0)
        for i in range(show.shownPieces):
            at = place(i, show.shownPieces)
            for under in (False, True):
                if show.landings.landing(i, under) or (under and i >= show.shownUnders):
                    continue
                node = show.nodes[("under_%d" if under else "piece_%d") % i]
                if not node.moving:
                    show.steps.after(i * 0.04, partial(node.hopTo, at[0], height(under, show.shownUnders), at[1], POP_HOP, POP_TIME))

    def readyGlow(self, dt):
        """熟好的食物一直亮着，告诉人"好了"（628-653）：每块一起鼓一下再缩回来，每鼓一下闪两颗，一路冒汽。不出声（噗是"翻我"）。"""
        show = self.show
        if show.shown is None or show.shownPieces == 0 or not show.isShownDone():
            if self.readySince is not None:
                self.readySince = None
                self.swell(1.0)
            return
        if self.readySince is None:
            self.readySince = show.clock
        before = (show.clock - dt - self.readySince) / READY_BEAT
        beat = (show.clock - self.readySince) / READY_BEAT
        self.swell(1.0 + READY_SWELL * (0.5 - 0.5 * math.cos(beat * TWO_PI)))
        if floorInt(beat - 0.5) > floorInt(before - 0.5) and not show.tossing():
            for _ in range(READY_GLINTS):
                show.particles("glint", self.onFood(), (0.0, 0.8, 0.0), 0.4, 1, GLINT_COLOR)
        self.wisp += dt * WISP_RATE
        while self.wisp >= 1.0:
            self.wisp -= 1.0
            show.particles("steam", self.onFood(), (self._randomly(0.2), 1.4, self._randomly(0.2)), 0.3, 1, 0x30FFFFFF)

    def swell(self, factor):
        """躺在锅里的每块按 factor 的大小；正在落、在飞的按自己的（656-663）。"""
        show = self.show
        for i in range(PIECES):
            for under in (False, True):
                lying = not show.landings.landing(i, under) and not show.waitingIn[PIECES + i if under else i] and not show.tossing()
                show.nodes[("under_%d" if under else "piece_%d") % i].scaleTo(factor if lying else 1.0, 0.0)

    def hitsTheFat(self):
        """食物落进热锅：油泡翻起来，溅油星，冒汽（678-692）。"""
        show = self.show
        if show.shown is None:
            return
        for _ in range(12):
            show.particles("oil_pop", self.roundFood(), (0.0, 0.6, 0.0), 0.1, 1, 0)
        for _ in range(6):
            self.spitOne(3.0, 3.0, 8.0, 5.0)
        show.particles("steam", self.onFood(), (0.0, 3.0, 0.0), 1.5, 3, 0x50FFFFFF)
