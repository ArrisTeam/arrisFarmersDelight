# -*- coding: utf-8 -*-
# runner: both
"""方块上物品的客户端渲染：摆法（Shared/Rules/BlockDisplay.py）与姿态换算（Shared/Rules/ItemPose.py）。
砧板这几条测的是砧板站点在场时板上的摆法（和站点里一样，开站关站不跳），所以按装了前置包算（linkkit.link）；
没装前置包 / 站点关着时 FD 自己的渲染器（砧板、煎锅、炉灶）在 test_classic_block_display.py。"""
from __future__ import print_function

import math

import fdtest
import linkkit

linkkit.link()        # 砧板站点在场（HandsOnOptions.cuttingBoard）：板上的东西摆成站点里的样子

BD = fdtest.load("Shared.Rules.BlockDisplay")
Pose = fdtest.load("Shared.Rules.ItemPose")
Station = fdtest.load("Shared.Rules.BoardStation")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


TOOLS = {"pickaxe": "pickaxe", "hoe": "hoe", "axe": "axe", "shovel": "shovel", "shears": "shears", "trident": "trident"}


def _typeOf(item):
    name = item["newItemName"]
    if name.endswith("_log") or name.endswith("_mushroom_colony") or name in ("minecraft:poppy", "arris:wild_cabbages"):      # 花、野生作物、蘑菇丛：引擎也说是 block
        return "block"
    if name.endswith("_knife") or name.endswith("_sword"):
        return "sword"
    return TOOLS.get(name.split(":")[-1].split("_")[-1], "food")


ENV = Station.Env(lambda name: name.endswith("_knife"), _typeOf)       # 板上的东西是不是插着的工具：站点里问的同一个规矩


def _board(items, **extra):
    """砧板上的东西怎么摆（板在 (1, 64, 1)，要问"是不是插着的工具""画成方块还是平躺的图标"：站点里问的同一个 Env.isCarving / isBlock）。"""
    return BD.layout(BD.KIND_BOARD, items, _typeOf, (1, 64, 1), carving=ENV.isCarving, isBlock=ENV.isBlock, **extra)


def testABoardShowsOneItemAndTheRightPose():
    food, = _board({"0": _item("minecraft:beef", 1)})
    assert food.flat and food.item["count"] == 1 and food.center[0] == 0.5 and food.center[2] == 0.5
    assert BD.BOARD_TOP < food.center[1] < BD.BOARD_TOP + 0.05, "食物平躺在板面上"
    pile = _board({"0": _item("minecraft:beef", 5)})
    assert len(pile) == 2 and pile[1].center[1] - pile[0].center[1] > 0.03, "一叠不止一个：底下再垫一张，上面那张抬高 0.65 像素"
    assert pile[0].direction != pile[1].direction, "底下那张转个角度"
    moved = _board({"0": _item("minecraft:beef", 1)}, offset=(-1.5 / 16.0, 0.0))
    assert abs(moved[0].center[0] - (0.5 - 1.5 / 16.0)) < 1e-9 and moved[0].center[2] == 0.5, "挪到板底座中间"
    block, = _board({"0": _item("minecraft:oak_log")})
    assert not block.flat, "方块类立在板上"
    assert abs(block.scale - 5.2 / 4.0) < 1e-9, "方块的掉落物是立方体（缩放 1 棱长 4 像素）：棱长 5.2 像素要缩放 1.3"
    pivot = block.center[1] - block.scale * 8.0 / 2.0 / 16.0                 # 道具按贴图物品摆：轴心在"中心"下方半个贴图边长
    assert abs(pivot + 3.2 / 16.0 - (BD.BOARD_TOP + 2.6 / 16.0)) < 1e-9, "引擎把立方体画在轴心上方 3.2 像素：它的中心在板面上方半个棱长"
    tool, = _board({"0": _item("arris:iron_knife")})
    assert not tool.flat and tool.roll == Scene.carvedRoll("sword") == 180.0, "插着的工具竖着、刀身朝板的正面斜着（FD 的 180 度）"
    assert _board({"0": {}}) == []
    assert _board({"0": None}) == []


