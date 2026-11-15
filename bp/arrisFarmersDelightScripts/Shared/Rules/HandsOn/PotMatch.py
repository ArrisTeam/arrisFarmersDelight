# -*- coding: utf-8 -*-
"""PotMatch - 锅里的料能凑出几份配方，增广路匹配（双端）

移植自 Hands-On Delight 的 station/PotLogic.java：servingsLeft / makes / take。
锅里每个槽给一份的一件料，一件料只能给一个配料；一个配料能接受哪些槽由调用方的 accepts(配料序号, 槽序号) 决定
（这样配料可以是 FD 的"任一标签物品"，不依赖任何物品系统）。贪心分配会漏解：先到的配料占了后面配料唯一能用的槽，
所以找不到空位时，让已占了这个槽的别的配料去别处另找（沿增广路改派）。
"""


def servingsLeft(counts, ingredientCount, accepts, isEmpty=None):
    """料够做几份。counts 是各槽的物品数（空槽 0，下标就是 accepts 的槽序号）；ingredientCount 是配方的配料数。"""
    filled = [count for count in counts if count > 0]
    if not filled:
        return 0
    left = min(filled)
    # 同一个槽里可能躺着两件料各被一个配料占（Autochef 那类按堆叠匹配的 mod）：
    # 逐份减下去，直到真能凑出来为止
    while left > 0 and not makes(counts, ingredientCount, left, accepts, isEmpty):
        left -= 1
    return left


def makes(counts, ingredientCount, times, accepts, isEmpty=None):
    """各槽的料能不能把每个配料各凑 times 份。isEmpty(配料序号) 为真的配料（占位）跳过。"""
    room = list(counts)
    taken = [[0] * len(counts) for _ in range(ingredientCount)]
    for ingredient in range(ingredientCount):
        if isEmpty is not None and isEmpty(ingredient):
            continue
        for _ in range(times):
            if not _take(ingredient, accepts, room, taken, [False] * ingredientCount):
                return False
    return True


def _take(ingredient, accepts, room, taken, seen):
    """再给 ingredient 找一件料：先找还有余量的槽；没有就让占着这个槽的别的配料去别处另找一件。"""
    seen[ingredient] = True
    for stack in range(len(room)):
        if accepts(ingredient, stack) and room[stack] > 0:
            room[stack] -= 1
            taken[ingredient][stack] += 1
            return True
    for stack in range(len(room)):
        if not accepts(ingredient, stack):
            continue
        for other in range(len(seen)):
            if not seen[other] and taken[other][stack] > 0 and _take(other, accepts, room, taken, seen):
                taken[other][stack] -= 1
                taken[ingredient][stack] += 1
                return True
    return False
