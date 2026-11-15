# -*- coding: utf-8 -*-
"""Effects - 舒适效果会清除的负面效果（双端，纯数据）
"""
# 原版所有负面效果 (frozenset for O(1) lookup — 本 mod 内部使用，不对外暴露于扩展接口)
negativeEffect = frozenset([
    "slowness",
    "mining_fatigue",
    "instant_damage",
    "nausea",
    "blindness",
    "hunger",
    "weakness",
    "wither",
    "poison",
    "fatal_poison",
    "wither",
    "levitation",
    "darkness",
    "wind_charged",
    "weaving",
    "oozing",
    "infested"
])
