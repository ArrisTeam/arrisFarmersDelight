# -*- coding: utf-8 -*-
"""Food - 物品放置成方块、合成返还容器（旧接口）、派、盘装食物（双端，纯数据）
"""
# 物品转变为方块字典
itemChangeBlockDict = {
    "arris:skillet_item": "arris:skillet",
    "arris:apple_pie_item": "arris:apple_pie",
    "arris:sweet_berry_cheesecake_item": "arris:sweet_berry_cheesecake",
    "arris:chocolate_pie_item": "arris:chocolate_pie",
    # 原版南瓜派（JE 的 PlacePumpkinPieMixin）：对方块使用就放成 arris:pumpkin_pie，没有自己的 *_item
    "minecraft:pumpkin_pie": "arris:pumpkin_pie",
}
# JE 配置 enablePumpkinPieSneakToPlace（缺省 false）：为 true 时原版南瓜派要潜行才放成方块，不潜行照常吃
PUMPKIN_PIE = "minecraft:pumpkin_pie"
PUMPKIN_PIE_SNEAK_TO_PLACE = False
# "合成后还给玩家的空容器"（linkage 的旧接口，下游包按成品名登记自己的无序配方）：从合成栏取出 key 物品时返还 value 容器，
# perCraft 是配方一份的产出数（缺省 1），一次取出 N 个按 N // perCraft 份还。按成品名查、分不出是哪条配方，
# 只适合"这个成品的无序配方都只还这一种容器、一份一个"的情况。
# 本包自己的配方不靠它：有序配方把剩余物写进 result 数组；无序配方由 Server/CraftReturns.py 读合成格、对上
# Shared/Data/CraftReturns.py（tools/gen_crafts.py 生成）按 JE 的合成剩余物逐格还，那张表里有的成品不再走这里。
# 下面留着的是本包里符合上面那种情况的成品（给按名字读这张表的下游包看；tests/test_recipe_rules.py 核对它和生成的表一致）。
# 表不能清空：linkage 的 Interface / Obtain 对空容器返回 False，下游包就登记不进来了。
shapedRecipeContainerDict = {
    "arris:milk_bottle": {"itemName": "minecraft:bucket", "count": 1, "auxValue": 0, "perCraft": 4},
    "arris:honey_cookie": {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0, "perCraft": 8},
    "arris:salmon_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0, "perCraft": 2},
    "arris:cod_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0, "perCraft": 2},
    "arris:roasted_mutton_chops": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0},
    "arris:steak_and_potatoes": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0},
}
# 派列表
pieList = [
    "arris:apple_pie",
    "arris:sweet_berry_cheesecake",
    "arris:chocolate_pie",
    "arris:pumpkin_pie"
]

# 盘装食物
platePackagedFoodDict = {
    "arris:roast_chicken_block_stage0": {"target": "arris:roast_chicken_block_stage1", "item": "arris:roast_chicken"},
    "arris:roast_chicken_block_stage1": {"target": "arris:roast_chicken_block_stage2", "item": "arris:roast_chicken"},
    "arris:roast_chicken_block_stage2": {"target": "arris:roast_chicken_block_stage3", "item": "arris:roast_chicken"},
    "arris:roast_chicken_block_stage3": {"target": "arris:roast_chicken_block_leftover", "item": "arris:roast_chicken"},
    "arris:roast_chicken_block_leftover": {"target": None, "item": None},
    "arris:stuffed_pumpkin_block_stage0": {"target": "arris:stuffed_pumpkin_block_stage1", "item": "arris:stuffed_pumpkin"},
    "arris:stuffed_pumpkin_block_stage1": {"target": "arris:stuffed_pumpkin_block_stage2", "item": "arris:stuffed_pumpkin"},
    "arris:stuffed_pumpkin_block_stage2": {"target": "arris:stuffed_pumpkin_block_stage3", "item": "arris:stuffed_pumpkin"},
    "arris:stuffed_pumpkin_block_stage3": {"target": None, "item": "arris:stuffed_pumpkin"},
    "arris:honey_glazed_ham_block_stage0": {"target": "arris:honey_glazed_ham_block_stage1", "item": "arris:honey_glazed_ham"},
    "arris:honey_glazed_ham_block_stage1": {"target": "arris:honey_glazed_ham_block_stage2", "item": "arris:honey_glazed_ham"},
    "arris:honey_glazed_ham_block_stage2": {"target": "arris:honey_glazed_ham_block_stage3", "item": "arris:honey_glazed_ham"},
    "arris:honey_glazed_ham_block_stage3": {"target": "arris:honey_glazed_ham_block_leftover", "item": "arris:honey_glazed_ham"},
    "arris:honey_glazed_ham_block_leftover": {"target": None, "item": None},
    "arris:shepherds_pie_block_stage0": {"target": "arris:shepherds_pie_block_stage1", "item": "arris:shepherds_pie"},
    "arris:shepherds_pie_block_stage1": {"target": "arris:shepherds_pie_block_stage2", "item": "arris:shepherds_pie"},
    "arris:shepherds_pie_block_stage2": {"target": "arris:shepherds_pie_block_stage3", "item": "arris:shepherds_pie"},
    "arris:shepherds_pie_block_stage3": {"target": "arris:shepherds_pie_block_leftover", "item": "arris:shepherds_pie"},
    "arris:shepherds_pie_block_leftover": {"target": None, "item": None},
    "arris:rice_roll_medley_block_stage0": {"target": "arris:rice_roll_medley_block_stage1", "item": "arris:kelp_roll_slice"},
    "arris:rice_roll_medley_block_stage1": {"target": "arris:rice_roll_medley_block_stage2", "item": "arris:kelp_roll_slice"},
    "arris:rice_roll_medley_block_stage2": {"target": "arris:rice_roll_medley_block_stage3", "item": "arris:kelp_roll_slice"},
    "arris:rice_roll_medley_block_stage3": {"target": "arris:rice_roll_medley_block_stage4", "item": "arris:salmon_roll"},
    "arris:rice_roll_medley_block_stage4": {"target": "arris:rice_roll_medley_block_stage5", "item": "arris:salmon_roll"},
    "arris:rice_roll_medley_block_stage5": {"target": "arris:rice_roll_medley_block_stage6", "item": "arris:salmon_roll"},
    "arris:rice_roll_medley_block_stage6": {"target": "arris:rice_roll_medley_block_stage7", "item": "arris:cod_roll"},
    "arris:rice_roll_medley_block_stage7": {"target": "arris:rice_roll_medley_block_leftover", "item": "arris:cod_roll"},
    "arris:rice_roll_medley_block_leftover": {"target": None, "item": None},
}
