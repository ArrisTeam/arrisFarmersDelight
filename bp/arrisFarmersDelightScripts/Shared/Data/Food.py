# -*- coding: utf-8 -*-
"""Food - 物品放置成方块、合成返还容器、派、盘装食物（双端，纯数据）
"""
# 物品转变为方块字典
itemChangeBlockDict = {
    "arris:skillet_item": "arris:skillet",
    "arris:apple_pie_item": "arris:apple_pie",
    "arris:sweet_berry_cheesecake_item": "arris:sweet_berry_cheesecake",
    "arris:chocolate_pie_item": "arris:chocolate_pie",
}
# "合成后还给玩家的空容器"映射：从合成栏取出 key 物品时 → 返还 value 空容器
# 由服务端 CraftItemOutputChangeServerEvent 发放；perCraft 是配方一份的产出数（缺省 1），
# 一次取出 N 个时按 N // perCraft 份返还
shapedRecipeContainerDict = {
    "arris:wheat_dough": {"itemName": "minecraft:bucket", "count": 1, "auxValue": 0},
    "arris:milk_bottle": {"itemName": "minecraft:bucket", "count": 1, "auxValue": 0, "perCraft": 4},
    "arris:honey_cookie": {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0, "perCraft": 8},
    "arris:stuffed_potato": {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0},
    "arris:salmon_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0},
    "arris:cod_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0},
}
# 派列表
pieList = [
    "arris:apple_pie",
    "arris:sweet_berry_cheesecake",
    "arris:chocolate_pie"
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
    "arris:stuffed_pumpkin_block_stage3": {"target": None, "item": None},
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
