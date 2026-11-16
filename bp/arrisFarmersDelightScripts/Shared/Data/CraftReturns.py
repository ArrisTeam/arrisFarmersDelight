# -*- coding: utf-8 -*-
"""CraftReturns - 无序合成配方做完一份补还的剩余物（双端，纯数据，由 tools/gen_crafts.py 从合成配方生成，别手改）

成品 -> 做它的各条无序配方：ingredients 原料名（排好序，一格一个）、count 一份出几个、returns {原料名: 剩余物名}
（每份每格还一件，JE 的合成剩余物；面团配方的水桶剩它自己）、source 是生成它的配方文件。
服务端 Server/CraftReturns.py 取结果时读格子对上这张表；有序配方的剩余物写在 result 数组里，引擎自己给。
"""
CraftReturns = {
    'arris:cod_roll': [
        {"ingredients": ('arris:cod_slice', 'arris:cod_slice', 'arris:cooked_rice',), "count": 2, "returns": {'arris:cooked_rice': 'minecraft:bowl'}, "source": 'arris_cod_roll.json'},
    ],
    'arris:honey_cookie': [
        {"ingredients": ('minecraft:honey_bottle', 'minecraft:wheat', 'minecraft:wheat',), "count": 8, "returns": {'minecraft:honey_bottle': 'minecraft:glass_bottle'}, "source": 'arris_honey_cookie.json'},
    ],
    'arris:honey_glazed_ham_block_stage0': [
        {"ingredients": ('arris:cooked_rice', 'arris:cooked_rice', 'arris:smoked_ham', 'minecraft:bowl', 'minecraft:honey_bottle', 'minecraft:sweet_berries', 'minecraft:sweet_berries', 'minecraft:sweet_berries', 'minecraft:sweet_berries',), "count": 1, "returns": {'arris:cooked_rice': 'minecraft:bowl', 'minecraft:honey_bottle': 'minecraft:glass_bottle'}, "source": 'arris_honey_glazed_ham_block.json'},
    ],
    'arris:milk_bottle': [
        {"ingredients": ('minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:glass_bottle', 'minecraft:milk_bucket',), "count": 4, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_milk_bottle.json'},
    ],
    'arris:roasted_mutton_chops': [
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:cooked_rice', 'arris:tomato', 'minecraft:beetroot', 'minecraft:bowl',), "count": 1, "returns": {'arris:cooked_rice': 'minecraft:bowl'}, "source": 'arris_roasted_mutton_chops.json'},
    ],
    'arris:salmon_roll': [
        {"ingredients": ('arris:cooked_rice', 'arris:salmon_slice', 'arris:salmon_slice',), "count": 2, "returns": {'arris:cooked_rice': 'minecraft:bowl'}, "source": 'arris_salmon_roll.json'},
    ],
    'arris:shepherds_pie_block_stage0': [
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:milk_bottle', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_shepherds_pie_block.json'},
        {"ingredients": ('arris:milk_bottle', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_shepherds_pie_block2.json'},
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_shepherds_pie_block3.json'},
        {"ingredients": ('arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_shepherds_pie_block4.json'},
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:milk_bottle', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_shepherds_pie_block5.json'},
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:milk_bottle', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_shepherds_pie_block6.json'},
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:cooked_mutton_chops', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_shepherds_pie_block7.json'},
        {"ingredients": ('arris:cooked_mutton_chops', 'arris:onion', 'arris:onion', 'minecraft:baked_potato', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_mutton', 'minecraft:cooked_mutton', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_shepherds_pie_block8.json'},
    ],
    'arris:steak_and_potatoes': [
        {"ingredients": ('arris:cooked_rice', 'arris:onion', 'minecraft:baked_potato', 'minecraft:bowl', 'minecraft:cooked_beef',), "count": 1, "returns": {'arris:cooked_rice': 'minecraft:bowl'}, "source": 'arris_steak_and_potatoes.json'},
    ],
    'arris:stuffed_potato': [
        {"ingredients": ('arris:beef_patty', 'arris:milk_bottle', 'minecraft:baked_potato',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_stuffed_potato.json'},
        {"ingredients": ('arris:milk_bottle', 'minecraft:baked_potato', 'minecraft:cooked_beef',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_stuffed_potato2.json'},
        {"ingredients": ('arris:beef_patty', 'minecraft:baked_potato', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_stuffed_potato3.json'},
        {"ingredients": ('minecraft:baked_potato', 'minecraft:cooked_beef', 'minecraft:milk_bucket',), "count": 1, "returns": {'minecraft:milk_bucket': 'minecraft:bucket'}, "source": 'arris_stuffed_potato4.json'},
    ],
    'arris:wheat_dough': [
        {"ingredients": ('minecraft:water_bucket', 'minecraft:wheat',), "count": 1, "returns": {'minecraft:water_bucket': 'minecraft:water_bucket'}, "source": 'arris_wheat_dough.json'},
    ],
    'minecraft:milk_bucket': [
        {"ingredients": ('arris:milk_bottle', 'arris:milk_bottle', 'arris:milk_bottle', 'arris:milk_bottle', 'minecraft:bucket',), "count": 1, "returns": {'arris:milk_bottle': 'minecraft:glass_bottle'}, "source": 'arris_milk_bucket_from_bottles.json'},
    ],
}
