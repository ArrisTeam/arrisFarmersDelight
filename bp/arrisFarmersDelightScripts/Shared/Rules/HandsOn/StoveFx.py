# -*- coding: utf-8 -*-
"""StoveFx - 烤架上的热气、蒸汽、烟、嗞嗞声和各个动作的声音与粒子：什么时候放、放在哪、多大声（双端，纯计算）

移植自 Hands-On Delight：client/StoveBehavior.java 的 heat（257-306）、hitsTheGrill（309-312）、onPiece / roundPiece / randomly（319-332）、
turned 里的声音与蒸汽（394-398）、onEffect 里 refused / grilled（482-497）。放上去 / 取下的声音（JE 是灯笼的放置声和拾取声，
480-481、516 行）本移植由服务端的世界广播顶替（Compat/Diegesis/GrillLogic.py），所有人都听得到，这里不放。
烤架点着时：架子上空一阵阵热浪；每件在烤的（贴烤架那面还没熟）冒一点蒸汽、轻轻嗞；贴烤架那面熟了等着翻的冒烟、嗞得更尖，
告诉厨师该翻了；烤好的只是躺着。粒子和声音在这里只是"一条条要放的东西"，客户端拿去放（Compat/Diegesis/GrillFx.py）。
位置是相对一件自己的落点（place 是序号）或相对烤架中心（place 是 None）的偏移，px；速度 px 每秒；color 是 ARGB（0 = 粒子自己的颜色）。
随机数由调用方给（rand() 返回 0..1），所以测试可以定下来。
"""
import math

SHIMMER_RATE = 1.6           # 热浪每秒几个（StoveBehavior.java:55）
VAPOUR_RATE = 0.9            # 每件在烤的每秒冒几口蒸汽（56）
SMOKE_RATE = 2.5             # 每件等着翻的每秒冒几口烟（57）
SIZZLE_TIME = 1.6            # 在烤的嗞一声隔多久（58）；等着翻的更勤（59）
WAITING_SIZZLE_TIME = 1.1
SHIMMER_REACH = 5.5          # 热浪在烤架中心周围 ±5.5 px 里冒（270 行）
PIECE_JITTER = 1.2           # 蒸汽落在件上，离它的中心 ±1.2 px、高 0.6 px（320 行）
PIECE_HEIGHT = 0.6
EDGE = 5.0                   # 烟从件的边上冒：半径 = 件边长 / 2 * (0.8 ~ 1.1)，高 0.15（325-327 行）
EDGE_LOW, EDGE_SPAN, EDGE_HEIGHT = 0.8, 0.3, 0.15
WHITE_40, WHITE_50, WHITE_60 = 0x40FFFFFF, 0x50FFFFFF, 0x60FFFFFF
GOLD = 0xFFFFE9A0            # 烤好了的闪光（494-495 行）


class Spawn(object):
    """要放一阵粒子：kind 是 heat / steam / smoke / glint；place 是哪一件（None = 烤架中心），offset 是相对它的位置。"""

    __slots__ = ("kind", "place", "offset", "velocity", "spread", "count", "color")

    def __init__(self, kind, place, offset, velocity, spread, count, color):
        self.kind, self.place, self.offset, self.velocity = kind, place, offset, velocity
        self.spread, self.count, self.color = spread, count, color

    def __repr__(self):
        return "Spawn(%s, %r, %r, %r, %r, %r, %#x)" % (self.kind, self.place, self.offset, self.velocity, self.spread, self.count,
                                                         self.color)


class Sound(object):
    """要放一声：name 是 JE 的叫法（sizzle / add_food / lantern_step / lantern_place / lantern_hit / item_pickup）。"""

    __slots__ = ("name", "volume", "pitch")

    def __init__(self, name, volume, pitch):
        self.name, self.volume, self.pitch = name, volume, pitch

    def __repr__(self):
        return "Sound(%s, %r, %r)" % (self.name, self.volume, self.pitch)


def _randomly(rand, most):
    """-most .. most（StoveBehavior.randomly）。"""
    return (rand() * 2.0 - 1.0) * most


def _onPiece(rand):
    """落在一件上的一点：中心 ±1.2 px，高 0.6 px（onPiece）。"""
    x = _randomly(rand, PIECE_JITTER)
    return (x, PIECE_HEIGHT, _randomly(rand, PIECE_JITTER))


