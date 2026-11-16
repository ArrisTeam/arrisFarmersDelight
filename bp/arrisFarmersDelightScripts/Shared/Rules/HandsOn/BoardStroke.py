# -*- coding: utf-8 -*-
"""BoardStroke - 刀以外的工具怎么落手：斧劈 / 削皮、镐砸、锹铲、锄撬、剪刀沿线剪（双端）

移植自 Hands-On Delight 的 client/ToolStroke.java（34-310 行）和 client/BoardBehavior.java 的 aim / workHeight / startStroke /
moveTool（913-1060）。点一下开始一个动作，动作到"接触"那一刻（impact）才把 chop 发给服务端，所以动作没落到活上之前什么也没切：
斧劈 0.19 / 0.42 秒、削皮 0.27 / 0.42、镐 0.19 / 0.40、锹 0.17 / 0.38、锄 0.20 / 0.40、剪刀 0.36 / 0.46（落点 / 全长，Cutting.STROKES）。
方块类的东西（原木、石头）在方块上任何地方落，没有线；食物按线（吸附同刀）。

HoD 的姿态是三维的（四元数把图标转到"握柄朝厨师的右手、扁面朝镜头"）。这里取同一套时刻和动作量（抬起角、杠杆角、推进量、
偏移、沿线剪的位置和一口一口的开合），姿态换成镜头平面里的二维版：工具立在板前朝着镜头，绕握柄在平面里摆；
平面再按 toolYaw 转到线的方向。位置是平面里的 (u 沿线、y 向上)，角度是度（roll，顺时针为正，同道具的 roll）。
"""
import math

from .BoardIcon import BLOCK_SIZE
from .Cutting import (SNIP_START, SNIP_TIME, SNIPS, STROKES, TOOL_CHOP, TOOL_CUT, TOOL_DIG, TOOL_PRY, TOOL_SMASH, TOOL_SNIP,
                      TOOL_STRIP)
from .Mth import clamp, lerp

SCALE = 0.45                 # ToolStroke.SCALE（51）：工具画多大（占 16 像素图标的比例，和刀一样）
BLOCK_MARGIN = 1.2           # BoardBehavior.BLOCK_MARGIN（208）：工具离方块边缘至少这么远
READY = 0.3                  # 悬着等点的时候头抬起的角度（弧度，chop / smash / pry 的"ready"）
# 图标上握在哪、哪一点干活（像素，从左上算；ToolStroke.Icon，119-123）和握柄朝哪（镜头平面里 x 往操作者左边长、y 向上：dir 的前两个分量）
ICONS = {
    TOOL_CHOP: ((3.0, 13.5), (7.0, 3.5), (-0.8, 0.7)),
    TOOL_STRIP: ((3.0, 13.5), (7.0, 3.5), (-1.0, 0.6)),
    TOOL_SMASH: ((3.0, 13.5), (6.0, 2.6), (-0.75, 0.75)),
    TOOL_DIG: ((3.0, 13.5), (13.6, 2.6), (-0.8, 0.7)),
    TOOL_PRY: ((3.0, 13.5), (7.2, 1.8), (-1.0, 0.8)),
    TOOL_SNIP: ((3.5, 11.5), (11.5, 2.5), (-1.0, 0.15)),
}


def ease(t):
    """ToolStroke.ease（372-375）：smoothstep。"""
    c = clamp(t, 0.0, 1.0)
    return c * c * (3.0 - 2.0 * c)


def timesOf(kind):
    """(落点, 全长)，秒。"""
    return STROKES[kind]


def swing(kind, age, ready, back, raised, hold):
    """ToolStroke.raise（298-310）：头抬起的角度（弧度）：悬着 ready -> 往后抬到 back（raised 秒）-> 加速落到 0（到 impact）-> 压着到 hold -> 抬回 ready。"""
    impact, length = timesOf(kind)
    if age < raised:
        return lerp(ease(age / raised), ready, back)
    if age < impact:
        t = (age - raised) / (impact - raised)
        return lerp(t * t, back, 0.0)
    if age < hold:
        return 0.0
    return lerp(ease((age - hold) / (length - hold)), 0.0, ready)