def testAFlowerAndAWildCropLieFlatLikeAnyFoodThoughTheEngineCallsThemBlocks():
    """JE 的物品模型是一张贴图（item/generated，HoD 的 ItemVoxels.icon / FD 的 isGui3d 都按它判），所以像别的食物一样平躺着切、一叠底下垫一张；
    基岩版的 itemType 对它们也是 block，所以按名字认（Data/FlatBlockItems）。真的方块（原木）照旧立着；蘑菇丛的掉落物是缩小的立体模型，也立着。"""
    for name in ("minecraft:poppy", "arris:wild_cabbages"):
        lone, = _board({"0": _item(name, 1)})
        assert lone.flat and lone.direction == (1.0, 0.0) and abs(lone.scale - BD.BOARD_FOOD_SCALE) < 1e-9, name
        pile = _board({"0": _item(name, 5)})
        assert len(pile) == 2 and all(p.flat for p in pile) and pile[1].center[1] > pile[0].center[1], "一叠：底下再垫一张：%s" % name
    for name in ("minecraft:oak_log", "arris:brown_mushroom_colony", "arris:red_mushroom_colony"):
        block, = _board({"0": _item(name)})
        assert not block.flat and abs(block.scale - BD.BLOCK_SCALE) < 1e-9, "立着：%s" % name


def testAFlatFlowerIsReportedWhereTheEngineWillDrawItOnTheBoardNotFloatingAboveIt():
    """实机（3.10）：花、野生作物的掉落物引擎照方块物品的规矩整体抬高 0.2 格、轴心在离贴图底边 5/16 处。照贴图物品的规矩报中心，它会浮在板上 0.2 格
    （用户报的"浮空了"）。报出去的中心先反着挪：按引擎的画法算回去，画出来的中心和同样摆着的食物是同一个点。"""
    for count in (1, 5):
        flowers = _board({"0": _item("minecraft:poppy", count)})
        foods = _board({"0": _item("minecraft:beef", count)})
        assert len(flowers) == len(foods)
        for flower, food in zip(flowers, foods):
            matrix = Pose.flatMatrix(flower.direction[0], flower.direction[1])
            pivot = Pose.pivotFor(flower.center, matrix, flower.scale)
            reach = (Pose.ITEM_SPAN / 2.0 - Pose.RAISED_PIVOT) * flower.scale / 16.0       # 引擎：轴心到贴图中心，沿贴图自己的上方向
            drawn = (pivot[0] + matrix[0][1] * reach, pivot[1] + Pose.BLOCK_LIFT / 16.0 + matrix[1][1] * reach, pivot[2] + matrix[2][1] * reach)
            assert all(abs(a - b) < 1e-9 for a, b in zip(drawn, food.center)), (count, drawn, food.center)
            assert abs(food.center[1] - flower.center[1] - 0.2) < 1e-9, "平躺：报的中心比食物低 0.2 格"


def _stuck(name, yaw=0, offset=(0.0, 0.0)):
    placed = _board({"0": _item(name)}, offset=offset, yaw=yaw)
    assert len(placed) == 1 and not placed[0].flat, name
    return placed[0]


def testAStuckToolStandsInTheMiddleOfTheBlockAndNotOnTheBoardsBase():
    """FD 的 renderItemCarved：translate(0.5, 0.23, 0.5)——方块正中心、0.23 格高；板底座的中间（offset）只管躺着的食物。"""
    for offset in ((0.0, 0.0), (-1.5 / 16.0, 0.0), (0.0, 1.5 / 16.0)):
        tool = _stuck("arris:iron_knife", offset=offset)
        assert abs(tool.center[0] - 0.5) < 1e-9 and abs(tool.center[2] - 0.5) < 1e-9 and abs(tool.center[1] - 0.23) < 1e-9, offset
        assert abs(tool.scale - Scene.scaleOf(0.6 * 16.0)) < 1e-9, "画 0.6 个图标大：9.6 像素"
    food, = _board({"0": _item("minecraft:beef")}, offset=(-1.5 / 16.0, 0.0))
    assert abs(food.center[0] - (0.5 - 1.5 / 16.0)) < 1e-9, "食物还躺在底座中间"


def testAStuckToolTurnsWithTheBoardItsPictureFacingAwayFromTheBoardsFacing():
    """贴图的正面朝板 FACING 的反方向（renderItemCarved 比摆平的东西多转半圈），所以随方块的朝向转：朝北的板（yaw 0）正面朝南，朝东的朝西，朝南的朝北，朝西的朝东。"""
    fronts = dict((yaw, _stuck("arris:iron_knife", yaw).direction) for yaw in (0, 90, 180, 270))
    for yaw, want in ((0, (0.0, 1.0)), (90, (-1.0, 0.0)), (180, (0.0, -1.0)), (270, (1.0, 0.0))):
        assert abs(fronts[yaw][0] - want[0]) < 1e-9 and abs(fronts[yaw][1] - want[1]) < 1e-9, (yaw, fronts[yaw])
    assert BD.carvedFront(0) == fronts[0]
    assert _stuck("arris:iron_knife").direction == fronts[0], "不给朝向就是朝北"


