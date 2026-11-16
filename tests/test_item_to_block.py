# -*- coding: utf-8 -*-
# runner: both
"""整块的派 / 原版南瓜派对方块使用时放成方块（Server/ItemToBlock.py）；用假引擎驱动（tests/fakeengine.py）。

JE 的 PlacePumpkinPieMixin：原版南瓜派（minecraft:pumpkin_pie）对方块使用就放成 farmersdelight:pumpkin_pie；
配置 enablePumpkinPieSneakToPlace（缺省 false）为 true 时要潜行才放，不潜行照常吃。
放成方块用的是 BlockItem.useOn：放得下、放不下都不会再落到"吃"，所以事件里要取消物品使用（ret），
按住右键每刻重发时（交互冷却内）也一样。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
ItemToBlock = fdtest.load("Server.ItemToBlock")      # 导入即把 OnPlaceItemAsBlock 登记进注册表
Food = fdtest.load("Shared.Data.Food")

PIE = {"newItemName": "minecraft:pumpkin_pie", "newAuxValue": 0, "count": 3}
APPLE_PIE = {"newItemName": "arris:apple_pie_item", "newAuxValue": 0, "count": 2}
CLICKED = (5, 64, 5)         # 点的方块，点它的上面；派放在它上面一格
ABOVE = (5, 65, 5)

# 假引擎的玩家组件没有潜行状态：在这个进程里补上
_basePlayer = world._Player


def _playerWithSneaking(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: bool(world.players[target].get("sneaking"))
    return methods


world._Player = _playerWithSneaking


def _setUp(hand=PIE, sneaking=False, creative=False):
    del world.calls[:]
    world.sounds[:] = []
    world.players.clear()
    world.entities.clear()
    world.blocks.clear()
    world.modAttr.clear()
    world.timers = []
    world.addPlayer("p1", hand=dict(hand), creative=creative)
    world.players["p1"]["sneaking"] = sneaking
    world.setBlock(CLICKED[0], CLICKED[1], CLICKED[2], "minecraft:stone")


def _use(blockName="minecraft:stone", face=1, then=True):
    args = {"entityId": "p1", "x": CLICKED[0], "y": CLICKED[1], "z": CLICKED[2], "face": face, "dimensionId": 0,
            "blockName": blockName, "itemDict": dict(world.players["p1"]["hand"]), "ret": False}
    Registry.dispatch("ServerItemUseOnEvent", args, blockName)
    if then:
        world.runTimers()          # 过了交互冷却，下一次点击才算新的一次
    return args


def _handCount():
    hand = world.players["p1"]["hand"]
    return hand["count"] if hand else 0


def _pieData():
    # 真引擎在放下派的时候建好方块实体数据；假引擎放方块不带数据，这里补一份旧数据，看放置时有没有重置
    data = {"blockStatus": 2.0, "setMolang": True}
    ItemToBlock.GetBlockEntityData = lambda dimensionId, pos: data
    return data


def testThePumpkinPiePlacesItsBlockAndCancelsTheUse():
    _setUp()
    data = _pieData()
    args = _use()
    assert world.blockName(*ABOVE) == "arris:pumpkin_pie"
    assert _handCount() == 2, "放一个扣一个"
    assert args["ret"] is True, "JE：BlockItem.useOn 成功，不会落到吃"
    assert data == {"blockStatus": 0.0, "setMolang": False}, "新放的派是完整的一个"
    assert ("dig.cloth", ABOVE) in world.sounds


def testTheOtherPiesKeepTheirOwnItemAndAreNotCancelled():
    _setUp(hand=APPLE_PIE)
    args = _use()
    assert world.blockName(*ABOVE) == "arris:apple_pie" and _handCount() == 1
    assert args["ret"] is False, "只有原版南瓜派要拦住"


def testSneakConfigOffByDefaultPlacesWithoutSneaking():
    assert Food.PUMPKIN_PIE_SNEAK_TO_PLACE is False, "JE enablePumpkinPieSneakToPlace 缺省 false"
    _setUp(sneaking=False)
    _use()
    assert world.blockName(*ABOVE) == "arris:pumpkin_pie"


def testSneakConfigOnNeedsSneakingAndOtherwiseLetsTheGameEatIt():
    Food.PUMPKIN_PIE_SNEAK_TO_PLACE = True
    try:
        _setUp(sneaking=False)
        args = _use()
        assert world.blockName(*ABOVE) == "minecraft:air" and _handCount() == 3
        assert args["ret"] is False, "不取消：原版照常开始吃"
        _setUp(sneaking=True)
        args = _use()
        assert world.blockName(*ABOVE) == "arris:pumpkin_pie" and _handCount() == 2 and args["ret"] is True
    finally:
        Food.PUMPKIN_PIE_SNEAK_TO_PLACE = False


def testTheUseStaysCancelledWhenTheSpotIsTakenOrInsideTheCooldown():
    _setUp()
    world.setBlock(ABOVE[0], ABOVE[1], ABOVE[2], "minecraft:dirt")
    args = _use()
    assert world.blockName(*ABOVE) == "minecraft:dirt" and _handCount() == 3, "放不下：什么都不动"
    assert args["ret"] is True, "放不下也不会去吃（JE 的 BlockItem 返回 FAIL）"
    _setUp()
    first = _use(then=False)
    again = _use(then=False)          # 按住右键：冷却里重发的事件
    assert first["ret"] is True and again["ret"] is True
    assert _handCount() == 2, "冷却里不再放第二个"


def testCuttingBoardAndFramesAreLeftToTheirOwnHandlers():
    for blockName in ("arris:cutting_board", "minecraft:frame", "minecraft:glow_frame"):
        _setUp()
        args = _use(blockName=blockName)
        assert world.blockName(*ABOVE) == "minecraft:air" and _handCount() == 3, blockName
        assert args["ret"] is False, blockName


def testCreativeKeepsThePie():
    _setUp(creative=True)
    _use()
    assert world.blockName(*ABOVE) == "arris:pumpkin_pie" and _handCount() == 3


def testThePlacementFollowsTheClickedFace():
    _setUp()
    _use(face=4)                                      # 点西面：派放在西边那一格
    assert world.blockName(CLICKED[0] - 1, CLICKED[1], CLICKED[2]) == "arris:pumpkin_pie"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
