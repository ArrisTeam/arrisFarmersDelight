# -*- coding: utf-8 -*-
# runner: both
"""放在地上的食物（Server/FoodBlocks.py）：盘装大菜盛菜、派切块吃（手里拿刀则切下一片）；用假引擎驱动（tests/fakeengine.py）。

JE 的 FeastBlock：每份盛一次，要对应的容器（碗）；盛完最后一份，有空盘的菜（hasLeftovers）留下空盘、再点一下收走，
没有空盘的菜（南瓜盅）整道消失 —— 最后一份照样盛给玩家。
JE 的 PieBlock：手里拿刀右键派切下一片掉出来（不吃、不耗刀），否则吃一口；4 口吃完派就没了。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
FoodBlocks = fdtest.load("Server.FoodBlocks")

BOWL = {"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 4}
KNIFE = {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1}
POS = (1, 64, 1)


def _setUp(hand=BOWL, blockName="arris:stuffed_pumpkin_block_stage0"):
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match=FoodBlocks.platePackagedFoodDict)(FoodBlocks.OnServePlatedFood)
    Registry.registerHandler("ServerBlockUseEvent", match=FoodBlocks.pieList)(FoodBlocks.OnEatPie)
    del world.calls[:]
    world.spawned[:] = []
    world.sounds[:] = []
    world.players.clear()
    world.entities.clear()
    world.modAttr.clear()
    world.timers = []
    world.addPlayer("p1", hand=dict(hand) if hand else None)
    world.setBlock(POS[0], POS[1], POS[2], blockName)


def _click(blockName=None):
    blockName = blockName or world.blockName(*POS)
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "blockName": blockName, "aux": 0}
    Registry.dispatch("ServerBlockUseEvent", args, blockName)
    world.runTimers()          # 过了交互冷却，下一次点击才算新的一次


def _given():
    return [(item["itemName"], item["count"]) for item in world.players["p1"]["given"]]


def testStuffedPumpkinGivesAllFourPortionsThenVanishes():
    _setUp()
    seen = []
    for _ in range(4):
        _click()
        seen.append(world.blockName(*POS))
    assert seen == ["arris:stuffed_pumpkin_block_stage1", "arris:stuffed_pumpkin_block_stage2",
                    "arris:stuffed_pumpkin_block_stage3", "minecraft:air"], seen
    assert _given() == [("arris:stuffed_pumpkin", 1)] * 4
    assert world.players["p1"]["hand"] is None, "4 个碗用了 4 个"


def testNeedsABowlAndTheBlockStaysPut():
    _setUp(hand=None, blockName="arris:stuffed_pumpkin_block_stage3")
    _click()
    assert world.blockName(*POS) == "arris:stuffed_pumpkin_block_stage3"
    assert _given() == []
    assert (("p1", "ShowTip", "你需要一个碗以食用它。")) in world.calls


def testCreativeKeepsTheBowl():
    _setUp(blockName="arris:stuffed_pumpkin_block_stage3")
    world.players["p1"]["creative"] = True
    _click()
    assert world.blockName(*POS) == "minecraft:air" and _given() == [("arris:stuffed_pumpkin", 1)]
    assert world.players["p1"]["hand"]["count"] == 4


def testLeftoverPlateIsClearedWithoutAServing():
    _setUp(hand=None, blockName="arris:roast_chicken_block_leftover")
    _click()
    assert world.blockName(*POS) == "minecraft:air" and _given() == []


def testRoastChickenLeavesAPlateAfterTheLastServing():
    _setUp(blockName="arris:roast_chicken_block_stage3")
    _click()
    assert world.blockName(*POS) == "arris:roast_chicken_block_leftover"
    assert _given() == [("arris:roast_chicken", 1)]


def testRiceRollMedleyNeedsNoBowl():
    _setUp(hand=None, blockName="arris:rice_roll_medley_block_stage0")
    _click()
    assert world.blockName(*POS) == "arris:rice_roll_medley_block_stage1" and _given() == [("arris:kelp_roll_slice", 1)]


def _pie(hand, blockName="arris:apple_pie", eaten=0.0):
    _setUp(hand=hand, blockName=blockName)
    world.setBlock(POS[0], POS[1], POS[2], blockName, data={"blockStatus": eaten})


def _molang():
    return [data["molang"] for target, endpoint, data in world.calls if endpoint == "SetEntityBlockMolang"]


def testEatingAPieFeedsThePlayerAndTakesABite():
    _pie(None)
    _click()
    assert world.blocks[(0,) + POS]["data"]["blockStatus"] == 1.0
    assert world.players["p1"]["hunger"] == 13
    assert world.entities["p1"]["effects"] == [("speed", 30, 1)]
    assert ("random.eat", POS) in world.sounds and _molang() == [1.0]


def testThePieIsGoneAfterTheFourthBite():
    _pie(None, eaten=3.0)
    _click()
    assert world.blockName(*POS) == "minecraft:air"


def testKnifeCutsASliceOffThePieWithoutEatingIt():
    _pie(KNIFE)
    _click()
    assert world.blocks[(0,) + POS]["data"]["blockStatus"] == 1.0
    assert world.spawnedNames() == [("arris:apple_pie_slice", 1)]
    assert world.players["p1"]["hunger"] == 10 and world.entities["p1"]["effects"] == []
    assert ("ambient.cutting_board.knife", POS) in world.sounds and _molang() == [1.0]
    assert world.players["p1"]["hand"]["count"] == 1, "切片不耗刀（耐久也不动）"


def testCuttingTheLastSliceRemovesThePie():
    _pie(KNIFE, blockName="arris:sweet_berry_cheesecake", eaten=3.0)
    _click()
    assert world.blockName(*POS) == "minecraft:air"
    assert world.spawnedNames() == [("arris:sweet_berry_cheesecake_slice", 1)]


def testAPieWithoutASliceItemIsStillEatenWithAKnife():
    # 下游追加的派（pieList 里有、切片表里没有）：拿刀也只能吃
    FoodBlocks.pieList.append("test:custom_pie")
    try:
        _pie(KNIFE, blockName="test:custom_pie")
        Registry.registerHandler("ServerBlockUseEvent", match=FoodBlocks.pieList)(FoodBlocks.OnEatPie)
        _click()
        assert world.spawned == [] and world.players["p1"]["hunger"] == 13
    finally:
        FoodBlocks.pieList.remove("test:custom_pie")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