def testAStuckToolIsTurnedByItsKindPicksAndHoesMoreAndTheTridentLess():
    """CuttingBoardRenderer.java:101-109：镐、锄 225 度，三叉戟 135 度，别的 180 度。剪刀、三叉戟也是插着的工具（不再平躺）。"""
    assert [_stuck("minecraft:iron_" + kind).roll for kind in ("pickaxe", "hoe", "axe", "shovel")] == [225.0, 225.0, 180.0, 180.0]
    assert _stuck("arris:iron_knife").roll == _stuck("minecraft:iron_sword").roll == 180.0
    assert _stuck("minecraft:shears").roll == 180.0 and _stuck("minecraft:trident").roll == 135.0


def testTheSkilletStacksLayersByCount():
    """FD 的 SkilletRenderer（逐项对 Java 的在 test_classic_block_display.py）：1 + ceil(个数 / 最大叠数 * 4) 张，一层叠一层。"""
    assert [BD.modelCount(n, 64) for n in (1, 2, 16, 17, 33, 49, 64)] == [1, 2, 2, 3, 4, 5, 5]
    layers = BD.layout(BD.KIND_SKILLET, {"0": _item("minecraft:beef", 20)}, _typeOf, (3, 64, -7))
    assert len(layers) == 3 and all(p.flat for p in layers)
    heights = [p.center[1] for p in layers]
    assert heights == sorted(heights) and abs(heights[1] - heights[0] - BD.FD_LAYER_RISE) < 1e-9, "一层叠一层"
    again = BD.layout(BD.KIND_SKILLET, {"0": _item("minecraft:beef", 20)}, _typeOf, (3, 64, -7))
    assert [p.center for p in again] == [p.center for p in layers], "同一个煎锅每次画都一样，不会跳"
    assert all(abs(p.center[0] - 0.5) <= BD.FD_SPREAD + 1e-9 and abs(p.center[2] - 0.5) <= BD.FD_SPREAD + 1e-9 for p in layers)


def testTheStoveFillsItsSixPlaces():
    slots = {"0": _item("minecraft:beef"), "3": _item("minecraft:cod"), "5": {}, "4": None}
    placed = BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0))
    assert [(p.center[0], p.center[2]) for p in placed] == [BD.STOVE_SLOTS[0], BD.STOVE_SLOTS[3]]
    assert all(p.flat and p.center[1] == BD.FD_STOVE_HEIGHT > 1.0 for p in placed)


def testTheStoveLayoutTurnsAboutTheBlockCentreWithTheStovesFacing():
    """六个烤位和每件的转角跟着炉灶朝向转（FD 的 DefaultStoveRenderer 按 FACING 转）：朝向 yaw（度）= 站点的北面转到的那一侧；
    第 0 件在朝北的炉灶上在方块的 (0.8, 0.7)，朝东 (0.3, 0.8)、朝南 (0.2, 0.3)、朝西 (0.7, 0.2)；不给朝向就是朝北。"""
    slots = {"0": _item("minecraft:beef")}
    north = BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0))
    assert [(p.center[0], p.center[2]) for p in north] == [BD.STOVE_SLOTS[0]]
    assert [(p.center, p.direction) for p in BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0), yaw=0)] == [(north[0].center, north[0].direction)]
    for yaw, at in ((90, (0.3, 0.8)), (180, (0.2, 0.3)), (270, (0.7, 0.2))):
        turned, = BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0), yaw=yaw)
        assert abs(turned.center[0] - at[0]) < 1.0e-9 and abs(turned.center[2] - at[1]) < 1.0e-9, yaw
        assert turned.center[1] == north[0].center[1] and turned.scale == north[0].scale and turned.flat
        assert turned.direction != north[0].direction, "每件的朝向也转了"
        assert abs(math.hypot(*turned.direction) - 1.0) < 1.0e-9


