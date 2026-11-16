# -*- coding: utf-8 -*-
"""PanToss - 颠锅：锅沿远的那头翘起来、整只锅猛地向厨师一拽，食物一块块飞起来在空中翻个面落回来（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java：常量 47-60 行，tossed（784-824）、flip（827-842）。每一帧谁都看得见：
- 锅（pan 节点）0.07 秒里绕 x 转 TILT * (0.7 + 0.3 * 力度) 度、往上 1.2 往厨师 0.9 像素一拽，再 0.2 秒落回原位；
- 每块食物（上面四块和下面四块，下面的晚两位）错开 0.03 秒各飞一回：飞 FLIGHT + FLIGHT_STRONG * 力度 秒，抬 (HEIGHT + HEIGHT_STRONG * 力度)
  * (0.85 + 0.3 * 随机) 像素（垫在下面的 0.8 倍），前半程转到竖起来（边朝镜头，x 转 90 度），到顶点一刹那换成另一面的样子、转到 -90 度，
  后半程转回 0；
- 食物落回锅里时再放一声下料、溅油星、冒油泡；飞起来的这一刻放一声挂灯（LANTERN_STEP）的"咣"。
上面那一面的熟度 tossedUp 一颠就换成颠之前贴锅那面（"翻过来了"），服务端的话来了也要等食物转到边朝镜头那一刻才换（lookHeldUntil）。
时间是秒，位置是锅里的像素（离锅心），转角是度。
"""
from functools import partial

from .PanLayout import PIECES, height, place, yaw

TILT = 11.0            # 锅的远沿翘起来多少度（SkilletBehavior 51）
JERK_UP = 1.2          # 锅一拽，抬高 / 往厨师挪多少像素（52-53）
JERK_BACK = 0.9
JERK_TIME = 0.07       # 一拽用多久（54）
SETTLE_TIME = 0.2      # 落回原位用多久（55）
FLIGHT = 0.32          # 食物飞多久，力度大时再多这么久（56-57）
FLIGHT_STRONG = 0.12
HEIGHT = 4.5           # 抬多高，力度大时再多这么高（58-59）
HEIGHT_STRONG = 6.0
STAGGER = 0.03         # 各块错开多久（60）
IN_AIR = JERK_TIME + FLIGHT + FLIGHT_STRONG                      # 508 行：这段时间里油泡油星都停着、不报"该翻了"
TOSSING = IN_AIR + STAGGER * PIECES * 2                          # 337 行：这段时间里别的动作不碰食物


def tossed(show, strength):
    """这一颠谁都看得见（tossed）：锅一拽、食物飞起来翻面、落回来。"""
    show.tossedAt = show.clock
    pan = show.nodes["pan"]
    pan.rotateTo(TILT * (0.7 + 0.3 * strength), 0.0, 0.0, JERK_TIME)
    pan.moveTo(0.0, JERK_UP, JERK_BACK, JERK_TIME)
    show.steps.after(JERK_TIME, partial(settle, pan, SETTLE_TIME))
    flight = FLIGHT + FLIGHT_STRONG * strength
    rise = HEIGHT + HEIGHT_STRONG * strength
    show.tossedUp = show.down                       # 颠之前贴锅的那面，现在朝上
    show.lookHeldUntil = show.clock + JERK_TIME * 0.6 + flight / 2.0
    for index in range(PIECES):
        for under in (False, True):
            node = show.nodes[("under_%d" if under else "piece_%d") % index]
            if not node.visible:
                continue
            delay = JERK_TIME * 0.6 + STAGGER * (index + (2 if under else 0))
            high = rise * (0.85 + 0.3 * show.rand()) * (0.8 if under else 1.0)
            show.steps.after(delay, partial(flip, show, node, index, under, flight, high))
    show.sound("lantern_step", 0.35, 0.8 + 0.2 * strength)
    show.steps.after(JERK_TIME * 0.6 + flight, partial(comesDown, show))


def settle(pan, seconds):
    """锅回到原位。"""
    pan.rotateTo(0.0, 0.0, 0.0, seconds)
    pan.moveTo(0.0, 0.0, 0.0, seconds)


def flip(show, node, index, under, flight, rise):
    """一块飞起来翻个面（flip）：飞到顶、转到边朝镜头、换另一面的样子、转完落下。"""
    at = place(index, show.shownPieces)
    base = yaw(index, under)
    spin = (show.rand() * 2.0 - 1.0) * 25.0
    node.hopTo(at[0], height(under, show.shownUnders), at[1], rise, flight)
    node.rotateTo(90.0, base + spin * 0.5, 0.0, flight / 2.0)
    show.steps.after(flight / 2.0, partial(turnedOver, show, node, index, under, base, spin, flight))


def turnedOver(show, node, index, under, base, spin, flight):
    """转到边朝镜头：这一刻换成另一面的样子（只看最前面那块），再转完。"""
    if not under and index == 0:
        show.lookHeldUntil = 0.0
        show.refresh()
    node.rotateTo(-90.0, base + spin * 0.5, 0.0, 0.0)
    node.rotateTo(0.0, base, 0.0, flight / 2.0)


def comesDown(show):
    """食物落回锅里：下料声、油星、油泡（812-823）。"""
    show.sound("add_food", 0.55, 0.95 + show.rand() * 0.15)
    for _ in range(10):
        show.heat.spitOne(4.0, 4.0, 8.0, 6.0)
    for _ in range(8):
        show.particles("oil_pop", show.heat.roundFood(), (0.0, 0.6, 0.0), 0.1, 1, 0)
