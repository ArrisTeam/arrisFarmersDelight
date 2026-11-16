# -*- coding: utf-8 -*-
# runner: both
"""用刀切蛋糕、拆派和蛋糕、拆南瓜（Server/KnifeSlicing.py），用假引擎驱动（tests/fakeengine.py）。

JE：右键蛋糕用刀切下一片（不吃）；用刀破坏派 / 蛋糕掉剩下口数的切片，插蜡烛的蛋糕额外 7 片；用刀破坏南瓜
（没有精准采集）掉 4 片南瓜片、不掉南瓜。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
KnifeSlicing = fdtest.load("Server.KnifeSlicing")

KNIFE = {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1}
POS = (3, 64, 3)
CAKE_SLICE = "arris:cake_slice"


def _setUp(hand=KNIFE, creative=False):
    Registry.clearAll()
    for event, match, handler in (
            ("ServerBlockUseEvent", KnifeSlicing.CAKES, KnifeSlicing.OnKnifeOnCake),
            ("ServerPlayerTryDestroyBlockEvent", KnifeSlicing.SLICEABLE, KnifeSlicing.OnTryBreakSliceable),
            ("DestroyBlockEvent", KnifeSlicing.SLICEABLE, KnifeSlicing.OnBrokeSliceable),
            ("DestroyBlockEvent", "minecraft:pumpkin", KnifeSlicing.OnBrokePumpkin)):
        Registry.registerHandler(event, match=match)(handler)
    world.players.clear()
    world.entities.clear()
    world.blocks.clear()
    world.spawned[:] = []
    world.destroyed[:] = []
    world.itemEntities.clear()
    world.modAttr.clear()
    world.timers = []
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)


def _use(blockName, aux=0):
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "blockName": blockName,
            "aux": aux, "cancel": False}
    Registry.dispatch("ServerBlockUseEvent", args, blockName)
    world.runTimers()
    return args


def _break(blockName, aux=0, drops=(), tryFirst=True):
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "fullName": blockName,
            "auxData": aux, "cancel": False, "spawnResources": True}
    if tryFirst:
        Registry.dispatch("ServerPlayerTryDestroyBlockEvent", dict(args), blockName)
    world.blocks.pop((0,) + POS, None)         # 方块没了
    done = dict(args, dropEntityIds=list(drops))
    Registry.dispatch("DestroyBlockEvent", done, blockName)


def testKnifeOnCakeCutsASliceInsteadOfEating():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    args = _use("minecraft:cake")
    assert args["cancel"] is True
    assert world.blocks[(0,) + POS]["states"] == {"bite_counter": 1}
    assert world.spawnedNames() == [(CAKE_SLICE, 1)]
    assert ("ambient.cutting_board.knife", POS) in world.sounds


def testLastSliceRemovesTheCake():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 6})
    _use("minecraft:cake")
    assert world.blockName(*POS) == "minecraft:air" and world.spawnedNames() == [(CAKE_SLICE, 1)]


def testCakeBitesFallBackToTheAuxValue():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states=None)
    _use("minecraft:cake", aux=6)
    assert world.blockName(*POS) == "minecraft:air"


def testWithoutAKnifeTheCakeIsLeftToTheGame():
    for hand in (None, {"newItemName": "minecraft:wheat", "newAuxValue": 0, "count": 1}):
        _setUp(hand=hand)
        world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
        args = _use("minecraft:cake")
        assert args["cancel"] is False and world.spawned == []
        assert world.blocks[(0,) + POS]["states"] == {"bite_counter": 0}


def testKnifeOnCandleCakeLeavesACakeWithOneBiteAndDropsTheCandle():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:red_candle_cake", states={"lit": False})
    _use("minecraft:red_candle_cake")
    assert world.blockName(*POS) == "minecraft:cake"
    assert world.blocks[(0,) + POS]["states"] == {"bite_counter": 1}
    assert sorted(world.spawnedNames()) == sorted([("minecraft:red_candle", 1), (CAKE_SLICE, 1)])


def testHoldingTheClickDoesNotCutTwiceWithinTheCooldown():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "blockName": "minecraft:cake",
            "aux": 0, "cancel": False}
    Registry.dispatch("ServerBlockUseEvent", dict(args), "minecraft:cake")
    second = dict(args)
    Registry.dispatch("ServerBlockUseEvent", second, "minecraft:cake")
    assert second["cancel"] is True, "冷却内的重复事件也要取消，免得原版吃了蛋糕"
    assert len(world.spawned) == 1 and world.blocks[(0,) + POS]["states"] == {"bite_counter": 1}


def testBreakingACakeWithAKnifeDropsTheRemainingSlices():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 2})
    _break("minecraft:cake")
    assert world.spawnedNames() == [(CAKE_SLICE, 5)]


def testBreakingACandleCakeDropsSevenSlices():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:candle_cake", states={"lit": False})
    _break("minecraft:candle_cake")
    assert world.spawnedNames() == [(CAKE_SLICE, 7)]


def testBreakingAPieDropsOneSlicePerRemainingServing():
    for bites, left in ((None, 4), (0.0, 4), (1.0, 3), (3.0, 1)):
        _setUp()
        world.setBlock(POS[0], POS[1], POS[2], "arris:apple_pie", data={"blockStatus": bites})
        _break("arris:apple_pie")
        assert world.spawnedNames() == [("arris:apple_pie_slice", left)], (bites, world.spawnedNames())


def testEachPieDropsItsOwnSlice():
    for pie, sliceItem in (("arris:chocolate_pie", "arris:chocolate_pie_slice"),
                           ("arris:sweet_berry_cheesecake", "arris:sweet_berry_cheesecake_slice"),
                           ("arris:pumpkin_pie", "arris:pumpkin_pie_slice")):
        _setUp()
        world.setBlock(POS[0], POS[1], POS[2], pie, data={"blockStatus": 2.0})
        _break(pie)
        assert world.spawnedNames() == [(sliceItem, 2)]


def testNothingDropsWithoutAKnifeOrInCreativeOrWhenTheBreakNeverFinished():
    _setUp(hand=None)
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    _break("minecraft:cake")
    _setUp(creative=True)
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    _break("minecraft:cake")
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    _break("minecraft:cake", tryFirst=False)          # 没有"即将破坏"的单子：不补
    assert world.spawned == []


def testAbandonedBreakLeavesNoSlicesAndItsTicketIsNotReusedByAnotherPlayer():
    _setUp()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:cake", states={"bite_counter": 0})
    Registry.dispatch("ServerPlayerTryDestroyBlockEvent", {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0,
                                                           "playerId": "p1", "fullName": "minecraft:cake", "auxData": 0},
                      "minecraft:cake")
    world.addPlayer("p2", hand=None)
    Registry.dispatch("DestroyBlockEvent", {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p2",
                                            "fullName": "minecraft:cake", "dropEntityIds": []}, "minecraft:cake")
    assert world.spawned == []


def _pumpkinDrop():
    world.itemEntities["drop1"] = {"newItemName": "minecraft:pumpkin", "newAuxValue": 0, "count": 1}
    return ["drop1"]


def testKnifeBreaksAPumpkinIntoFourSlices():
    _setUp()
    _break("minecraft:pumpkin", drops=_pumpkinDrop(), tryFirst=False)
    assert world.destroyed == ["drop1"]
    assert world.spawnedNames() == [("arris:pumpkin_slice", 4)]


def testSilkTouchKnifeKeepsThePumpkin():
    _setUp(hand=dict(KNIFE, enchantData=[(16, 1)]))
    _break("minecraft:pumpkin", drops=_pumpkinDrop(), tryFirst=False)
    assert world.destroyed == [] and world.spawned == []


def testNoSlicesWithoutAKnifeInCreativeOrWithoutAPumpkinDrop():
    _setUp(hand={"newItemName": "minecraft:iron_axe", "newAuxValue": 0, "count": 1})
    _break("minecraft:pumpkin", drops=_pumpkinDrop(), tryFirst=False)
    _setUp(creative=True)
    _break("minecraft:pumpkin", drops=_pumpkinDrop(), tryFirst=False)
    _setUp()
    _break("minecraft:pumpkin", drops=[], tryFirst=False)
    assert world.spawned == [] and world.destroyed == []


def testOtherDropsAreLeftAlone():
    _setUp()
    world.itemEntities["other"] = {"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1}
    _break("minecraft:pumpkin", drops=["other"], tryFirst=False)
    assert world.destroyed == [] and world.spawned == []


def testVanillaCakesAreWhitelistedForUseEvents():
    names = set(world.listened)
    assert "minecraft:cake:*" in names and "minecraft:candle_cake:*" in names and "minecraft:black_candle_cake:*" in names
    assert len([n for n in names if n.endswith("candle_cake:*")]) == 17


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
