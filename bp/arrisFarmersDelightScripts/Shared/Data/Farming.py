# -*- coding: utf-8 -*-
"""Farming - 堆肥物品、野生作物可种植的地面、作物下一阶段（双端，纯数据）

cropsDict 的值为空字符串表示已经长到最后一阶段。
"""
# 可堆肥的物品
ComposterItemDict = {
    ("arris:cabbage_seeds", 0): 50,
    ("arris:tomato_seeds", 0): 50,
    ("arris:rotten_tomato", 0): 40,
    ("arris:cabbage_leaf", 0): 50,
    ("arris:rice", 0): 50,
    ("arris:tree_bark", 0): 50,
    ("arris:straw", 0): 50,
    ("arris:cabbage", 0): 70,
    ("arris:rice_panicle", 0): 60,
    ("arris:tomato", 0): 70,
    ("arris:onion", 0): 70
}

# 野生作物方块且允许种植在其方块上的列表字典
# 八种野生作物可种的地面相同；每种各自持有一份拷贝（下游若改其中一种，不影响其它）
_WILD_CROP_GROUND = ["minecraft:sand", "minecraft:grass_block", "minecraft:dirt", "minecraft:dirt_with_roots",
                     "minecraft:farmland", "minecraft:podzol", "minecraft:mycelium", "minecraft:mud"]
WildCropDict = {
    "arris:sandy_shrub": list(_WILD_CROP_GROUND),
    "arris:wild_beetroots": list(_WILD_CROP_GROUND),
    "arris:wild_carrots": list(_WILD_CROP_GROUND),
    "arris:wild_cabbages": list(_WILD_CROP_GROUND),
    "arris:wild_onions": list(_WILD_CROP_GROUND),
    "arris:wild_rice": list(_WILD_CROP_GROUND),
    "arris:wild_tomatoes": list(_WILD_CROP_GROUND),
    "arris:wild_potatoes": list(_WILD_CROP_GROUND)
}

# 农作物下一阶段字典
cropsDict = {
    "arris:cabbages_stage0": "arris:cabbages_stage1",
    "arris:cabbages_stage1": "arris:cabbages_stage2",
    "arris:cabbages_stage2": "arris:cabbages_stage3",
    "arris:cabbages_stage3": "arris:cabbages_stage4",
    "arris:cabbages_stage4": "arris:cabbages_stage5",
    "arris:cabbages_stage5": "arris:cabbages_stage6",
    "arris:cabbages_stage6": "arris:cabbages_stage7",
    "arris:cabbages_stage7": "",
    "arris:budding_tomatoes_stage0": "arris:budding_tomatoes_stage1",
    "arris:budding_tomatoes_stage1": "arris:budding_tomatoes_stage2",
    "arris:budding_tomatoes_stage2": "arris:budding_tomatoes_stage3",
    "arris:budding_tomatoes_stage3": "arris:budding_tomatoes_stage4",
    "arris:budding_tomatoes_stage4": "arris:budding_tomatoes_stage5",
    "arris:budding_tomatoes_stage5": "arris:budding_tomatoes_stage6",
    "arris:budding_tomatoes_stage6": "",
    "arris:tomatoes_vine_stage0": "arris:tomatoes_vine_stage1",
    "arris:tomatoes_vine_stage1": "arris:tomatoes_vine_stage2",
    "arris:tomatoes_vine_stage2": "arris:tomatoes_vine_stage3",
    "arris:tomatoes_vine_stage3": "",
    "arris:onions_stage0": "arris:onions_stage1",
    "arris:onions_stage1": "arris:onions_stage2",
    "arris:onions_stage2": "arris:onions_stage3",
    "arris:onions_stage3": "",
    "arris:organic_compost_stage0": "arris:organic_compost_stage1",
    "arris:organic_compost_stage1": "arris:organic_compost_stage2",
    "arris:organic_compost_stage2": "arris:organic_compost_stage3",
    "arris:organic_compost_stage3": "arris:rich_soil",
    "arris:rich_soil": "",
    "arris:rich_soil_wheat0": "arris:rich_soil_wheat1",
    "arris:rich_soil_wheat1": "arris:rich_soil_wheat2",
    "arris:rich_soil_wheat2": "arris:rich_soil_wheat3",
    "arris:rich_soil_wheat3": "arris:rich_soil_wheat4",
    "arris:rich_soil_wheat4": "arris:rich_soil_wheat5",
    "arris:rich_soil_wheat5": "arris:rich_soil_wheat6",
    "arris:rich_soil_wheat6": "arris:rich_soil_wheat7",
    "arris:rich_soil_wheat7": "",
    "arris:rich_soil_beetroot0": "arris:rich_soil_beetroot1",
    "arris:rich_soil_beetroot1": "arris:rich_soil_beetroot2",
    "arris:rich_soil_beetroot2": "arris:rich_soil_beetroot3",
    "arris:rich_soil_beetroot3": "",
    "arris:rich_soil_carrots0": "arris:rich_soil_carrots1",
    "arris:rich_soil_carrots1": "arris:rich_soil_carrots2",
    "arris:rich_soil_carrots2": "arris:rich_soil_carrots3",
    "arris:rich_soil_carrots3": "",
    "arris:rich_soil_potatoes0": "arris:rich_soil_potatoes1",
    "arris:rich_soil_potatoes1": "arris:rich_soil_potatoes2",
    "arris:rich_soil_potatoes2": "arris:rich_soil_potatoes3",
    "arris:rich_soil_potatoes3": "",
    # 火把花种在沃土耕地上：方块定义里开了随机刻，但之前漏登记在这里，永远长不大
    "arris:rich_soil_torchflower0": "arris:rich_soil_torchflower1",
    "arris:rich_soil_torchflower1": "arris:rich_soil_torchflower2",
    "arris:rich_soil_torchflower2": "",
    "arris:rice_stage0": "arris:rice_stage1",
    "arris:rice_stage1": "arris:rice_stage2",
    "arris:rice_stage2": "arris:rice_stage3",
    "arris:rice_stage3": "",
    "arris:rice_upper_crop_stage0": "arris:rice_upper_crop_stage1",
    "arris:rice_upper_crop_stage1": "arris:rice_upper_crop_stage2",
    "arris:rice_upper_crop_stage2": "arris:rice_upper_crop_stage3",
    "arris:rice_upper_crop_stage3": "",
}