def testPlaceholderValuesFromTheClientDrawNothing():
    """客户端读到的空值可能是整数之类的占位（实机：空砧板的 cuttingDict 读出来是整数）。"""
    for junk in (0, 2, "", [], {}, {"count": 3}, {"newItemName": "minecraft:beef", "count": 0}):
        assert BD.layout(BD.KIND_BOARD, {"0": junk}, _typeOf, (0, 64, 0)) == [], junk
        assert BD.layout(BD.KIND_SKILLET, {"0": junk}, _typeOf, (0, 64, 0)) == [], junk
        assert BD.layout(BD.KIND_STOVE, {"0": junk, "1": junk}, _typeOf, (0, 64, 0)) == [], junk


def testUnknownKindsDrawNothing():
    assert BD.layout("mystery", {"0": _item("minecraft:beef")}, _typeOf, (0, 0, 0)) == []


def _rebuild(euler):
    x, y, z = euler
    return Pose._mul(Pose._rz(z), Pose._mul(Pose._rx(x), Pose._ry(y)))


def testTheFarmersDelightCopyOfThePoseMathMatchesTheCalibration():
    alpha = math.radians(30.0)
    x, y, z = Pose.engineEuler(Pose.flatMatrix(math.cos(alpha), -math.sin(alpha)))
    assert abs(x - 60.0) < 1e-6 and abs(y - 90.0) < 1e-6 and abs(z + 90.0) < 1e-6
    assert Pose.engineEuler(Pose.uprightMatrix(0.0, -1.0, 135.0)) == (0.0, 0.0, 135.0) or \
        all(abs(a - b) < 1e-6 for a, b in zip(Pose.engineEuler(Pose.uprightMatrix(0.0, -1.0, 135.0)), (0.0, 0.0, 135.0)))
    for placement in BD.layout(BD.KIND_SKILLET, {"0": _item("minecraft:beef", 40)}, _typeOf, (5, 70, 5)):
        matrix = Pose.flatMatrix(placement.direction[0], placement.direction[1])
        rebuilt = _rebuild(Pose.engineEuler(matrix))
        assert all(abs(rebuilt[i][j] - matrix[i][j]) < 1e-6 for i in range(3) for j in range(3))



def testAThingHeldUprightLeansBackAndTipsInTheScenesFrame():
    """厨师手里端着的瓶、桶、蛋：正面朝场景的 -z（镜头那边），往后仰、在贴图平面里倾；场景转了 90 度，姿态跟着转。"""
    same = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    up = [row[1] for row in Pose.standingMatrix(same, 16.0, 0.0)]
    assert abs(up[0]) < 1e-9 and up[1] > 0.95 and 0.27 < up[2] < 0.28, "往后仰 16 度：顶朝 +z（离开镜头）"
    tipped = [row[1] for row in Pose.standingMatrix(same, 0.0, -105.0)]
    assert tipped[0] > 0.96 and tipped[1] < 0.0, "倾 -105 度：顶倒向 +x（屏幕左边），过了水平"
    turned = [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]          # 场景的 x 轴是世界的 +z，z 轴是世界的 -x
    moved = [row[1] for row in Pose.standingMatrix(turned, 16.0, 0.0)]
    assert abs(moved[2]) < 1e-9 and moved[0] < -0.27, "场景转了：往后仰变成朝世界的 -x"
    flat = Pose.lyingMatrix(30.0)
    assert Pose.framed(same, flat) == flat
    assert [row[1] for row in Pose.framed(turned, flat)] != [row[1] for row in flat]
    rebuilt = _rebuild(Pose.engineEuler(Pose.standingMatrix(turned, 16.0, -40.0)))
    wanted = Pose.standingMatrix(turned, 16.0, -40.0)
    assert all(abs(rebuilt[i][j] - wanted[i][j]) < 1e-6 for i in range(3) for j in range(3)), "引擎的欧拉角还原得回来"


