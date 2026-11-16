# -*- coding: utf-8 -*-
"""Effects - 有害效果表、滋养时长档位、原版汤的额外增益（双端，纯数据）
"""
COMFORT = "arris:comfort"          # 舒适：JE 1.3.2 起弃用，食物不再给，效果和处理保留
NOURISHMENT = "arris:nourishment"  # 滋养

# JE FoodValues 的滋养时长档位（秒）
BRIEF_DURATION = 30
SHORT_DURATION = 60
MEDIUM_DURATION = 180
LONG_DURATION = 300

# 原版汤吃下后追加的增益（JE CommonEvents.handleVanillaSoupEffects，默认配置里汤类额外效果和兔肉煲跳跃都开着）
# 物品名 -> [(效果名, 秒, 等级, 是否显示粒子)]；滋养不显示粒子，兔肉煲的跳跃提升 II 显示 10 秒
VANILLA_SOUP_BUFFS = {
    "minecraft:mushroom_stew": [(NOURISHMENT, MEDIUM_DURATION, 0, False)],
    "minecraft:beetroot_soup": [(NOURISHMENT, MEDIUM_DURATION, 0, False)],
    "minecraft:rabbit_stew": [(NOURISHMENT, LONG_DURATION, 0, False), ("jump_boost", 10, 1, True)],
}

# 原版所有负面效果 (frozenset for O(1) lookup)。热可可 / 舒适靠它判断"有害"；Api/LegacyModAttr.py 的联动白名单里也有它，名字和对象身份别动
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
