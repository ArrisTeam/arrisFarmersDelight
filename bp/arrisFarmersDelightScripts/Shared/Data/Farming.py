# -*- coding: utf-8 -*-
"""Farming - 堆肥物品、野生作物可种植的地面、作物下一阶段、稻草来源、沃土与堆肥的标签（双端，纯数据）

cropsDict 的值为空字符串表示已经长到最后一阶段；它和 WildCropDict、ComposterItemDict 是对外联动契约的一部分
（Api/LegacyModAttr.py），下游会往里追加，必须保持同一个对象。作物具体怎么长见 Shared/Rules/CropGrowth.py。
"""
# 可堆肥的物品 → 放进堆肥桶后桶升一层的概率（%）。表是 JE CommonSetup.registerCompostables 的原样搬运：
# 30% 种子 / 稻米 / 树皮这类，50% 切片和卷心菜叶，65% 蔬菜和野生作物，85% 熟食和甜点，100% 整个的派和菌落
ComposterItemDict = {
    # 30%
    ("arris:tree_bark", 0): 30,
    ("arris:straw", 0): 30,
    ("arris:cabbage_seeds", 0): 30,
    ("arris:tomato_seeds", 0): 30,
    ("arris:rice", 0): 30,
    ("arris:rice_panicle", 0): 30,
    ("arris:sandy_shrub", 0): 30,
    # 50%
    ("arris:pumpkin_slice", 0): 50,
    ("arris:cabbage_leaf", 0): 50,
    ("arris:kelp_roll_slice", 0): 50,
    # 65%
    ("arris:cabbage", 0): 65,
    ("arris:onion", 0): 65,
    ("arris:tomato", 0): 65,
    ("arris:wild_cabbages", 0): 65,
    ("arris:wild_onions", 0): 65,
    ("arris:wild_tomatoes", 0): 65,
    ("arris:wild_carrots", 0): 65,
    ("arris:wild_potatoes", 0): 65,
    ("arris:wild_beetroots", 0): 65,
    ("arris:wild_rice", 0): 65,
    ("arris:pie_crust", 0): 65,
    # 85%
    ("arris:rice_bale", 0): 85,
    ("arris:sweet_berry_cookie", 0): 85,
    ("arris:honey_cookie", 0): 85,
    ("arris:cake_slice", 0): 85,
    ("arris:apple_pie_slice", 0): 85,
    ("arris:sweet_berry_cheesecake_slice", 0): 85,
    ("arris:chocolate_pie_slice", 0): 85,
    ("arris:raw_pasta", 0): 85,
    ("arris:rotten_tomato", 0): 85,
    ("arris:kelp_roll", 0): 85,
    # 100%（派的物品形态叫 *_item；填馅南瓜是厨锅做出来的整块）
    ("arris:apple_pie_item", 0): 100,
    ("arris:sweet_berry_cheesecake_item", 0): 100,
    ("arris:chocolate_pie_item", 0): 100,
    ("arris:dumplings", 0): 100,
    ("arris:stuffed_pumpkin_block_stage0", 0): 100,
    ("arris:brown_mushroom_colony", 0): 100,
    ("arris:red_mushroom_colony", 0): 100,
}

# 野生作物方块且允许种植在其方块上的列表字典
# 七种野生作物可种的地面相同；每种各自持有一份拷贝（下游若改其中一种，不影响其它）。
# 地面是 JE WildCropBlock.mayPlaceOn 的 #minecraft:dirt 加 #minecraft:sand（FD 把沃土也加进了 dirt 标签），
# 加上 Bedrock 的 dirt 标签里有而 JE 没有的耕地（早先版本就能种，留着免得已有的野生作物掉光）。
# 沙地灌木只认沙子（SandyShrubBlock.mayPlaceOn：BlockTags.SAND），不和野生作物共用地面
_WILD_CROP_GROUND = ["minecraft:sand", "minecraft:grass_block", "minecraft:dirt", "minecraft:dirt_with_roots",
                     "minecraft:farmland", "minecraft:podzol", "minecraft:mycelium", "minecraft:mud",
                     "minecraft:red_sand", "minecraft:coarse_dirt", "minecraft:moss_block",
                     "minecraft:muddy_mangrove_roots", "arris:rich_soil"]
WildCropDict = {
    "arris:sandy_shrub": ["minecraft:sand", "minecraft:red_sand"],
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

# 刀具收割时额外掉稻草的方块 → (概率 %, 要求的 aux 或 None)：JE 的 straw_from_grass / tall_grass / sandy_shrub /
# mature_wheat / mature_rice 战利品修改器。蕨不在里面；小麦、稻穗要熟了才掉
STRAW_SOURCES = {
    "minecraft:short_grass": (20, None),
    "minecraft:tall_grass": (20, None),
    "arris:sandy_shrub": (30, None),
    "minecraft:wheat": (100, 7),
    "arris:rich_soil_wheat7": (100, None),
    "arris:rice_upper_crop_stage3": (100, None),
}

# 堆肥催化剂（JE 标签 farmersdelight:compost_activators）：有机肥周围 3×3×3 里每有一个，堆沤的概率 +2%
COMPOST_ACTIVATORS = frozenset([
    "minecraft:brown_mushroom", "minecraft:red_mushroom", "minecraft:podzol", "minecraft:mycelium",
    "arris:organic_compost_stage0", "arris:organic_compost_stage1", "arris:organic_compost_stage2",
    "arris:organic_compost_stage3", "arris:rich_soil", "arris:rich_soil_farmland", "arris:rich_soil_farmland_moist",
    "arris:brown_mushroom_colony", "arris:red_mushroom_colony",
])

# 沃土 / 沃土耕地不催熟的植物（JE 标签 farmersdelight:unaffected_by_rich_soil）。
# 实际能被催熟的只有本模组自己的作物（原版植物没有可调用的骨粉接口），这里照 JE 的标签列全
UNAFFECTED_BY_RICH_SOIL = frozenset([
    "minecraft:grass_block", "minecraft:moss_block", "minecraft:crimson_nylium", "minecraft:warped_nylium",
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
    "minecraft:twisting_vines", "minecraft:big_dripleaf", "minecraft:pink_petals",
    "minecraft:sunflower", "minecraft:lilac", "minecraft:rose_bush", "minecraft:peony", "minecraft:pitcher_plant",
    "arris:sandy_shrub", "arris:brown_mushroom_colony", "arris:red_mushroom_colony",
    "arris:wild_carrots", "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_cabbages",
    "arris:wild_tomatoes", "arris:wild_onions", "arris:wild_rice",
])