def motion(kind, age, top=0.0, snipFrom=-0.5, snipTo=0.5):
    """这个动作 age 秒（None = 悬着等点）时的各个量：{"raise": 头抬起的角度, "lever": 杠杆角度, "push": 沿工具推进的距离,
    "slide": 沿板面竖着挪的距离（削皮从上到下，top 是起点离板面多高）, "offset": (沿线, 高, 前后) 的小偏移, "along": 剪刀沿线走到哪, "bite": 剪刀张合的角度}。"""
    out = {"raise": 0.0, "lever": 0.0, "push": 0.0, "slide": 0.0, "offset": (0.0, 0.0, 0.0), "along": 0.0, "bite": 0.0}
    impact, length = timesOf(kind)
    waiting = age is None
    if kind == TOOL_CHOP:
        out["raise"] = READY if waiting else swing(kind, age, READY, 0.95, 0.13, 0.24)
    elif kind == TOOL_SMASH:
        out["raise"] = READY if waiting else swing(kind, age, READY, 1.05, 0.14, 0.22)
    elif kind == TOOL_STRIP:
        travel = top - 1.6
        out["slide"] = 1.0 if waiting else (lerp(ease(age / 0.07), 1.0, 0.0) if age < 0.07 else
                                            -travel * ease((age - 0.07) / (impact - 0.07)) if age < impact else
                                            lerp(ease((age - impact) / (length - impact)), -travel, 1.0))
    elif kind == TOOL_DIG:
        out["push"], out["lever"] = -1.5, 0.0
        if not waiting:
            if age < 0.1:
                out["push"] = lerp(ease(age / 0.1), -1.5, 2.0)
            elif age < 0.22:
                out["push"], out["lever"] = 2.0, 0.5 * ease((age - 0.1) / 0.12)
            else:
                t = ease((age - 0.22) / (length - 0.22))
                out["push"], out["lever"] = lerp(t, 2.0, -1.5), 0.5 * (1.0 - t)
    elif kind == TOOL_PRY:                                          # 钩住缝、往回撬、抬走（242-264）
        out["raise"] = 0.35
        if not waiting and age < 0.08:
            out["raise"] = lerp(ease(age / 0.08), 0.35, 0.0)
        elif not waiting and age < 0.24:
            t = ease((age - 0.08) / 0.16)
            out["raise"], out["lever"], out["offset"] = 0.0, 0.45 * t, (0.0, 0.5 * t, -0.4 * t)
        elif not waiting:
            t = ease((age - 0.24) / (length - 0.24))
            out["raise"], out["lever"], out["offset"] = 0.35 * t, 0.45 * (1.0 - t), (0.0, 0.5 * (1.0 - t), -0.4 * (1.0 - t))
    elif kind == TOOL_SNIP:
        out["along"], out["bite"] = _snip(age, snipFrom, snipTo)
    return out


def _snip(age, start, end):
    """snip（270-292）：先 SNIP_START 秒移到线头，再 SNIPS 口沿线剪到线尾（每口张合一次），落点之后退回原处。"""
    if age is None:
        return 0.0, 0.0
    impact, length = timesOf(TOOL_SNIP)
    if age < SNIP_START:
        return lerp(ease(age / SNIP_START), 0.0, start), 0.0
    if age < impact:
        snips = (age - SNIP_START) / SNIP_TIME
        done = min(SNIPS - 1, int(snips))
        part = snips - done
        return lerp((done + ease(part)) / SNIPS, start, end), math.sin(part * math.pi) * 0.3
    return lerp(ease((age - impact) / (length - impact)), end, 0.0), 0.0


def reachOf(kind):
    """握的地方离干活的点多远（像素，已乘 SCALE）：Icon.reach（141-143）。"""
    grip, point, _handle = ICONS[kind]
    return math.hypot(grip[0] - point[0], grip[1] - point[1]) * SCALE


def _turn(vector, angle, up):
    """二维里把 vector 转 angle 弧度，往让它的末端升高（up）或降低的那个方向转（ToolStroke.turn，340-344）。"""
    best = None
    for sign in (1.0, -1.0):
        c, s = math.cos(sign * angle), math.sin(sign * angle)
        turned = (vector[0] * c - vector[1] * s, vector[0] * s + vector[1] * c)
        if best is None or (turned[1] > best[1]) == up:
            best = turned
    return best


