# -*- coding: utf-8 -*-
# runner: both
"""拿着绳子点绳子（Server/RopeAndNet.py 的 OnPlaceRopeOnRope + Shared/Rules/RopeExtend.py）对照 JE 的 RopeItem（FD 1.3.4）。

JE：点到的格子（点到的方块能被顶替就是它自己，绳子对手里的绳子算能被顶替；否则是点到的面外侧那一格）是绳子时，
不潜行一律往下、潜行照点到的面走：碰到岩浆不放，能被顶替的一格放下，实心方块不放；还是绳子时只有往下才接着走。
点到的格子不是绳子就和这里无关（照常放）。
"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest

world = fakeengine.install()
engineModule = sys.modules[fakeengine.ENGINE_MODULE]
engineModule.IsLiving = lambda entityId: True
# QuModLibs 离线导入不了（它要引擎）：RopeAndNet 只用它的两个装饰器，换成什么都不做的
quMod = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Server")
quMod.AllowCall = lambda func: func
quMod.InjectHttpPlayerId = lambda func: func
sys.modules[quMod.__name__] = quMod

world.sneaking, world.cannotBuild = set(), set()
_basePlayer = world._Player


def _player(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: target in world.sneaking
    methods["GetPlayerAbilities"] = lambda: {"build": target not in world.cannotBuild, "mine": True}
    return methods


world._Player = _player

Registry = fdtest.load("Server.EventRegistry")
RopeAndNet = fdtest.load("Server.RopeAndNet")
RopeExtend = fdtest.load("Shared.Rules.RopeExtend")

ROPE = "arris:rope"
STONE = "minecraft:stone"
DOWN, UP, NORTH, SOUTH, WEST, EAST = range(6)
HAND = {"newItemName": ROPE, "newAuxValue": 0, "count": 5}


def _column(top, count, x=5, z=5):
    """从 top 往下 count 节绳子（规则用例的世界：{坐标: 方块名}，没写的是空气）。"""
    return dict(((x, top - index, z), ROPE) for index in range(count))


def _nameAt(blocks):
    return lambda pos: blocks.get(tuple(pos), "minecraft:air")


# ---- 规则 ----

def testNotSneakingAlwaysGoesToTheBottomOfTheRope():
    blocks = _column(70, 4)                                    # 70 69 68 67
    nameAt = _nameAt(blocks)
    for face in range(6):
        assert RopeExtend.placeAt((5, 70, 5), face, False, nameAt) == (5, 66, 5), face
    assert RopeExtend.placeAt((5, 68, 5), NORTH, False, nameAt) == (5, 66, 5)          # 点中间那节也一样


def testTheRopeStopsAtSolidGroundAndLava():
    blocks = _column(70, 4)
    blocks[(5, 66, 5)] = STONE
    assert RopeExtend.placeAt((5, 70, 5), NORTH, False, _nameAt(blocks)) is None      # JE：break，不放
    for lava in ("minecraft:lava", "minecraft:flowing_lava"):
        blocks[(5, 66, 5)] = lava
        assert RopeExtend.placeAt((5, 70, 5), NORTH, False, _nameAt(blocks)) is None
    for soft in ("minecraft:water", "minecraft:flowing_water", "minecraft:tall_grass", "minecraft:vine"):
        blocks[(5, 66, 5)] = soft
        assert RopeExtend.placeAt((5, 70, 5), NORTH, False, _nameAt(blocks)) == (5, 66, 5), soft


def testUnloadedCellsAndTheWorldBottomStopIt():
    blocks = _column(70, 4)
    nameAt = lambda pos: None if pos[1] == 66 else _nameAt(blocks)(pos)                 # noqa: E731
    assert RopeExtend.placeAt((5, 70, 5), NORTH, False, nameAt) is None
    assert RopeExtend.placeAt((5, -63, 5), DOWN, False, _nameAt(_column(-63, 2))) is None   # -63 -64 都是绳子，再往下出了世界
    assert RopeExtend.placeAt((5, -62, 5), DOWN, False, _nameAt(_column(-62, 2))) == (5, -64, 5)


def testSneakingFollowsTheClickedFace():
    blocks = _column(70, 4)
    nameAt = _nameAt(blocks)
    assert RopeExtend.placeAt((5, 70, 5), EAST, True, nameAt) == (6, 70, 5)
    assert RopeExtend.placeAt((5, 70, 5), NORTH, True, nameAt) == (5, 70, 4)
    assert RopeExtend.placeAt((5, 70, 5), UP, True, nameAt) == (5, 71, 5)
    assert RopeExtend.placeAt((5, 70, 5), DOWN, True, nameAt) == (5, 66, 5)              # 朝下的面：顺着绳子往下走
    assert RopeExtend.placeAt((5, 69, 5), UP, True, nameAt) is None                      # 往上一格还是绳子：不放
    blocks[(6, 70, 5)] = ROPE
    assert RopeExtend.placeAt((5, 70, 5), EAST, True, _nameAt(blocks)) is None           # 旁边那格是绳子：只有往下才接着走


def testTheStartIsTheClickedRopeOrTheRopeOutsideTheClickedFace():
    blocks = _column(70, 2)                                    # 70 69
    blocks[(5, 71, 5)] = STONE                                 # 绳子挂在石头下面
    nameAt = _nameAt(blocks)
    for sneaking in (False, True):
        assert RopeExtend.startRope((5, 69, 5), NORTH, sneaking, nameAt) == (5, 69, 5)   # 点到的就是绳子：潜行不潜行都算
    assert RopeExtend.startRope((5, 71, 5), DOWN, True, nameAt) == (5, 70, 5)            # 潜行点石头朝下的面：外侧那格是绳子
    assert RopeExtend.startRope((5, 71, 5), DOWN, False, nameAt) is None                 # 不潜行：石头（可能是箱子、门）先轮到，不抢
    assert RopeExtend.startRope((5, 71, 5), NORTH, True, nameAt) is None                 # 外侧是空气：照常放
    blocks[(4, 70, 5)] = "minecraft:tall_grass"
    blocks[(3, 70, 5)] = ROPE
    assert RopeExtend.startRope((4, 70, 5), WEST, True, _nameAt(blocks)) is None         # 点到的是草：JE 放在草那一格，不看旁边


# ---- 服务端 ----

def _setUp(hand=HAND, creative=False, sneaking=False):
    Registry.clearAll()
    Registry.registerHandler("ServerItemUseOnEvent", match=ROPE, keyOf=RopeAndNet._itemName, priority=98)(RopeAndNet.OnPlaceRopeOnRope)
    for table in (world.players, world.entities, world.blocks, world.modAttr):
        table.clear()
    world.sounds[:] = []
    world.calls[:] = []
    world.timers = []
    world.sneaking.clear()
    world.cannotBuild.clear()
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    if sneaking:
        world.sneaking.add("p1")


def _click(pos, face=NORTH):
    hand = world.players["p1"]["hand"]
    args = {"x": pos[0], "y": pos[1], "z": pos[2], "face": face, "dimensionId": 0, "entityId": "p1",
            "blockName": world.blockName(*pos), "itemDict": dict(hand), "ret": False}
    Registry.dispatch("ServerItemUseOnEvent", args, args["blockName"])
    world.runTimers()
    return args


def _ropes(x=5, z=5):
    return [y for y in range(60, 80) if world.blockName(x, y, z) == ROPE]


def _hang(top, count, x=5, z=5):
    for pos in _column(top, count, x, z):
        world.setBlock(pos[0], pos[1], pos[2], ROPE)


def testClickingARopeAddsOneAtTheBottomAndUsesOneRope():
    _setUp()
    _hang(70, 3)                                               # 70 69 68
    args = _click((5, 70, 5), EAST)
    assert args["ret"] is True                                 # 引擎自己放在东边那格的不要
    assert _ropes() == [67, 68, 69, 70] and world.blockName(6, 70, 5) == "minecraft:air"
    assert world.players["p1"]["hand"]["count"] == 4
    assert world.sounds == [("dig.cloth", (5.5, 67.5, 5.5))]


def testCreativeKeepsTheRope():
    _setUp(creative=True)
    _hang(70, 3)
    _click((5, 69, 5))
    assert _ropes() == [67, 68, 69, 70] and world.players["p1"]["hand"]["count"] == 5


def testNothingWhenTheRopeAlreadyReachesTheGround():
    _setUp()
    _hang(70, 3)
    world.setBlock(5, 67, 5, STONE)
    args = _click((5, 70, 5))
    assert args["ret"] is True and _ropes() == [68, 69, 70]
    assert world.players["p1"]["hand"]["count"] == 5 and world.sounds == []


def testSneakingPlacesOnTheClickedFace():
    _setUp(sneaking=True)
    _hang(70, 3)
    _click((5, 70, 5), EAST)
    assert world.blockName(6, 70, 5) == ROPE and _ropes() == [68, 69, 70]


def testPlayersWhoMayNotBuildPlaceNothing():
    _setUp()
    _hang(70, 3)
    world.cannotBuild.add("p1")
    args = _click((5, 70, 5))
    assert args["ret"] is True and _ropes() == [68, 69, 70] and world.players["p1"]["hand"]["count"] == 5


def testHoldingTheButtonPlacesOncePerCooldown():
    _setUp()
    _hang(70, 3)
    hand = world.players["p1"]["hand"]
    args = {"x": 5, "y": 70, "z": 5, "face": NORTH, "dimensionId": 0, "entityId": "p1", "blockName": ROPE, "itemDict": dict(hand), "ret": False}
    Registry.dispatch("ServerItemUseOnEvent", dict(args), ROPE)
    Registry.dispatch("ServerItemUseOnEvent", dict(args), ROPE)        # 冷却没过（计时器还没跑）
    assert _ropes() == [67, 68, 69, 70]


def testOtherBlocksAreLeftToTheEngine():
    _setUp()
    world.setBlock(5, 70, 5, STONE)
    args = _click((5, 70, 5), DOWN)                            # 石头下面没有绳子：引擎照常放
    assert args["ret"] is False and world.timers == [] and world.modAttr == {}
    _setUp(hand={"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1})
    _hang(70, 3)
    assert _click((5, 70, 5))["ret"] is False and _ropes() == [68, 69, 70]               # 手里不是绳子


def testSneakingOnTheFaceARopeHangsFromExtendsIt():
    _setUp(sneaking=True)
    world.setBlock(5, 71, 5, STONE)
    _hang(70, 2)
    _click((5, 71, 5), DOWN)                                   # 潜行点石头朝下的面：从挂着的那节往下接
    assert _ropes() == [68, 69, 70]


def testNotSneakingNextToARopeLeavesTheClickToTheBlock():
    # 不潜行时 JE 先调点到的方块的 use（箱子、门、按钮、砧板……）；这边不认外侧那格的绳子，引擎照原样
    for block in (STONE, "minecraft:chest", "arris:cutting_board"):
        _setUp()
        world.setBlock(5, 70, 5, block)
        _hang(70, 2, x=4)                                      # 方块西边挂着绳子
        args = _click((5, 70, 5), WEST)
        assert args["ret"] is False and _ropes(x=4) == [69, 70] and world.timers == [] and world.modAttr == {}, block
    _setUp(sneaking=True)
    world.setBlock(5, 70, 5, "minecraft:chest")
    _hang(70, 2, x=4)
    _click((5, 70, 5), WEST)                                   # 潜行：JE 不调方块的 use，从那节绳子再往西一格
    assert _ropes(x=4) == [69, 70] and world.blockName(3, 70, 5) == ROPE


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
