# -*- coding: utf-8 -*-
"""Blocks - 可攀爬方块、橱柜、篮子（双端，纯数据）
"""
# 可攀爬的方块列表
canClimbList = [
    "arris:rope",
    "arris:tomatoes_vine_stage0",
    "arris:tomatoes_vine_stage1",
    "arris:tomatoes_vine_stage2",
    "arris:tomatoes_vine_stage3"
]
# 橱柜列表
cabinetList = [
    "arris:oak_cabinet",
    "arris:spruce_cabinet",
    "arris:birch_cabinet",
    "arris:jungle_cabinet",
    "arris:acacia_cabinet",
    "arris:dark_oak_cabinet",
    "arris:mangrove_cabinet",
    "arris:cherry_cabinet",
    "arris:bamboo_cabinet",
    "arris:crimson_cabinet",
    "arris:warped_cabinet"
]
# 篮子（JE 的竹篮与木篮，同一个 BasketBlock）：掉落物进了收集区就吸进去，见 Server/Basket.py；
# 下游追加的篮子要在方块 JSON 里带 netease:on_entity_inside 才走事件那条路，轮询那条路认这张表
basketList = [
    "arris:basket",
    "arris:wooden_basket"
]
