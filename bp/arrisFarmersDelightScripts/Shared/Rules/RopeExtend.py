# -*- coding: utf-8 -*-
"""RopeExtend - 拿着绳子点绳子：新的一节放在哪（双端，纯规则）

照 JE 的 RopeItem.updatePlacementContext（FD 1.3.4）。拿着绳子点方块时，"点到的格子"是：点到的方块能被顶替就是它自己
（绳子对手里的绳子算能被顶替：RopeBlock.canBeReplaced），否则是点到的面外侧那一格（这一种只在潜行时认，见 startRope）。
这一格不是绳子：和这里无关，照常放。
是绳子：不潜行一律往下、潜行照点到的面，从它那个方向的下一格走起——
- 碰到不是绳子的一格：是水以外的液体（岩浆）不放；能被顶替（空气、水、草……）就放在这一格；别的（实心方块、没加载的格子）不放；
- 还是绳子：往下就接着走，往别的方向不放；
- 走到世界最下面还没找到，不放。
"""
from .Placement import placePositions
from .TatamiMat import isReplaceable

ROPE = "arris:rope"
DOWN = 0                                   # 引擎的面：0 下 1 上 2 北 3 南 4 西 5 东
LAVA = ("minecraft:lava", "minecraft:flowing_lava")
# 往下走的底线：所有维度里最低的是主世界的 -64。下界、末地从 0 起：走到 0 以下那几格读出来是什么没核实（多半是空气），
# 就算算出一个 0 以下的落点，RopeAndNet 用 SetBlockNew 放不上去（返回 False）时不扣绳子、什么都不放——和 JE 走到世界底不放一样
BOTTOM = -64


def startRope(clicked, face, sneaking, nameAt):
    """拿着绳子点了 clicked 的 face 面：从哪一节绳子算起；和绳子无关（照常放）返回 None。
    nameAt(坐标) 查那一格的方块名（没加载的格子 None）。

    点到的就是绳子：潜行不潜行都算。点到的不是绳子、外侧那一格才是：只在潜行时算——JE 不潜行时先调点到的方块的 use
    （箱子、门、按钮……自己有右键），这边没有"哪些方块自己会处理右键"的表，不潜行就不抢；潜行时 JE 本来就不调方块的 use。"""
    clickedName = nameAt(clicked)
    if clickedName == ROPE:
        return tuple(clicked)
    if not sneaking or isReplaceable(clickedName):
        return None                        # 点到的是草、水这些：JE 就放在它那一格，不看旁边
    beside = placePositions(*clicked)[face]
    return beside if nameAt(beside) == ROPE else None


def placeAt(start, face, sneaking, nameAt, bottom=BOTTOM):
    """从绳子 start 起，新的一节放在哪：坐标，或者 None（不放）。"""
    direction = face if sneaking else DOWN
    dx, dy, dz = placePositions(0, 0, 0)[direction]
    x, y, z = start
    while True:
        x, y, z = x + dx, y + dy, z + dz
        if y < bottom:
            return None
        name = nameAt((x, y, z))
        if name != ROPE:
            if name in LAVA:
                return None
            return (x, y, z) if isReplaceable(name) else None
        if direction != DOWN:
            return None
