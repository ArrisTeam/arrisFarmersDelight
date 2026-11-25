# -*- coding: utf-8 -*-
"""Effects - 有害效果表、滋养时长档位、原版汤的额外增益（双端，纯数据）
"""
COMFORT = "arris:comfort"          # 舒适：JE 1.3.2 起弃用，食物不再给，效果和处理保留
NOURISHMENT = "arris:nourishment"  # 滋养

# 吃下去给滋养的食物（物品 JSON 的 minecraft:food.effects 里有 arris:nourishment；tests/test_food_effects_rules.py 对着 JSON 核）。
# JE 的 FoodValues 给的滋养不冒粒子（MobEffectInstance 的 visible 是 false）：食物 JSON 写不了，吃下后由 Server/FoodEffects.py 换成不冒粒子的
NOURISHING_FOODS = frozenset([
    "arris:bacon_and_eggs", "arris:baked_cod_stew", "arris:bone_broth", "arris:chicken_soup", "arris:cookbeef_stew", "arris:cooked_rice",
    "arris:fish_stew", "arris:fried_rice", "arris:gleaming_salad", "arris:grilled_salmon", "arris:honey_glazed_ham", "arris:mushroom_rice",
    "arris:noodle_soup", "arris:onion_soup", "arris:pasta_with_meatballs", "arris:pasta_with_mutton_chop", "arris:pumpkin_soup",
    "arris:ratatouille", "arris:roast_chicken", "arris:roasted_mutton_chops", "arris:shepherds_pie", "arris:squid_ink_pasta",
    "arris:steak_and_potatoes", "arris:stuffed_pumpkin", "arris:vegetable_noodles", "arris:vegetable_soup",
])

# JE FoodValues 的滋养时长档位（秒）
BRIEF_DURATION = 30
SHORT_DURATION = 60
MEDIUM_DURATION = 180
LONG_DURATION = 300

# 西瓜汁回的生命值（JE MelonJuiceItem：heal(2.0F)，一颗心）
MELON_JUICE_HEAL = 2.0

# 原版汤吃下后追加的增益（JE CommonEvents.handleVanillaSoupEffects，默认配置里汤类额外效果和兔肉煲跳跃都开着）
# 物品名 -> [(效果名, 秒, 等级, 是否显示粒子)]；滋养不显示粒子，兔肉煲的跳跃提升 II 显示 10 秒
VANILLA_SOUP_BUFFS = {
    "minecraft:mushroom_stew": [(NOURISHMENT, MEDIUM_DURATION, 0, False)],
    "minecraft:beetroot_soup": [(NOURISHMENT, MEDIUM_DURATION, 0, False)],
    "minecraft:rabbit_stew": [(NOURISHMENT, LONG_DURATION, 0, False), ("jump_boost", 10, 1, True)],
}

# 原版所有负面效果 (frozenset for O(1) lookup)。热可可靠它判断"有害"；Api/LegacyModAttr.py 的联动白名单里也有它，名字和对象身份别动
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