def _roundPiece(rand):
    """件边上的一点，烟从这里冒出来（roundPiece）：随机角度，离中心 2.5 * (0.8 + 0.3 * r) px。"""
    angle = rand() * 2.0 * math.pi
    reach = EDGE * 0.5 * (EDGE_LOW + EDGE_SPAN * rand())
    return (math.cos(angle) * reach, EDGE_HEIGHT, math.sin(angle) * reach)


class Heat(object):
    """点着的烤架每一帧的热气日程（heat）：热浪、蒸汽、烟、嗞嗞声各有一个累计的计数。"""

    def __init__(self, rand):
        self.rand = rand
        self.shimmer = self.vapour = self.smoke = self.sizzle = 0.0

    def idle(self):
        """烤架没点着：嗞嗞声的计时清零（点着的才有）。"""
        self.sizzle = 0.0

    def step(self, dt, cooking, waiting):
        """前进 dt 秒。cooking / waiting 是在烤的、等着翻的件的位置序号；返回这一步要放的 [Spawn / Sound]。"""
        rand, out = self.rand, []
        self.shimmer += dt * SHIMMER_RATE
        while self.shimmer >= 1.0:
            self.shimmer -= 1.0
            x = _randomly(rand, SHIMMER_REACH)
            out.append(Spawn("heat", None, (x, 2.0 + rand() * 2.0, _randomly(rand, SHIMMER_REACH)), (0.0, 3.0, 0.0), 0.3, 1, 0))
        self.vapour += dt * VAPOUR_RATE * len(cooking)
        while self.vapour >= 1.0 and cooking:
            self.vapour -= 1.0
            place = cooking[int(rand() * len(cooking))]
            where = _onPiece(rand)
            out.append(Spawn("steam", place, where, (_randomly(rand, 0.4), 2.2, _randomly(rand, 0.4)), 0.4, 1, WHITE_40))
        self.smoke += dt * SMOKE_RATE * len(waiting)
        while self.smoke >= 1.0 and waiting:
            self.smoke -= 1.0
            place = waiting[int(rand() * len(waiting))]
            where = _roundPiece(rand)
            out.append(Spawn("smoke", place, where, (_randomly(rand, 0.5), 4.0, _randomly(rand, 0.5)), 0.3, 1, 0))
        if not cooking and not waiting:
            self.sizzle = 0.0
            return out
        self.sizzle -= dt
        if self.sizzle <= 0.0:
            wants = bool(waiting)
            self.sizzle = WAITING_SIZZLE_TIME if wants else SIZZLE_TIME
            out.append(Sound("sizzle", 0.3 if wants else 0.15, (1.15 if wants else 1.0) + rand() * 0.1))
        return out


# ---------------------------------------------------------------- 各个动作

def hitsTheGrill(place, rand):
    """一件落到热的烤架上：嘶地冒两口汽、下料的一声（hitsTheGrill，309-312）。"""
    return [Spawn("steam", place, _onPiece(rand), (0.0, 3.0, 0.0), 1.2, 2, WHITE_50),
            Sound("add_food", 0.45, 1.05 + rand() * 0.1)]


def turnStarts():
    """翻面一起跳：哐的一小声（394 行）。"""
    return [Sound("lantern_step", 0.25, 1.3)]


def turnLands(place, rand):
    """翻过来落回烤架：下料的一声、冒两口汽（395-398 行）。"""
    return [Sound("add_food", 0.5, 1.0 + rand() * 0.15),
            Spawn("steam", place, _onPiece(rand), (0.0, 3.0, 0.0), 0.8, 2, WHITE_50)]


def grilled(place, rand):
    """一件两面都烤好了：一团蒸汽、三点金光、叮的一声（493-496 行）。"""
    return [Spawn("steam", place, _onPiece(rand), (0.0, 3.0, 0.0), 1.5, 3, WHITE_60),
            Spawn("glint", place, _onPiece(rand), (0.0, 2.0, 0.0), 1.5, 3, GOLD),
            Sound("item_pickup", 0.3, 1.3)]


def refused():
    """放不上去：弹回来时的一声（490 行）。"""
    return [Sound("lantern_hit", 0.4, 1.3)]
