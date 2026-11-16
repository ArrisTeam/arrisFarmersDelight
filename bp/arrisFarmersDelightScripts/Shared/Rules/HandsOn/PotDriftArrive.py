# -*- coding: utf-8 -*-
"""PotDriftArrive - 往锅里放料时料的到达：错开出发、飞入的弧线、落水事件（双端）

移植自 Hands-On Delight：client/PotBehavior.java 的 refresh 里到达的那段（741-756）、arrivals（850-870）、splashIn（786-798），
和 drift 里飞行的那段（1447-1456）。飞入的起点来自 FromPlayer.java（玩家在屏幕下方的那一点投到液面上方），由调用方算好传进来；
没有起点（旁观的人）就从锅心正上方落下。时间是秒（Java 用秒），长度是站点像素，相对锅心。

一次放进一件：直接落水（事件 LANDED），料就在它的位置。一次放进好几件（点书上的菜、Shift 分堆）：按放进的顺序每件晚 0.16 秒出发，
飞 0.4 秒，落水时同样发 LANDED。会沉下去的东西（倒的液体、打的蛋、化掉的糖）不飘，轮到它时发 POUR，由调用方接着演手上的动作。
事件是 (种类, 格子序号) 的元组，攒在调用方给的 list 里。
"""
import math

from .Mth import lerp

ARRIVE_STAGGER = 0.16        # 一起放进的几件，每件晚这么久出发，秒（PotBehavior.java:207）
ARRIVE_TIME = 0.4            # 飞行时间，秒（208 行）
ARRIVE_FROM = 9.0            # 起点比落点高这么多，px（209 行）
ARRIVE_ARC = 4.0             # 弧线中间再高这么多，px（210 行）
ARRIVE_ROLL = 180.0          # 飞行中额外翻的角度，度，落地前翻完（1455 行）
EVENT_LANDED = 1             # 一件浮着的料落水：放水波、溅水、噗的一声（splashIn）
EVENT_POUR = 2               # 一件会沉的东西轮到了：开始演倒 / 打 / 撒（goesIn）
LAND_RIPPLE = 0.5            # 落水在锅心起的水波高度，px（PotBehavior.java:792）
LAND_SPLASH = 5              # 落水溅起的水花个数，染成汤色（793 行）
PLOP_VOLUME = 0.5            # 噗的音量；音调 0.92 + 0.03 * 格子序号（794 行）
PLOP_PITCH = 0.92
PLOP_PITCH_STEP = 0.03
ADD_FOOD_VOLUME = 0.16       # 锅在烧着时再加一声下料的嗞，音调 0.8（795-797 行）
ADD_FOOD_PITCH = 0.8


def landingEffects(slot, heated):
    """一件料落水该有的效果 (水波高度 px, 水花个数, 噗的音量, 噗的音调, 下料声音量（没烧 = 0）, 下料声音调)。对应 splashIn（786-798）。"""
    return (LAND_RIPPLE, LAND_SPLASH, PLOP_VOLUME, PLOP_PITCH + PLOP_PITCH_STEP * slot,
            ADD_FOOD_VOLUME if heated else 0.0, ADD_FOOD_PITCH)


