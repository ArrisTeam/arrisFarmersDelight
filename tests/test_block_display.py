# -*- coding: utf-8 -*-
# runner: both
"""方块上物品的客户端渲染：摆法（Shared/Rules/BlockDisplay.py）与姿态换算（Shared/Rules/ItemPose.py）。"""
from __future__ import print_function

import math

import fdtest

BD = fdtest.load("Shared.Rules.BlockDisplay")
Pose = fdtest.load("Shared.Rules.ItemPose")


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def _typeOf(item):
    name = item["newItemName"]
    if name.endswith("_log"):
        return "block"
    if name.endswith("_knife") or name.endswith("_sword"):
        return "sword"
    return "food"


def testABoardShowsOneItemAndTheRightPose():
    food, = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:beef", 1)}, _typeOf, (1, 64, 1))
    assert food.flat and food.item["count"] == 1 and food.center[0] == 0.5 and food.center[2] == 0.5
    assert BD.BOARD_TOP < food.center[1] < BD.BOARD_TOP + 0.05, "食物平躺在板面上"
    pile = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:beef", 5)}, _typeOf, (1, 64, 1))
    assert len(pile) == 2 and pile[1].center[1] - pile[0].center[1] > 0.03, "一叠不止一个：底下再垫一张，上面那张抬高 0.65 像素"
    assert pile[0].direction != pile[1].direction, "底下那张转个角度"
    moved = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:beef", 1)}, _typeOf, (1, 64, 1), offset=(-1.5 / 16.0, 0.0))
    assert abs(moved[0].center[0] - (0.5 - 1.5 / 16.0)) < 1e-9 and moved[0].center[2] == 0.5, "挪到板底座中间"
    block, = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:oak_log")}, _typeOf, (1, 64, 1))
    assert not block.flat, "方块类立在板上"
    assert abs(block.scale - 5.2 / 4.0) < 1e-9, "方块的掉落物是立方体（缩放 1 棱长 4 像素）：棱长 5.2 像素要缩放 1.3"
    pivot = block.center[1] - block.scale * 8.0 / 2.0 / 16.0                 # 道具按贴图物品摆：轴心在"中心"下方半个贴图边长
    assert abs(pivot + 3.2 / 16.0 - (BD.BOARD_TOP + 2.6 / 16.0)) < 1e-9, "引擎把立方体画在轴心上方 3.2 像素：它的中心在板面上方半个棱长"
    tool, = BD.layout(BD.KIND_BOARD, {"0": _item("arris:iron_knife")}, _typeOf, (1, 64, 1))
    assert not tool.flat and tool.roll == BD.TOOL_ROLL, "工具竖着、刀尖朝下"
    assert BD.layout(BD.KIND_BOARD, {"0": {}}, _typeOf, (1, 64, 1)) == []
    assert BD.layout(BD.KIND_BOARD, {"0": None}, _typeOf, (1, 64, 1)) == []


def testTheSkilletStacksLayersByCount():
    assert [BD.skilletLayers(n) for n in (0, 1, 2, 16, 17, 33, 49, 64)] == [0, 1, 2, 2, 3, 4, 5, 5]
    layers = BD.layout(BD.KIND_SKILLET, {"0": _item("minecraft:beef", 20)}, _typeOf, (3, 64, -7))
    assert len(layers) == 3 and all(p.flat for p in layers)
    heights = [p.center[1] for p in layers]
    assert heights == sorted(heights) and abs(heights[1] - heights[0] - BD.LAYER_STEP) < 1e-9, "一层叠一层"
    again = BD.layout(BD.KIND_SKILLET, {"0": _item("minecraft:beef", 20)}, _typeOf, (3, 64, -7))
    assert [p.center for p in again] == [p.center for p in layers], "同一个煎锅每次画都一样，不会跳"
    assert all(abs(p.center[0] - 0.5) <= 0.06 and abs(p.center[2] - 0.5) <= 0.06 for p in layers)


def testTheStoveFillsItsSixPlaces():
    slots = {"0": _item("minecraft:beef"), "3": _item("minecraft:cod"), "5": {}, "4": None}
    placed = BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0))
    assert [(p.center[0], p.center[2]) for p in placed] == [BD.STOVE_SLOTS[0], BD.STOVE_SLOTS[3]]
    assert all(p.flat and p.center[1] > BD.STOVE_TOP for p in placed)


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

if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