def testDishLayersStackOnTheBoardAndTheDishLiesAlone():
    bread = {"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 3}
    egg = {"newItemName": "arris:fried_egg", "newAuxValue": 0, "count": 6}
    items = {"0": None, BD.layerKey(0): bread, BD.layerKey(1): egg, BD.layerKey(2): egg}
    placements = BD.layout(BD.KIND_BOARD, items, lambda item: "", (3, 64, 3))
    assert len(placements) == 3 and all(p.flat for p in placements)
    heights = [p.center[1] for p in placements]
    assert heights == sorted(heights) and heights[2] - heights[0] > 0.05, "一层比一层高"
    assert BD.layout(BD.KIND_BOARD, items, lambda item: "", (3, 64, 3))[1].center == placements[1].center, "同一块板每次一样"
    dish = {"newItemName": "arris:egg_sandwich", "newAuxValue": 0, "count": 3}
    done = BD.layout(BD.KIND_BOARD, dict(items, D=dish), lambda item: "", (3, 64, 3))
    assert len(done) == 1 and done[0].item["newItemName"] == "arris:egg_sandwich"

def testLiquidLayersAreNotDrawnAndEggLayersAreDrawnOpenedLikeAtTheStation():
    """站点里手倒完、磕完以后：液体层什么也不画（容器走了）、蛋层是打开的蛋；没开站点时板上的展示也是这样，开关站那几层不跳（BoardHands.lookOf）。"""
    wheat = _item("minecraft:wheat", 3)
    items = {"0": None, BD.layerKey(0): wheat, BD.layerKey(1): _item("minecraft:milk_bucket", 3), BD.layerKey(2): _item("minecraft:egg", 3),
             BD.layerKey(3): _item("minecraft:sugar", 3), BD.layerKey(4): _item("minecraft:water_bucket", 3)}
    placements = BD.layout(BD.KIND_BOARD, items, lambda item: "", (3, 64, 3))
    assert [p.item["newItemName"] for p in placements] == ["minecraft:wheat", "arris:egg_look_0", "minecraft:sugar"], "奶桶、水桶不画；蛋是打开的蛋；别的原样"
    assert all(p.item["count"] == 1 and p.flat for p in placements)
    heights = [p.center[1] for p in placements]
    base = BD.BOARD_TOP + 0.02
    expected = [base + index * 0.65 / 16.0 for index in (0, 2, 3)]
    assert all(abs(got - want) < 0.003 for got, want in zip(heights, expected)), "液体层虽然不画，它那一层的高度照留：后面的层不往下掉"
    assert [p.scale for p in placements] == [BD.BoardScene.scaleOf(10.0), BD.BoardScene.scaleOf(9.0), BD.BoardScene.scaleOf(9.0)]
    bottom = BD.layout(BD.KIND_BOARD, {BD.layerKey(0): _item("minecraft:milk_bucket", 2), BD.layerKey(1): wheat}, lambda item: "", (3, 64, 3))
    assert [p.item["newItemName"] for p in bottom] == ["minecraft:milk_bucket", "minecraft:wheat"], "第 0 层是底座：容器照旧画"


def testAPoseFollowsTheLastOneSoThePivotDoesNotJumpWhenTheSpriteIsTurnedUpsideDown():
    """ItemPose.steadied：贴图的"上"方向和上一次画的反着时，换成贴图在自己平面里转半圈的那个——占同一块地方、朝外的还是同一面、轴心留在原来那一边。"""
    before = Pose._mul(Pose._ry(30.0), Pose._rx(180.0))                      # 立着、上下颠倒（翻到一半之前）
    after = Pose._ry(30.0)                                                   # 同一块地方、正着（HoD 换成 -90 度之后）
    assert Pose.steadied(after, None) is after and Pose.steadied(before, before) is before
    kept = Pose.steadied(after, before)
    center = (3.0, 5.0, 7.0)
    old, new = Pose.pivotFor(center, before, 1.25), Pose.pivotFor(center, kept, 1.25)
    assert max(abs(a - b) for a, b in zip(old, new)) < 1e-9, "轴心没动"
    jumped = Pose.pivotFor(center, after, 1.25)
    assert abs(jumped[1] - old[1]) > 0.6, "原样摆的话轴心跳一个边长（8 / 16 x 1.25 格）"
    assert all(abs(kept[r][2] - after[r][2]) < 1e-12 for r in range(3)), "朝外的还是同一面（法线没变）"
    assert all(abs(kept[r][0] + after[r][0]) < 1e-12 and abs(kept[r][1] + after[r][1]) < 1e-12 for r in range(3)), "贴图在自己的平面里转了半圈"
    again = Pose.steadied(Pose._mul(Pose._ry(31.0), Pose._rx(-80.0)), kept)
    assert again[1][1] < 0.0, "之后接着它画：还在同一边，不翻回去"
    quarter = Pose._mul(Pose._ry(30.0), Pose._rx(90.0))
    assert Pose.steadied(quarter, Pose._ry(30.0)) is quarter, "转了正好四分之一圈（点积 0）：不换"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
