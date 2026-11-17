# -*- coding: utf-8 -*-
"""FlatBlockItems - 基岩版说是方块、JE 里的物品模型却是一张平面贴图的物品（双端，纯数据）

砧板把东西画成立着的方块还是平躺的图标，JE 看的是物品模型立不立体：HoD 的 ItemVoxels.icon 在 model.isGui3d() 为真时是"方块"
（BoardBehavior.drawItem / chopped 的 block）、FD 的 CuttingBoardRenderer.render 的 isBlockItem 也是 model.isGui3d()。花、野生作物、蘑菇丛的物品模型是
item/generated（一张贴图），JE 把它们像别的食物一样平躺着切，刀口按图标的轮廓走；原木、石头、栅栏、活板门、按钮、压力板、橱柜的模型是方块（父模型是 block/…），才立着。
基岩版的 GetItemBasicInfo 对这两样都说 block，3.10 实机问过：花和 arris:wild_cabbages 引擎画出来的也是一张平面的图，所以按名字把 JE 里画成平面的列在这里。

怎么得到这张表：砧板配方（Shared/Data/Cutting）里每一件，查 JE 1.20.1 的物品模型（原版 assets/minecraft/models/item/<名>.json、
农夫乐事 data 生成的 assets/farmersdelight/models/item/<名>.json）的父模型：item/generated 的、而基岩版的 itemType 是 block 的，就是这里的 23 件
（14 种花、7 种野生作物、2 种蘑菇丛）；别的方块（原木、石头……）父模型是 block/…，门 / 告示牌 / 船 / 矿车 / 皮甲 / 食物基岩版本来就不是 block、
在 tools/gen_item_masks.py 的图标表里。FD 自己的 flat_on_cutting_board 标签（三叉戟、望远镜、两个别的模组的火鸡 / 箭袋）一件也不在砧板配方里，
三叉戟在这里是插着的工具（BoardStation.Env.isCarving）。
这几件的图标掩码（刀口怎么穿过它）在 Shared/Data/ItemMasks，也由 tools/gen_item_masks.py 生成；下游往配方里追加的花不在这里，照旧画成方块。
"""
FlatBlockItems = frozenset((
    # 花（minecraft:item/generated，贴图 block/<名>）
    "minecraft:allium",
    "minecraft:azure_bluet",
    "minecraft:blue_orchid",
    "minecraft:cornflower",
    "minecraft:dandelion",
    "minecraft:lily_of_the_valley",
    "minecraft:orange_tulip",
    "minecraft:oxeye_daisy",
    "minecraft:pink_tulip",
    "minecraft:poppy",
    "minecraft:red_tulip",
    "minecraft:torchflower",
    "minecraft:white_tulip",
    "minecraft:wither_rose",
    # 农夫乐事的野生作物（minecraft:item/generated，贴图 farmersdelight:block/wild_<作物>；野生稻是 block/wild_rice_top）
    "arris:wild_beetroots",
    "arris:wild_cabbages",
    "arris:wild_carrots",
    "arris:wild_onions",
    "arris:wild_potatoes",
    "arris:wild_rice",
    "arris:wild_tomatoes",
    # 蘑菇丛（贴图 block/<颜色>_mushroom_colony_stage3）
    "arris:brown_mushroom_colony",
    "arris:red_mushroom_colony",
))
