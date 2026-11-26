# -*- coding: utf-8 -*-
"""Cooking - 煎锅 / 炉灶可烹饪食物、热源方块、炉灶列表（双端，纯数据）

CanCookedFoodDict / CanProvideHeatBlockList / StoveList 是对外联动契约的一部分
（下游经 ArrisFarmersDelightInterface 追加），对象身份不得改变。热源的状态条件表 HeatSourceStateDict 和它派生的 HeatSourceAuxDict
不在契约里，但也随表同步发给客户端（Shared/Rules/SyncTables.OUTSIDE_CONTRACT），对象身份同样不能变。
"""
# 基岩版有三种鸡蛋（鸡蛋、蓝色鸡蛋、棕色鸡蛋：原版物品标签 minecraft:egg 的成员），JE 1.20 只有一种。三种一视同仁：厨锅收三种
# （配方里蛋的格子是 minecraft:egg 标签），别处也一样——能煎、只煎一面、烤架不收、是"磕开的蛋"（PotSunk.CRACKED），工作台另说（JSON 配方没改）
_EGGS = ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")

# 可以烹饪的食物及输出结果字典：JE 的营火烹饪配方（煎锅、炉灶、手持煎锅都照营火配方）——
# 原版 9 条（牛肉、鸡肉、鳕鱼、海带、羊肉、猪排、土豆、兔肉、鲑鱼）加 FD 的 7 条（蛋、肉馅、鸡块、鳕鱼片、鲑鱼片、培根、羊排），共 16 条，时间都是 600 刻；
# 再加基岩版另外两种蛋（JE 没有），也煎成煎蛋。表里没有的，Shared/Rules/Grilling 再问引擎的营火配方
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
    "minecraft:blue_egg": "arris:fried_egg",
    "minecraft:brown_egg": "arris:fried_egg",
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

# 热源方块的状态条件：{方块名: {状态名: 条件}}，一个方块的几条条件都满足才算热（规则 Shared/Rules/HeatSources、HeatStates）。
# 条件三种写法：一个值（相等）、一组值（list / tuple：是其中之一）、{"min": n} / {"max": n}（数值范围，两个可以都写）。
# 写了条件的方块处处按条件判（锅 / 煎锅下面、手持煎锅身边；状态读不到、缺这个状态都算不满足），在名单 / 标签里的也一样；不在名单、标签里的
# 满足条件也算热源。不属于对外联动契约（Api/LegacyModAttr.py 的白名单里没有它）。
# 自带一条：JE 标签里的熔岩炼药锅（minecraft:lava_cauldron）。基岩版没有这个方块（3.10 实机：SetBlockNew("minecraft:lava_cauldron") 放出来的是
# 盛水、0 级的 minecraft:cauldron），它是炼药锅的状态 cauldron_liquid = lava；舀空了（fill_level 0）的不算
HeatSourceStateDict = {
    "minecraft:cauldron": {"cauldron_liquid": "lava", "fill_level": {"min": 1}},
}

# 上面那张表派生的：每个写了条件的方块，满足条件的 aux。客户端读不到方块状态（GetBlock 只给名字和 aux），手持煎锅"身边有没有热源"按它判
# （HeatSources.heatsByAux；写了条件、这里却没有这个方块的当不热）。服务端照引擎的 GetBlockStatesFromAuxValue 重算（Server/HeatAux，
# 每次表同步算差异之前），经表同步发给客户端；这里是同步到之前的初值：熔岩炼药锅 1–6 级，aux = fill_level + 8 × cauldron_liquid 的序号，
# 熔岩是 1（3.10 实机：服务端熔岩 6 级读到 aux 14）
HeatSourceAuxDict = {
    "minecraft:cauldron": [9, 10, 11, 12, 13, 14],
}

# 把热传给上面一格的方块（FD 的标签 heat_conductors：漏斗；create:chute 是可选项，这个引擎上没有对应的方块名）：厨锅 / 煎锅下面是它们时，
# 热源在再下面一格也算热（HeatableBlockEntity.isHeated，java:28-34）。不属于对外联动契约（Api/LegacyModAttr.py 的白名单里没有它）
HeatConductorList = [
    "minecraft:hopper"
]

# 炉灶列表
StoveList = [
    "arris:stove"
]

# 煎锅站点（沉浸式交互前置在场时）上只煎一面、不用翻的东西（HoD 的 KitchenTags.ONE_SIDED，JE 的物品标签，默认只有蛋：这边是三种蛋）。下游模组经联动契约往里追加名字
OneSidedList = list(_EGGS)

# 炉灶站点的烤架不收的东西（HoD 的 KitchenTags.NOT_ON_GRILL：会从烤架的缝里漏下去，默认只有蛋：这边是三种蛋；煎锅照收）。下游模组经联动契约往里追加名字
NotOnGrillList = list(_EGGS)