def pose(kind, age, target, top=0.0, snipFrom=-0.5, snipTo=0.5):
    """工具在 age 秒（None = 悬着）时的位置和朝向，二维：干活的点要落在 target（沿线 u，高 y）。
    返回 {"point": (u, y) 干活的点, "center": (u, y) 图标中心, "roll": 图标顺时针转多少度, "lean": (沿线, 高, 前后) 的小偏移}。"""
    grip, point, handle = ICONS[kind]
    length = math.hypot(*handle)
    hand = (handle[0] / length, handle[1] / length)
    reach = reachOf(kind)
    step = motion(kind, age, top, snipFrom, snipTo)
    target = (target[0] + step["along"], target[1] + step["slide"])
    if kind == TOOL_DIG:                                           # 锹顺着刃的方向推：刃朝 -handle
        target = (target[0] - hand[0] * step["push"], target[1] - hand[1] * step["push"])
    holding = (target[0] + hand[0] * reach, target[1] + hand[1] * reach)
    arm = (target[0] - holding[0], target[1] - holding[1])
    swung = _turn(arm, step["raise"], True)
    working = (holding[0] + swung[0], holding[1] + swung[1])
    back = _turn((-swung[0], -swung[1]), step["lever"], False)     # 杠杆：绕干活的点，把握柄压下去
    final = (back[0], back[1])
    # 图标里从干活的点到握的地方的方向 -> 要转到 final：图标坐标 u 往右、v 往下，镜头里 x 往操作者左边长，所以 x = -u；x、y 平面里的逆时针在屏幕上是顺时针，正好是 roll 的正方向
    mine = (-(grip[0] - point[0]), -(grip[1] - point[1]))
    turn = math.atan2(final[1], final[0]) - math.atan2(mine[1], mine[0])
    centre = (-(8.0 - point[0]) * SCALE, -(8.0 - point[1]) * SCALE)
    c, s = math.cos(turn), math.sin(turn)
    middle = (working[0] + centre[0] * c - centre[1] * s, working[1] + centre[0] * s + centre[1] * c)
    return {"point": working, "center": middle, "roll": math.degrees(turn), "lean": step["offset"]}


def towardsCook(angle):
    """一条线的角度，转半圈，让横在线上的工具的握柄朝厨师这边（towardsCook，995-997）。"""
    return angle + math.pi if math.cos(angle) < 0.0 else angle


def workHeight(kind, top):
    """工具干活的点在多高（workHeight，1000-1008）：锹插在土堆顶下面一点，削皮、撬贴着边。"""
    return top - {TOOL_DIG: 1.2, TOOL_STRIP: 0.3, TOOL_PRY: 0.1}.get(kind, 0.0)


def aimOnBlock(kind, x, z):
    """方块类的东西在方块上任何地方落（aim，965-978）：x 夹在方块里，削皮和铲贴着近侧，其余 z 也夹进方块里。返回 (x, z)。"""
    reach = BLOCK_SIZE / 2.0 - BLOCK_MARGIN
    if kind == TOOL_STRIP:
        z = -BLOCK_SIZE / 2.0 - 0.15
    elif kind == TOOL_DIG:
        z = -BLOCK_SIZE / 2.0 - 0.3
    else:
        z = clamp(z, -reach, reach)
    return (clamp(x, -reach, reach), z)


def snipRange(toolX, toolZ, toolYaw, cut, ends):
    """startStroke 里剪刀的起止（1022-1036）：从线的一头到另一头，尖朝前，不管剪刀原来在线上哪里。cut 是这一刀，ends 是虚线沿线的两端 (t0, t1)。
    返回 (起, 止)，沿线的位置（相对剪刀现在的位置）。"""
    here = (toolX - cut.x) * math.cos(cut.angle) + (toolZ - cut.z) * math.sin(cut.angle)
    sign = 1.0 if math.cos(toolYaw - cut.angle) >= 0.0 else -1.0
    a, b = sign * (ends[0] - here), sign * (ends[1] - here)
    start = min(a, b) + 0.4
    return (start, max(start, max(a, b) - 0.4))


class Run(object):
    """一次正在进行的动作（strokeAge / strokeSent / snipsHeard，moveTool 里的）。step 返回这一步发生的事：
    "snip"（前两口剪刀各响一声）、"impact"（接触：这时才发 chop）、"done"（动作完了）。"""

    def __init__(self, kind, mark):
        self.kind = kind
        self.mark = mark                  # 开始时吸附着的那一刀，-1 = 在线外，接触时只"敲"
        self.age = 0.0
        self.sent = False
        self.heard = 0

    def step(self, dt):
        events = []
        impact, length = timesOf(self.kind)
        self.age += dt
        if self.kind == TOOL_SNIP:
            bites = int((self.age - SNIP_START) / SNIP_TIME) + 1
            while self.heard < min(bites, SNIPS - 1):
                self.heard += 1
                events.append("snip")
        if not self.sent and self.age >= impact:
            self.sent = True
            events.append("impact")
        if self.age >= length:
            events.append("done")
        return events


def isStroke(kind):
    """这种动作是不是"点一下开始一个动作"的（不是刀）。"""
    return kind != TOOL_CUT and kind in ICONS
