# -*- coding: utf-8 -*-
"""Cooking - 煎锅 / 炉灶可烹饪食物、热源方块、炉灶列表（双端，纯数据）

CanCookedFoodDict / CanProvideHeatBlockList / StoveList 是对外联动契约的一部分
（下游经 ArrisFarmersDelightInterface 追加），对象身份不得改变。
"""
# 可以烹饪的食物及输出结果字典：JE 的营火烹饪配方（煎锅、炉灶、手持煎锅都照营火配方）——
# 原版 9 条（牛肉、鸡肉、鳕鱼、海带、羊肉、猪排、土豆、兔肉、鲑鱼）加 FD 的 7 条（蛋、肉馅、鸡块、鳕鱼片、鲑鱼片、培根、羊排），共 16 条，时间都是 600 刻
CanCookedFoodDict = {
    "minecraft:beef": "minecraft:cooked_beef",
    "minecraft:chicken": "minecraft:cooked_chicken",
    "minecraft:cod": "minecraft:cooked_cod",
    "minecraft:kelp": "minecraft:dried_kelp",
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

# 把热传给上面一格的方块（FD 的标签 heat_conductors：漏斗；create:chute 是可选项，这个引擎上没有对应的方块名）：厨锅 / 煎锅下面是它们时，
# 热源在再下面一格也算热（HeatableBlockEntity.isHeated，java:28-34）。不属于对外联动契约（Api/LegacyModAttr.py 的白名单里没有它）
HeatConductorList = [
    "minecraft:hopper"
]

# 炉灶列表
StoveList = [
    "arris:stove"
]
