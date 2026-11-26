# -*- coding: utf-8 -*-
"""CraftReturns - 无序合成配方做完一份补还的剩余物（双端，纯数据，由 tools/gen_crafts.py 从合成配方生成，别手改）

成品 -> 做它的各条无序配方（只收做完可能还东西的）：slots 每格的选项（物品名，或 "#标签"，照配方里的先后，一格一个）、
count 一份出几个、keeps 原样留下的选项（JE 面团配方的水桶）、source 是生成它的配方文件。
还什么不写在表里：服务端 Server/CraftReturns.py 取结果时读格子，Shared/Rules/Crafting 按标签认出是哪条，再按格子里实际放的物品
查 Shared/Data/Remainders.py（JE 的合成剩余物，每份每格还一件）。有序配方的剩余物写在 result 数组里，引擎自己给。
"""
CraftReturns = {
    'arris:cod_roll': [
        {"slots": ('arris:cod_slice', 'arris:cod_slice', 'arris:cooked_rice'), "count": 2, "keeps": (), "source": 'arris_cod_roll.json'},
    ],
    'arris:gleaming_salad_block_stage0': [
        {"slots": ('minecraft:glow_berries', 'minecraft:glow_berries', 'minecraft:honey_bottle', 'arris:tomato', 'minecraft:golden_carrot', 'minecraft:beetroot', 'arris:cabbage', 'arris:cabbage', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_gleaming_salad_block.json'},
    ],
    'arris:honey_cookie': [
        {"slots": ('minecraft:honey_bottle', 'minecraft:wheat', 'minecraft:wheat'), "count": 8, "keeps": (), "source": 'arris_honey_cookie.json'},
    ],
    'arris:honey_glazed_ham_block_stage0': [
        {"slots": ('minecraft:sweet_berries', 'minecraft:sweet_berries', 'minecraft:sweet_berries', 'minecraft:sweet_berries', 'minecraft:honey_bottle', 'arris:smoked_ham', 'arris:cooked_rice', 'arris:cooked_rice', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_honey_glazed_ham_block.json'},
    ],
    'arris:milk_bottle': [
        {"slots": ('minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:milk_bucket'), "count": 4, "keeps": (), "source": 'arris_milk_bottle.json'},
    ],
    'arris:roasted_mutton_chops': [
        {"slots": ('arris:cooked_rice', 'arris:cooked_mutton_chops', 'arris:tomato', 'minecraft:beetroot', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_roasted_mutton_chops.json'},
    ],
    'arris:salmon_roll': [
        {"slots": ('arris:cooked_rice', 'arris:salmon_slice', 'arris:salmon_slice'), "count": 2, "keeps": (), "source": 'arris_salmon_roll.json'},
    ],
    'arris:shepherds_pie_block_stage0': [
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'arris:milk_bottle', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'arris:milk_bottle', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block2.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:milk_bucket', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block3.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:milk_bucket', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block4.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'arris:milk_bottle', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block5.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'arris:milk_bottle', 'arris:cooked_mutton_chops', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block6.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:milk_bucket', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block7.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:milk_bucket', 'arris:cooked_mutton_chops', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'arris:onion', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_shepherds_pie_block8.json'},
    ],
    'arris:steak_and_potatoes': [
        {"slots": ('arris:cooked_rice', 'minecraft:cooked_beef', 'minecraft:baked_potato', 'arris:onion', 'minecraft:bowl'), "count": 1, "keeps": (), "source": 'arris_steak_and_potatoes.json'},
    ],
    'arris:stuffed_potato': [
        {"slots": ('minecraft:baked_potato', 'arris:beef_patty', 'arris:milk_bottle'), "count": 1, "keeps": (), "source": 'arris_stuffed_potato.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:cooked_beef', 'arris:milk_bottle'), "count": 1, "keeps": (), "source": 'arris_stuffed_potato2.json'},
        {"slots": ('minecraft:baked_potato', 'arris:beef_patty', 'minecraft:milk_bucket'), "count": 1, "keeps": (), "source": 'arris_stuffed_potato3.json'},
        {"slots": ('minecraft:baked_potato', 'minecraft:cooked_beef', 'minecraft:milk_bucket'), "count": 1, "keeps": (), "source": 'arris_stuffed_potato4.json'},
    ],
    'arris:wheat_dough': [
        {"slots": ('minecraft:wheat', 'minecraft:water_bucket'), "count": 1, "keeps": ('minecraft:water_bucket',), "source": 'arris_wheat_dough.json'},
    ],
    'minecraft:milk_bucket': [
        {"slots": ('minecraft:bucket', 'arris:milk_bottle', 'arris:milk_bottle', 'arris:milk_bottle', 'arris:milk_bottle'), "count": 1, "keeps": (), "source": 'arris_milk_bucket_from_bottles.json'},
    ],
}
