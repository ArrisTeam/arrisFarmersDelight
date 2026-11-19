# -*- coding: utf-8 -*-
"""FlatBlockItems - 基岩版说是方块、掉落物却画成一张平面贴图的物品（双端，纯数据）

砧板把东西画成立着的方块还是平躺的图标，JE 看的是物品模型立不立体：HoD 的 ItemVoxels.icon 在 model.isGui3d() 为真时是"方块"
（BoardBehavior.drawItem / chopped 的 block）、FD 的 CuttingBoardRenderer.render 的 isBlockItem 也是 model.isGui3d()。花、野生作物的物品模型是
item/generated（一张贴图），JE 把它们像别的食物一样平躺着切，刀口按图标的轮廓走；原木、石头、栅栏、活板门、按钮、压力板、橱柜的模型是方块（父模型是 block/…），立着。
基岩版的 GetItemBasicInfo 对这两样都说 block；3.10 实机看过：花和野生作物的掉落物引擎画出来也是一张平面的图，所以按名字把它们列在这里。

怎么得到这张表：砧板配方（Shared/Data/Cutting）里每一件，查 JE 1.20.1 的物品模型（原版 assets/minecraft/models/item/<名>.json、
农夫乐事 data 生成的 assets/farmersdelight/models/item/<名>.json）的父模型：item/generated 的、而基岩版的 itemType 是 block 的，有 23 件
（14 种花、7 种野生作物、2 种蘑菇丛）；别的方块（原木、石头……）父模型是 block/…，门 / 告示牌 / 船 / 矿车 / 皮甲 / 食物基岩版本来就不是 block、
在 tools/gen_item_masks.py 的图标表里。FD 自己的 flat_on_cutting_board 标签（三叉戟、望远镜、两个别的模组的火鸡 / 箭袋）一件也不在砧板配方里，
三叉戟在这里是插着的工具（BoardStation.Env.isCarving）。
**两种蘑菇丛不在这张表里**：实机（3.10，2026-11-18）它们的掉落物不是一张贴图，是方块模型缩小的立体小蘑菇，放平了是侧躺着的一小撮。
JE 里它们的物品模型也是一张贴图（item/generated，贴图 block/<名>_stage3），所以另做了两件只用来显示的平面物品（ShownAs：图标就是 stage3 那张贴图，
bp/netease_items_beh/arris_*_mushroom_colony_look.json，创造栏里没有）：板上、世界里的展示、手上画的都是那一件，照普通贴图物品平躺。表里是 21 件。
引擎画这 21 件和画贴图物品还有一处不同：照方块物品的规矩整体抬高 0.2 格、轴心在离贴图底边 5/16 处，摆的时候要扣掉（Shared/Rules/ItemPose.raisedShift，
BoardStation.Env.isRaised 说是不是这一类）——不扣的话平躺在板上会浮起 0.2 格。
这几件的图标掩码（刀口怎么穿过它）在 Shared/Data/ItemMasks，也由 tools/gen_item_masks.py 生成；下游往配方里追加的花不在这里，照旧画成方块。
"""
# 画出来换成另一件物品的（只用来显示）：真物品名 -> 显示用的物品名。换过之后就是一件普通的贴图物品（不是 block、不用扣抬高）
ShownAs = {
    "arris:brown_mushroom_colony": "arris:brown_mushroom_colony_look",
    "arris:red_mushroom_colony": "arris:red_mushroom_colony_look",
}

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
))
