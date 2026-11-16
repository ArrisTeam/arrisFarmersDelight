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
    food, = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:beef", 5)}, _typeOf, (1, 64, 1))
    assert food.flat and food.item["count"] == 1 and food.center[0] == 0.5 and food.center[2] == 0.5
    assert BD.BOARD_TOP < food.center[1] < BD.BOARD_TOP + 0.05, "食物平躺在板面上"
    block, = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:oak_log")}, _typeOf, (1, 64, 1))
    assert not block.flat, "方块类立在板上"
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
