# -*- coding: utf-8 -*-
# runner: both
"""砧板上花、野生作物是平躺的图标，不是立着的方块（Shared/Data/FlatBlockItems、BoardStation.Env.isBlock / isRaised、图标掩码）；蘑菇丛照旧立着。

JE：HoD 的 ItemVoxels.icon / FD 的 CuttingBoardRenderer 都看物品模型立不立体（isGui3d）：花、野生作物、蘑菇丛的物品模型是 item/generated（一张贴图），
像别的食物一样平躺着切；基岩版的 itemType 对它们也是 block（3.10 实机问过），引擎画的也是一张平面的图，所以按名字认。
这张表是照 JE 1.20.1 的物品模型（原版 assets/minecraft/models/item、农夫乐事 data 生成的 assets/farmersdelight/models/item）逐件查出来的：
砧板配方里模型是 item/generated 的方块类物品正好 23 件；FD 自己的 flat_on_cutting_board 标签（三叉戟、望远镜、别的模组的火鸡 / 箭袋）一件也不在砧板配方里。
23 件里的两种蘑菇丛不在表里：实机（3.10，2026-11-18）它们的掉落物是方块模型缩小的立体小蘑菇，不是一张贴图，放平是侧躺的一小撮，所以照旧当方块立着。
表里的 21 件引擎照方块物品的规矩抬高着画（Env.isRaised），摆的时候要扣掉（tests/test_item_pose_raised.py）。
"""
from __future__ import print_function

import fdtest

Station = fdtest.load("Shared.Rules.BoardStation")
CuttingStation = fdtest.load("Shared.Rules.CuttingStation")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
Flat = fdtest.load("Shared.Data.FlatBlockItems").FlatBlockItems
Table = fdtest.load("Shared.Data.Cutting")
Masks = fdtest.load("Shared.Data.ItemMasks").ItemMasks
Icon = fdtest.load("Shared.Rules.HandsOn.BoardIcon")

FLOWERS = ("allium", "azure_bluet", "blue_orchid", "cornflower", "dandelion", "lily_of_the_valley", "orange_tulip", "oxeye_daisy", "pink_tulip",
           "poppy", "red_tulip", "torchflower", "white_tulip", "wither_rose")
CROPS = ("wild_beetroots", "wild_cabbages", "wild_carrots", "wild_onions", "wild_potatoes", "wild_rice", "wild_tomatoes")
COLONIES = ("brown_mushroom_colony", "red_mushroom_colony")
MUSHROOMS = tuple("arris:" + name for name in COLONIES)
# 图标上实心（alpha >= 128）的像素数，数自 JE 的贴图：原版 assets/minecraft/textures/block/<名>.png、农夫乐事 textures/block/<名>.png
# （野生稻是 wild_rice_top，蘑菇丛是 stage3：JE 的物品模型用的就是它们）
JE_SOLID = {"minecraft:allium": 38, "minecraft:azure_bluet": 43, "minecraft:blue_orchid": 44, "minecraft:cornflower": 35, "minecraft:dandelion": 32,
            "minecraft:lily_of_the_valley": 52, "minecraft:orange_tulip": 41, "minecraft:oxeye_daisy": 51, "minecraft:pink_tulip": 41, "minecraft:poppy": 35,
            "minecraft:red_tulip": 49, "minecraft:torchflower": 97, "minecraft:white_tulip": 45, "minecraft:wither_rose": 37,
            "arris:wild_beetroots": 122, "arris:wild_cabbages": 129, "arris:wild_carrots": 108, "arris:wild_onions": 147, "arris:wild_potatoes": 96,
            "arris:wild_rice": 97, "arris:wild_tomatoes": 127, "arris:brown_mushroom_colony": 115, "arris:red_mushroom_colony": 138}
BLOCKS = ("minecraft:oak_log", "minecraft:stone", "minecraft:oak_fence", "minecraft:wooden_button", "minecraft:trapdoor", "arris:oak_cabinet",
          "minecraft:pumpkin", "minecraft:melon_block", "minecraft:gravel")


def _type(item):
    """引擎的物品类型：花、野生作物、蘑菇丛、方块都说 block（3.10 实机），别的是食物。"""
    name = item["newItemName"]
    return "block" if name in Flat or name in BLOCKS or name in MUSHROOMS or name == "x:downstream_flower" else "food"


ENV = Station.Env(lambda name: False, _type)


