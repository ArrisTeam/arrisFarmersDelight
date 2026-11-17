# -*- coding: utf-8 -*-
"""InventoryAdd - 往玩家背包窗口放东西的落格次序：原版 Inventory.add（双端，纯规则）

JE 的 HoD 往背包放东西（盛出的菜、取回的料、煎好的成品）用的是原版 Inventory.add（PotLogic.java:184、205、269、549、599、627，
SkilletLogic.java:120），放不下的再 player.drop。1.20.1 的次序（对着 minecraft 的字节码核过：Inventory.getSlotWithRemainingSpace /
getFreeSlot / addResource）：
1. 选中的快捷栏格里是同一种、没满：先并进它；
2. 副手里是同一种、没满（基岩版的副手放不了食物和料，不看）；
3. 格号 0..35 里同一种、没满的栈，按格号；
4. 都没有（或还没放完）才放进第一个空格，按格号，每格放满一栈；放完为止。
窗口是 36 格的列表（0-8 快捷栏，9-35 主背包，空格 None），就地改；放不下的余量返回，由调用方掉在玩家脚下。物品的比较和增减
用前置包的 Items（sameItem / countOf / grow / shrink / withCount）：这里只管次序，所以只要有这几个函数的对象，不导入前置包。
"""

HOTBAR = 9


def mergeOrder(selected, size):
    """同一种、没满的栈按什么次序找：选中的快捷栏格（0-8；-1 是不知道）先，再按格号 0..size-1。
    选中的那格在后面又排了一遍：它前面并过了，满了或不是同一种就是白看一眼，不碍事。"""
    first = [selected] if 0 <= selected < min(HOTBAR, size) else []
    return first + list(range(size))


def addToWindow(items, window, item, maxStack, selected=-1):
    """item 放进 window（就地改）；返回放不下的余量，全放进去了返回 None。maxStack 是这种物品一栈最多几个，selected 是选中的快捷栏格。"""
    rest = item
    for index in mergeOrder(selected, len(window)):
        there = window[index]
        if there is None or not items.sameItem(there, rest):
            continue
        moved = min(maxStack - items.countOf(there), items.countOf(rest))
        if moved > 0:
            window[index] = items.grow(there, moved)
            rest = items.shrink(rest, moved)
            if rest is None:
                return None
    for index in range(len(window)):
        if window[index] is None:
            moved = min(maxStack, items.countOf(rest))
            window[index] = items.withCount(rest, moved)
            rest = items.shrink(rest, moved)
            if rest is None:
                return None
    return rest
