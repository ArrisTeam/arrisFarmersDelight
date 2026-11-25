# -*- coding: utf-8 -*-
"""TomatoVine - 绳上的番茄藤：下面撑不撑得住、没了以后绳子回不回来（双端，纯规则）

照 JE 的 HangingTomatoBlock / TomatoBlock（FD 1.3.4）：
- canSurvive：下面是番茄（TOMATO_CROP：这边是地上那株第 3 级起，CropGrowth 的 climbFrom）或者另一节藤才撑得住
  （JE 另外要亮度 ≥ 8 或者看得见天，这里不管）；撑不住就碎掉，照常掉东西；
- onRemove / onDestroyedByPlayer：藤没了（不是换成另一节藤：长一级、摘果子都是换方块）就在原地放回一根绳子
  （配置 enableTomatoRopePermanence 缺省开）。这边只在那一格变成了空气或者水时放（被挖、被炸、下面没了、被水冲掉）；
  JE 连 /setblock 换上去的方块也拿绳子盖掉，它的说明里自己叫"技术限制"，不照搬。
"""
from .CropGrowth import FAMILIES, isFamilyBlock, lastStage
from .CropTick import ROPE, VINE_PREFIX, isVine     # noqa: F401  ROPE：放回去的就是这根绳子（服务端从这里拿）

BASE_PREFIX = "arris:budding_tomatoes_stage"
VINES = tuple(VINE_PREFIX + str(stage) for stage in range(lastStage(VINE_PREFIX) + 1))
# 藤没了以后这一格是这些时把绳子放回去
CLEARED = ("minecraft:air", "minecraft:water", "minecraft:flowing_water")
_BEARING = tuple(range(FAMILIES[BASE_PREFIX]["climbFrom"], lastStage(BASE_PREFIX) + 1))


def holds(belowName):
    """一节藤下面那一格（belowName，没加载 None）撑不撑得住它。"""
    if not belowName:
        return False
    return isVine(belowName) or isFamilyBlock(belowName, BASE_PREFIX, _BEARING)


def ropeBack(nowName):
    """一节藤被拆掉以后，那一格现在是 nowName：要不要放回一根绳子。"""
    return nowName in CLEARED
