# -*- coding: utf-8 -*-
# runner: both
"""放在地上的食物（Server/FoodBlocks.py）：盘装大菜盛菜、派用刀切；用假引擎驱动（tests/fakeengine.py）。

JE 的 FeastBlock：每份盛一次，要对应的容器（碗）；盛完最后一份，有空盘的菜（hasLeftovers）留下空盘、再点一下收走，
没有空盘的菜（南瓜盅）整道消失 —— 最后一份照样盛给玩家。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
FoodBlocks = fdtest.load("Server.FoodBlocks")

BOWL = {"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 4}
POS = (1, 64, 1)


def _setUp(hand=BOWL, blockName="arris:stuffed_pumpkin_block_stage0"):
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match=FoodBlocks.platePackagedFoodDict)(FoodBlocks.OnServePlatedFood)
    del world.calls[:]
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


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
