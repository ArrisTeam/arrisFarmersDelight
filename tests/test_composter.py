# -*- coding: utf-8 -*-
# runner: both
"""原版堆肥桶收本包的物品（Server/Storage.OnUseComposter + Shared/Rules/Composter.py）对照 JE 的 ComposterBlock，
基岩原版 2026-11-26 实测一样（INGAME-FACTS-1 §3，小麦种子 30%）：空桶第一件 60 次里 60 次成功；7 层不收、不扣、层数不变。
"""
from __future__ import print_function

import sys

import fakeengine
import fdtest

world = fakeengine.install()
sys.modules[fakeengine.ENGINE_MODULE].GetLoadedEntities = lambda: {}        # Storage 导入篮子（篮子的轮询要它，这里用不到）
world.sneaking = set()
_basePlayer = world._Player


def _player(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: target in world.sneaking
    return methods


world._Player = _player

Registry = fdtest.load("Server.EventRegistry")
Storage = fdtest.load("Server.Storage")
Composter = fdtest.load("Shared.Rules.Composter")

POS = (3, 64, 3)
SEEDS = {"newItemName": "arris:tomato_seeds", "newAuxValue": 0, "count": 10}          # 30%


def testRules():
    assert [Composter.accepts(level) for level in range(9)] == [True] * 7 + [False, False]
    assert Composter.nextLevel(0, False) == 1                              # 空桶第一件必成
    assert Composter.nextLevel(3, False) == 3 and Composter.nextLevel(3, True) == 4
    assert Composter.nextLevel(6, True) == Composter.READY == 7 and Composter.FULL == 8 and Composter.READY_SECONDS == 1.0


def _setUp(level, hand=SEEDS):
    for table in (world.players, world.entities, world.blocks, world.modAttr):
        table.clear()
    world.timers = []
    world.sounds[:] = []
    world.sneaking.clear()
    world.addPlayer("p1", hand=dict(hand) if hand else None)
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:composter", states={"composter_fill_level": level})


def _use(lucky):
    Storage.probability = lambda percent: lucky
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "blockName": "minecraft:composter", "cancel": False}
    Registry.dispatch("ServerBlockUseEvent", args, "minecraft:composter")
    return args


placed = []
# 物品放成方块（ItemToBlock，优先级 98）的替身：堆肥桶那一下认领了，它就不该被调到
Registry.registerHandler("ServerItemUseOnEvent", priority=98)(lambda args: placed.append(args["itemDict"]["newItemName"]))


def _useOn(lucky):
    Storage.probability = lambda percent: lucky
    hand = world.players["p1"]["hand"]
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "face": 1, "dimensionId": 0, "entityId": "p1", "blockName": "minecraft:composter",
            "itemDict": dict(hand), "ret": False}
    claimed = Registry.dispatch("ServerItemUseOnEvent", args, "minecraft:composter")
    return args, claimed


def _level():
    return world.blocks[(0,) + POS]["states"]["composter_fill_level"]


def testTheFirstItemAlwaysCounts():
    _setUp(0)
    _use(False)
    assert _level() == 1 and world.players["p1"]["hand"]["count"] == 9


def testLaterItemsRollAndAreUsedEitherWay():
    _setUp(3)
    _use(False)
    assert _level() == 3 and world.players["p1"]["hand"]["count"] == 9
    world.runTimers()                                                       # 冷却过了
    _use(True)
    assert _level() == 4 and world.players["p1"]["hand"]["count"] == 8


def testLevelSevenTakesNothingAndRipensAfterASecond():
    _setUp(6)
    _use(True)
    assert _level() == 7
    ripen = [entry for entry in world.timers if entry[1] is Storage._ripen]
    assert [entry[0] for entry in ripen] == [1.0]
    _use(True)                                                              # 7 层：不收、不扣
    assert _level() == 7 and world.players["p1"]["hand"]["count"] == 9
    ripen[0][1](*ripen[0][2])
    assert _level() == 8 and world.sounds[-1][0] == "block.composter.ready"
    _setUp(8)
    _use(True)
    assert _level() == 8 and world.players["p1"]["hand"]["count"] == 10    # 8 层是取骨粉，交给原版


def testHoldingTheButtonUsesOneItemPerCooldown():
    _setUp(2)
    _use(True)
    _use(True)                                                              # 冷却没过（计时器还没跑）
    assert _level() == 3 and world.players["p1"]["hand"]["count"] == 9


PIE = {"newItemName": "arris:apple_pie_item", "newAuxValue": 0, "count": 2}          # 能堆肥（100%）又能放成方块


def testACompostablePlaceableItemIsCompostedNotPlaced():
    # JE：不潜行时堆肥桶的 use 在先——派点堆肥桶是堆肥，不是把派放在桶上
    _setUp(2, hand=PIE)
    placed[:] = []
    args, claimed = _useOn(True)
    assert claimed is True and args["ret"] is True and placed == []
    assert _level() == 3 and world.players["p1"]["hand"]["count"] == 1
    blockUse = _use(True)                                                   # 同一下的方块事件：冷却挡住，不再扣第二个
    assert blockUse["cancel"] is True and _level() == 3 and world.players["p1"]["hand"]["count"] == 1


def testLevelSevenClaimsTheClickWithoutTakingAnything():
    _setUp(7, hand=PIE)
    placed[:] = []
    args, claimed = _useOn(True)
    assert claimed is True and args["ret"] is True and placed == [] and world.players["p1"]["hand"]["count"] == 2
    assert _use(True)["cancel"] is True and _level() == 7


def testSneakingOrAFullComposterLeavesTheClickAlone():
    _setUp(2, hand=PIE)
    world.sneaking.add("p1")
    placed[:] = []
    args, claimed = _useOn(True)                                            # 潜行：照常放方块
    assert claimed is False and args["ret"] is False and placed == ["arris:apple_pie_item"] and _level() == 2
    _setUp(8, hand=PIE)
    placed[:] = []
    args, claimed = _useOn(True)                                            # 8 层：取骨粉交给原版
    assert claimed is False and placed == ["arris:apple_pie_item"] and _use(True)["cancel"] is False


def testOtherItemsAreIgnored():
    _setUp(2, hand={"newItemName": "minecraft:stone", "newAuxValue": 0, "count": 1})
    _use(True)
    assert _level() == 2 and world.players["p1"]["hand"]["count"] == 1


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
