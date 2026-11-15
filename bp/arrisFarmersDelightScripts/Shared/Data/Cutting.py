# -*- coding: utf-8 -*-
"""Cutting - 砧板配方与刀 / 斧列表（双端，纯数据）

CuttingBoardDict 里刀具条目的 "tool" 与 knifeList 是同一个列表对象：
下游往 knifeList 里加刀要对所有条目生效（联动契约）。
"""
# 刀列表
knifeList = [
    "arris:flint_knife",
    "arris:golden_knife",
    "arris:iron_knife",
    "arris:diamond_knife",
    "arris:netherite_knife",
    "ends_delight:end_stone_knife",
    "ends_delight:purpur_knife",
    "ends_delight:dragon_egg_shell_knife",
    "ends_delight:dragon_tooth_knife"
]
# 斧头列表
axeList = [
    "minecraft:wooden_axe",
    "minecraft:stone_axe",
    "minecraft:copper_axe",
    "minecraft:iron_axe",
    "minecraft:golden_axe",
    "minecraft:diamond_axe",
    "minecraft:netherite_axe"
]
# 可以在砧板上切的食物及输出字典和使用工具
CuttingBoardDict = {
    ("minecraft:beef", 0): {"itemList": [{"itemName": "arris:minced_beef", "count": 2}], "tool": knifeList},
    ("minecraft:cooked_beef", 0): {"itemList": [{"itemName": "arris:beef_patty", "count": 2}], "tool": knifeList},
    ("minecraft:chicken", 0): {"itemList": [{"itemName": "arris:chicken_cuts", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:cooked_chicken", 0): {"itemList": [{"itemName": "arris:cooked_chicken_cuts", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:porkchop", 0): {"itemList": [{"itemName": "arris:bacon", "count": 2}], "tool": knifeList},
    ("minecraft:cooked_porkchop", 0): {"itemList": [{"itemName": "arris:cooked_bacon", "count": 2}], "tool": knifeList},
    ("minecraft:mutton", 0): {"itemList": [{"itemName": "arris:mutton_chops", "count": 2}], "tool": knifeList},
    ("minecraft:muttonraw", 0): {"itemList": [{"itemName": "arris:mutton_chops", "count": 2}], "tool": knifeList},
    ("minecraft:cooked_mutton", 0): {"itemList": [{"itemName": "arris:cooked_mutton_chops", "count": 2}], "tool": knifeList},
    ("minecraft:cod", 0): {"itemList": [{"itemName": "arris:cod_slice", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:cooked_cod", 0): {"itemList": [{"itemName": "arris:cooked_cod_slice", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:salmon", 0): {"itemList": [{"itemName": "arris:salmon_slice", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:cooked_salmon", 0): {"itemList": [{"itemName": "arris:cooked_salmon_slice", "count": 2}, {"itemName": "minecraft:bone_meal", "count": 1}], "tool": knifeList},
    ("minecraft:pumpkin", 0): {"itemList": [{"itemName": "arris:pumpkin_slice", "count": 4}], "tool": knifeList},
    ("minecraft:cake", 0): {"itemList": [{"itemName": "arris:cake_slice", "count": 7}], "tool": knifeList},
    ("arris:ham", 0): {"itemList": [{"itemName": "minecraft:porkchop", "count": 2}, {"itemName": "minecraft:bone", "count": 1}], "tool": knifeList},
    ("arris:smoked_ham", 0): {"itemList": [{"itemName": "minecraft:cooked_porkchop", "count": 2}, {"itemName": "minecraft:bone", "count": 1}], "tool": knifeList},
    ("arris:cabbage", 0): {"itemList": [{"itemName": "arris:cabbage_leaf", "count": 2}], "tool": knifeList},
    ("arris:wheat_dough", 0): {"itemList": [{"itemName": "arris:raw_pasta", "count": 1}], "tool": knifeList},
    ("arris:apple_pie_item", 0): {"itemList": [{"itemName": "arris:apple_pie_slice", "count": 4}], "tool": knifeList},
    ("arris:chocolate_pie_item", 0): {"itemList": [{"itemName": "arris:chocolate_pie_slice", "count": 4}], "tool": knifeList},
    ("arris:kelp_roll", 0): {"itemList": [{"itemName": "arris:kelp_roll_slice", "count": 3}], "tool": knifeList},
    ("arris:sweet_berry_cheesecake_item", 0): {"itemList": [{"itemName": "arris:sweet_berry_cheesecake_slice", "count": 4}], "tool": knifeList},
    ("arris:rice_panicle", 0): {"itemList": [{"itemName": "arris:rice", "count": 1}, {"itemName": "arris:straw", "count": 1}], "tool": knifeList},
    ("minecraft:oak_log", 0): {"itemList": [{"itemName": "minecraft:stripped_oak_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:spruce_log", 0): {"itemList": [{"itemName": "minecraft:stripped_spruce_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:acacia_log", 0): {"itemList": [{"itemName": "minecraft:stripped_acacia_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:birch_log", 0): {"itemList": [{"itemName": "minecraft:stripped_birch_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:cherry_log", 0): {"itemList": [{"itemName": "minecraft:stripped_cherry_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:dark_oak_log", 0): {"itemList": [{"itemName": "minecraft:stripped_dark_oak_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:jungle_log", 0): {"itemList": [{"itemName": "minecraft:stripped_jungle_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:mangrove_log", 0): {"itemList": [{"itemName": "minecraft:stripped_mangrove_log", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:crimson_stem", 0): {"itemList": [{"itemName": "minecraft:stripped_crimson_stem", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:crimson_hyphae", 0): {"itemList": [{"itemName": "minecraft:stripped_crimson_hyphae", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:warped_stem", 0): {"itemList": [{"itemName": "minecraft:stripped_warped_stem", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"},
    ("minecraft:warped_hyphae", 0): {"itemList": [{"itemName": "minecraft:stripped_warped_hyphae", "count": 1}, {"itemName": "arris:tree_bark", "count": 1}], "tool": axeList, "item_type": "axe"}
}