class Arrivals(object):
    """每个格子的到达钟：age < 0 在等轮到自己，0..0.4 在飞，到 0.4 落水（Java 的 arriveAge / arriveX / arriveZ，NaN = 不在到达中）。"""

    def __init__(self, slots):
        self.slots = slots
        self.arriving = [False] * slots
        self.age = [0.0] * slots
        self.startX = [0.0] * slots
        self.startZ = [0.0] * slots
        self.sinking = [False] * slots
        self.again = [0] * slots          # 手忙着时又放进来的次数：手走完再来一次（PotBehavior 的 again）
        self.staged = [False] * slots     # 这格是一次放进好几件里会沉的一件：手从 startX / startZ 出发（FromPlayer），轮到它时 takeStart 取一次

    def clear(self, slot):
        """这格空了（或安静地重画）：不再到达，排着队的手也不来了（PotBehavior.java:725-727、734）。"""
        self.arriving[slot] = False
        self.again[slot] = 0
        self.staged[slot] = False

    def more(self, slot, events, busy):
        """这格里又放进了同种的、会沉的东西（个数涨了）：手还忙着（busy）、或这一格还在等轮到，就记一次，手走完再来一次；否则马上来一次
        （PotBehavior.java:757-763 的 again / splashIn）。一次放进来多个算一次手；手忙着时又放了几回就排几次，不丢。"""
        if busy or self.waiting(slot):
            self.again[slot] += 1
        else:
            events.append((EVENT_POUR, slot))

    def handDone(self, slot, events):
        """这格的手走完了：排着队的还有就再来一次（PotBehavior.java:1428-1431）。"""
        if self.again[slot] > 0:
            self.again[slot] -= 1
            events.append((EVENT_POUR, slot))

    def takeStart(self, slot):
        """这格的手从哪出发（相对锅心的 x、z）：一次放进好几件、轮到它那一刻的 FromPlayer 出发点；放进一件的、第一件（走 splashIn 的）、
        同一格再来一只手的返回 None（手从光标来）。只给一次。"""
        if not self.staged[slot]:
            return None
        self.staged[slot] = False
        return (self.startX[slot], self.startZ[slot])

    def waiting(self, slot):
        """还在等轮到自己：Java 这时料已经画在圈里的位置上，只是不能点（setEnabled(false)）。"""
        return self.arriving[slot] and self.age[slot] < 0.0

    def flying(self, slot):
        """正在飞入（age >= 0）：位置要用 blend 改。"""
        return self.arriving[slot] and self.age[slot] >= 0.0

    def begin(self, slotList, events, starts=None, sinking=None):
        """一次放进了 slotList 这几格（按放进的顺序）。对应 PotBehavior.refresh（741-756）。

        starts：每件的起点 (x, z)，相对锅心的 px，None 或其中的 None = 锅心正上方；sinking：每件是不是会沉的东西。
        只有一件：马上发 LANDED（会沉的发 POUR）进 events；多件：开始错开计时，什么都不发。
        多件里会沉的轮到时发 POUR，手从哪出发读 startX / startZ[slot]（相对锅心的 px，在液面上方 ARRIVE_FROM 高处）。
        """
        count = len(slotList)
        for k in range(count):
            slot = slotList[k]
            sinks = bool(sinking[k]) if sinking is not None else False
            if count > 1:
                start = starts[k] if starts is not None else None
                self.arriving[slot] = True
                self.age[slot] = -k * ARRIVE_STAGGER
                self.startX[slot] = start[0] if start is not None else 0.0
                self.startZ[slot] = start[1] if start is not None else 0.0
                self.sinking[slot] = sinks
                self.staged[slot] = sinks
            else:
                self.arriving[slot] = False
                self.staged[slot] = False
                events.append((EVENT_POUR if sinks else EVENT_LANDED, slot))

    def advance(self, dt, present, events):
        """推进计时（PotBehavior.arrivals，850-870）：轮到会沉的发 POUR，飞满 0.4 秒的发 LANDED。

        present[i] 为假的浮着的料（格子被取空了）直接取消，不发事件；会沉的由调用方 clear。
        """
        for i in range(self.slots):
            if not self.arriving[i]:
                continue
            if not self.sinking[i] and not present[i]:
                self.arriving[i] = False
                continue
            before = self.age[i]
            self.age[i] = before + dt
            if before < 0.0 and self.age[i] >= 0.0 and self.sinking[i]:
                self.arriving[i] = False
                events.append((EVENT_POUR, i))
            elif self.age[i] >= ARRIVE_TIME:
                self.arriving[i] = False
                if self.sinking[i]:
                    # 第一件（错开 0 秒）：Java 里 -0.0 不小于 0，不走"轮到了"那一支，飞满 0.4 秒后走 splashIn，会沉的也是一只手，从光标来（786-790）
                    self.staged[i] = False
                    events.append((EVENT_POUR, i))
                else:
                    events.append((EVENT_LANDED, i))

    def blend(self, slot, x, y, z, out):
        """把落点 (x, y, z)（相对锅心的 x、z，y 是落点的高度）换成飞行中此刻的位置，写进 out[0..3] = (x, y, z, 额外的俯仰角)。

        t = min(1, age / 0.4)，eased = smoothstep(t)：x、z 按 eased 从起点滑向落点，y 从高 9 px 的地方按 t 落下，中间再拱高 4 sin(pi t)，
        额外的翻转 (1 - eased) * 180 度加在俯仰上。对应 PotBehavior.java:1450-1455。
        """
        t = min(1.0, self.age[slot] / ARRIVE_TIME)
        eased = t * t * (3.0 - 2.0 * t)
        out[0] = lerp(eased, self.startX[slot], x)
        out[1] = lerp(t, y + ARRIVE_FROM, y) + ARRIVE_ARC * math.sin(t * math.pi)
        out[2] = lerp(eased, self.startZ[slot], z)
        out[3] = (1.0 - eased) * ARRIVE_ROLL
        return out
