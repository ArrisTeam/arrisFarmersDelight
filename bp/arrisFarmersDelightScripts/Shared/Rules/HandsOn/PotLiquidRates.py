# -*- coding: utf-8 -*-
"""PotLiquidRates - 厨锅的水量、液面高度，以及按锅的状态定的沸腾 / 气泡 / 蒸汽速率（双端，纯函数）

移植自 Hands-On Delight：station/PotLogic.java 的水量（39-43, 721-729）与 client/PotBehavior.java 的 frame（1174-1178, 1205-1226）。
状态只有四种：没火（COLD）、有火只有水（HOT_WATER）、有火有汤（SOUP）、在煮（COOKING）；速率表按这个顺序排。
时间是秒，长度是站点像素（锅底 y = 2，满水 y = 8.5，锅沿 y = 10）。
"""

BROTH_BASE = 58              # 水量：永远有水，每个非空食材格再多 6（PotLogic.java:39-40）
BROTH_PER_STACK = 6
SOUP_BASE = 74               # 煮好的汤：74 加每份 5，一份一份往下沉（PotLogic.java:42-43）
SOUP_PER_SERVING = 5
TANK_CAPACITY = 100          # 水箱容量，毫桶数（CookingPotStation.java:122）
BROTH_FLOOR = 2.0            # 水箱底的 y，px（PotBehavior.Shape.COOKING_POT.floor，58 行）
BROTH_DEPTH = 6.5            # 满水比锅底高多少，px（Shape.depth）；满水在锅沿下 1.5 px
RIM = 10.0                   # 锅沿 y，px（Shape.rim）

COLD, HOT_WATER, SOUP, COOKING = 0, 1, 2, 3     # 状态：没火 | 有火只有水 | 有火有汤（有菜可煮或有成品）| 在煮
BUBBLE_RATES = (0.0, 0.8, 2.2, 7.0)             # 水里的气泡，个/秒 * boil（PotBehavior.java:1212）
STEAM_RATES = (0.0, 1.6, 3.2, 6.5)              # 蒸汽，个/秒（1217 行，不乘 boil）
EDGE_BUBBLE_RATES = (0.0, 4.0, 8.0, 16.0)       # 贴着锅壁的小泡，个/秒 * boil（1222 行）
AGITATIONS = (0.0, 0.03, 0.03, 0.12)            # 液面的躁动 0..1 * boil（1206 行）
EDGE_BOILS = (0.0, 0.3, 0.55, 0.9)              # 锅壁边的沸腾 0..1 * boil，最多 1（1208 行）


def tankAmount(filledSlots, servings=0):
    """水箱里的量 0..100：永远有水，每个非空食材格多一点；有煮好的菜时至少是汤的量。对应 PotLogic.java:721-729。

    filledSlots：非空的食材格数（0..6）；servings：锅里煮好待盛的份数（没有就 0）。
    0..6 格 -> 58 / 64 / 70 / 76 / 82 / 88 / 94；1..6 份 -> 79 / 84 / 89 / 94 / 99 / 100。
    """
    amount = BROTH_BASE + BROTH_PER_STACK * filledSlots
    if servings > 0:
        amount = max(amount, min(100, SOUP_BASE + SOUP_PER_SERVING * servings))
    return amount


def surfaceHeight(amount, floor=BROTH_FLOOR, depth=BROTH_DEPTH):
    """水量 amount（0..100）对应的液面高度 y，px：floor + depth * amount / 100（PotBehavior.java:531 的 brothFloor + brothDepth * level）。"""
    return floor + depth * amount / 100.0


def potMood(heated, stirring, dish, meal):
    """锅现在的状态：COLD / HOT_WATER / SOUP / COOKING。对应 PotBehavior.frame（1174-1178）。

    heated：锅下有火；stirring：算被搅着；dish：这些料做得出一道菜（或有成品）；meal：锅里有煮好的菜。
    cooking = 有火 && 被搅 && 有菜可煮 && 没成品；soup = 有菜可煮或有成品；没火一律 COLD。
    """
    if not heated:
        return COLD
    if stirring and dish and not meal:
        return COOKING
    return SOUP if (dish or meal) else HOT_WATER


def bubbleRate(mood, boil=1.0):
    """水里气泡的发生速率，个/秒（PotBehavior.java:1212）。boil 是锅的沸腾倍率，厨锅是 1。"""
    return BUBBLE_RATES[mood] * boil


def steamRate(mood):
    """液面蒸汽的发生速率，个/秒（PotBehavior.java:1217）。"""
    return STEAM_RATES[mood]


def edgeBubbleRate(mood, boil=1.0):
    """贴着锅壁的小泡的发生速率，个/秒（PotBehavior.java:1222）。"""
    return EDGE_BUBBLE_RATES[mood] * boil
