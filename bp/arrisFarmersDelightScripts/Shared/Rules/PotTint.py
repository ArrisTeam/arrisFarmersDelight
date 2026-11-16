# -*- coding: utf-8 -*-
"""PotTint - 锅里的料各是什么颜色、倒进去的液体什么时候把水染上色（双端，纯逻辑）

对应 Hands-On Delight：FoodColors.of（FoodColors.java:41-46）、PotBehavior.colour 里染水的那一段（1050-1060）和 onFlow（833-834）：
- 一件料的颜色：倒的液体（奶、水、蜂蜜……）是它容器里的液色，蛋是蛋黄加蛋白（不是蛋壳），其余是图标的加权平均（FoodColors 表，没有的取兜底色）；
- 能把水染色的只有倒的液体，蛋不染（它只作为食物色，按煮熟程度混进去）；而且液体从手里开始流出来的那一刻才染：
  手还端着、没开始倒的，和一起放进来还没轮到的（waiting）都不算。刚看到这口锅时就在锅里的、手走完了的、同一格里再叠一份的不用等。
"""
from ..Data import PotSunk
from ..Data.BrothColors import FALLBACK, PouredColors, RAW_EGG
from ..Data.FoodColors import FoodColors

LIQUIDS = frozenset(name for name, _aux in PotSunk.POURED)
EGGS = frozenset(name for name, _aux in PotSunk.CRACKED)


def colorOf(name):
    """一件料的颜色 0xRRGGBB（FoodColors.of）。"""
    if name in EGGS:
        return RAW_EGG
    if name in LIQUIDS and name in PouredColors:
        return PouredColors[name]
    return FoodColors.get(name, FALLBACK)


class Tint(object):
    """哪几格的液体还没倒出来（waiting）：这几格不染水，其余倒进去的照常染。"""

    def __init__(self):
        self.waiting = set()

    def put(self, slot, name):
        """第 slot 格新放进了 name：是倒的液体就等手把它倒出来再染（PotBehavior 里新放进的液体 goesIn 起一个 Pour）。"""
        if name in LIQUIDS:
            self.waiting.add(slot)

    def release(self, slot):
        """第 slot 格不再等了：液体开始流了（Pour 的 onFlow，从这一刻染），或者这格空了 / 手没了。返回有没有变化（要不要重算汤色）。"""
        if slot in self.waiting:
            self.waiting.discard(slot)
            return True
        return False

    def liquids(self, items, sunk):
        """此刻把水染上色的液体颜色（按格号）：沉着的格里倒的液体，等着倒的除外。"""
        return [PouredColors[items[slot]["newItemName"]] for slot in sorted(sunk)
                if items[slot] is not None and items[slot]["newItemName"] in LIQUIDS
                and items[slot]["newItemName"] in PouredColors and slot not in self.waiting]