def _item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testTheFlatListIsTheFlowersAndWildCropsTheBoardCuts():
    expected = set(["minecraft:" + name for name in FLOWERS] + ["arris:" + name for name in CROPS])
    assert set(Flat) == expected and len(Flat) == 21
    for name in Flat:
        assert (name, 0) in Table.CuttingBoardDict, "表里的每一件都是砧板能切的：%s" % name
        assert CuttingStation.strokeOf(Table.CuttingBoardDict[(name, 0)]) == Cutting.TOOL_CUT, "都是刀切的：不响材质破坏声，所以切一刀效果里的 block 变了声音不变：%s" % name


def testOnlyBlocksTheEngineCallsBlocksAndJavaDrawsAsBlocksStandUp():
    for name in Flat:
        assert not ENV.isBlock(_item(name)), "平躺：%s" % name
    for name in BLOCKS:
        assert ENV.isBlock(_item(name)), "立着：%s" % name
    assert ENV.isBlock(_item("x:downstream_flower")), "下游往配方里追加的方块类东西不在表里：照旧立着"
    for name in MUSHROOMS:
        assert not ENV.isBlock(_item(name)) and (name, 0) in Table.CuttingBoardDict, "蘑菇丛在 JE 里也是一张贴图：不当方块（%s）" % name
        assert not ENV.isRaised(_item(name)), "它画的是另一件平面物品（不是 block），不用扣抬高：%s" % name
        assert Station.shownItem(_item(name, 4)) == {"newItemName": name + "_look", "newAuxValue": 0, "count": 4}, name
        assert name not in Flat and fdtest.load("Shared.Data.FlatBlockItems").ShownAs[name] == name + "_look", "不在引擎画成平面图的那张表里：它的掉落物是立体的小模型，所以换一件物品来画"
    assert not ENV.isBlock(_item("arris:cabbage")) and not ENV.isBlock(_item("minecraft:beef")), "食物本来就平躺"
    assert not ENV.isBlock(None) and not ENV.isBlock({}) and not ENV.isBlock({"newItemName": "", "count": 1}), "没有东西不是方块"
    assert ENV.isBlock(dict(_item("minecraft:oak_log", 5), newAuxValue=2)) and not ENV.isBlock(dict(_item("minecraft:poppy", 5), newAuxValue=2)), "数量和 aux 不影响"


def testOnlyTheFlatOnesTheEngineCallsBlocksAreDrawnRaised():
    """花、野生作物：物品类型是 block、掉落物却是一张贴图，引擎照方块物品的规矩抬高着画（Env.isRaised），摆的时候要扣掉。
    真的方块（立方体，另有它的算法）、蘑菇丛、食物都不是；引擎不说它是 block 的也不是（没有那段抬高）。"""
    for name in Flat:
        assert ENV.isRaised(_item(name)) and ENV.isRaised(dict(_item(name, 7), newAuxValue=3)), name
    for name in BLOCKS + MUSHROOMS + ("x:downstream_flower", "arris:cabbage", "minecraft:beef"):
        assert not ENV.isRaised(_item(name)), name
    assert not ENV.isRaised(None) and not ENV.isRaised({}) and not ENV.isRaised({"newItemName": "", "count": 1})
    food = Station.Env(lambda name: False, lambda item: "food")
    assert not any(food.isRaised(_item(name)) for name in Flat), "引擎不把它当方块画，就没有那段抬高"


def testTheTypeTheEngineGivesIsStillWhatDecidesWhetherSomethingCanBeABlockAtAll():
    """按名字认的只是"JE 里画成平面的"：物品类型不是 block 的（引擎不把它当方块画）不会因为名字在表里就变样。"""
    env = Station.Env(lambda name: False, lambda item: "food")
    for name in Flat:
        assert not env.isBlock(_item(name))
    assert not Station.Env(lambda name: False, lambda item: "").isBlock(_item("minecraft:oak_log"))


def testEveryFlatThingHasItsOwnIconMaskLikeFoodSoTheKnifeLinesFollowItsOutline():
    """平躺的东西刀口线按图标的轮廓走（BoardMarks / BoardIcon.iconOf 读 ItemMasks）；没有掩码就按整格实心算，不是 JE 的样子。掩码的实心像素就是 JE 贴图的。"""
    for name in Flat:
        assert name in Masks, "没有掩码：%s" % name
        width, height, rows = Masks[name]
        assert (width, height) == (16, 16) and len(rows) == 16
        assert sum(bin(row).count("1") for row in rows) == JE_SOLID[name], "实心像素数和 JE 的贴图一致：%s" % name
        assert not all(row == (1 << width) - 1 for row in rows), "不是整格实心：%s" % name
        assert Icon.iconOf(name).axis(Icon.ITEM_SIZE) is not None


def testARealBlockHasNoMaskAndIsCutAsASquare():
    for name in BLOCKS:
        assert name not in Masks, "立着的方块不按图标切：%s" % name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
