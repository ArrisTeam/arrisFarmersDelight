# -*- coding: utf-8 -*-
"""Cooking - 煎锅 / 炉灶可烹饪食物、热源方块、炉灶列表（双端，纯数据）

CanCookedFoodDict / CanProvideHeatBlockList / StoveList 是对外联动契约的一部分
（下游经 ArrisFarmersDelightInterface 追加），对象身份不得改变。
"""
# 可以烹饪的食物及输出结果字典
CanCookedFoodDict = {
    "minecraft:beef": "minecraft:cooked_beef",
    "minecraft:chicken": "minecraft:cooked_chicken",
    "minecraft:cod": "minecraft:cooked_cod",
    "minecraft:mutton": "minecraft:cooked_mutton",
    "minecraft:porkchop": "minecraft:cooked_porkchop",
    "minecraft:potato": "minecraft:baked_potato",
    "minecraft:rabbit": "minecraft:cooked_rabbit",
    "minecraft:salmon": "minecraft:cooked_salmon",
    "minecraft:egg": "arris:fried_egg",
    "arris:cod_slice": "arris:cooked_cod_slice",
    "arris:salmon_slice": "arris:cooked_salmon_slice",
    "arris:chicken_cuts": "arris:cooked_chicken_cuts",
    "arris:minced_beef": "arris:beef_patty",
    "arris:bacon": "arris:cooked_bacon",
    "arris:mutton_chops": "arris:cooked_mutton_chops"
}
# 可以提供火源的方块列表
CanProvideHeatBlockList = [
    "minecraft:fire",
    "minecraft:soul_fire",
    "minecraft:campfire",
    "minecraft:soul_campfire",
    "minecraft:lava",
    "minecraft:flowing_lava",
    "minecraft:magma",
    "arris:stove"
]

# 炉灶列表
StoveList = [
    "arris:stove"
]
