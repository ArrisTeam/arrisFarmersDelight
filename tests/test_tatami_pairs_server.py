# -*- coding: utf-8 -*-
# runner: both
"""榻榻米方块两两配对的服务端（Server/TatamiPairs.py）：用假引擎（tests/fakeengine.py）驱动放置、邻格变化两个事件。

JE 的 TatamiBlock：点一块没配对的榻榻米放下另一块，两块配成一对、FACING 互相指着；潜行放的不配；
另一半没了（updateShape）剩下那块拆开、FACING 不变。
"""
from __future__ import print_function

import io
import os

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
Pairs = fdtest.load("Server.TatamiPairs")
Pair = fdtest.load("Shared.Rules.TatamiPair")

T = Pair.TATAMI
STATE = {"sneak": False}
WRITES = []                                    # SetBlockStates 的调用：(位置, 方块态)


def _player(target):
    methods = dict(fakeengine.FakeWorld._Player(world, target))
    methods["isSneaking"] = lambda: STATE["sneak"]
    return methods


def _blockState(target):
    methods = dict(fakeengine.FakeWorld._BlockState(world, target))
    setStates = methods["SetBlockStates"]

    def record(pos, states, dim=0):
        WRITES.append((tuple(pos), dict(states)))
        return setStates(pos, states, dim)
    methods["SetBlockStates"] = record
    return methods


world._Player = _player
world._BlockState = _blockState


def _setUp(sneak=False):
    world.blocks.clear()
    world.entities.clear()
    world.players.clear()
    del WRITES[:]
    STATE["sneak"] = sneak
    world.addPlayer("p1")
    world.addEntity("e1", "minecraft:enderman")


def _tatami(pos, facing=0, paired=0):
    world.setBlock(pos[0], pos[1], pos[2], T, states={Pair.FACING: facing, Pair.PAIRED: paired})


def _states(pos):
    return world.blocks[(0,) + tuple(pos)]["states"]


def _place(pos, face, entityId="p1"):
    """引擎放下一块（缺省方块态）之后的放置事件：face 是点的那一面。"""
    _tatami(pos)
    args = {"x": pos[0], "y": pos[1], "z": pos[2], "fullName": T, "auxData": 0, "entityId": entityId,
            "dimensionId": 0, "face": face}
    Registry.dispatch("EntityPlaceBlockAfterServerEvent", args, T)


def _neighbor(pos, neighbor, toName, fromName=T):
    world.setBlock(neighbor[0], neighbor[1], neighbor[2], toName)
    args = {"dimensionId": 0, "posX": pos[0], "posY": pos[1], "posZ": pos[2], "blockName": T, "auxValue": 0,
            "neighborPosX": neighbor[0], "neighborPosY": neighbor[1], "neighborPosZ": neighbor[2],
            "fromBlockName": fromName, "fromBlockAuxValue": 0, "toBlockName": toName, "toAuxValue": 0}
    Registry.dispatch("BlockNeighborChangedServerEvent", args, T)


def _pair(lower=(5, 64, 5)):
    """竖着一对：下面那块朝上、上面那块朝下。"""
    upper = (lower[0], lower[1] + 1, lower[2])
    _tatami(lower, Pair.UP, 1)
    _tatami(upper, Pair.DOWN, 1)
    del WRITES[:]
    return lower, upper


# ---- 放置 ----

def testPlacingOnTopOfAnUnpairedTatamiMakesAStandingPair():
    _setUp()
    _tatami((5, 64, 5), facing=Pair.SOUTH)
    _place((5, 65, 5), face=Pair.UP)
    assert _states((5, 65, 5)) == {Pair.FACING: Pair.DOWN, Pair.PAIRED: 1}
    assert _states((5, 64, 5)) == {Pair.FACING: Pair.UP, Pair.PAIRED: 1}


def testPlacingAgainstASideMakesALyingPair():
    _setUp()
    _tatami((5, 64, 5))
    _place((6, 64, 5), face=Pair.EAST)                             # 点它的东面，新块在东边
    assert _states((6, 64, 5)) == {Pair.FACING: Pair.WEST, Pair.PAIRED: 1}
    assert _states((5, 64, 5)) == {Pair.FACING: Pair.EAST, Pair.PAIRED: 1}
    _tatami((5, 64, 9))
    _place((5, 64, 8), face=Pair.NORTH)
    assert _states((5, 64, 8)) == {Pair.FACING: Pair.SOUTH, Pair.PAIRED: 1}
    assert _states((5, 64, 9)) == {Pair.FACING: Pair.NORTH, Pair.PAIRED: 1}


def testSneakingPlacesALoneOneFacingTheClickedBlock():
    _setUp(sneak=True)
    _tatami((5, 64, 5))
    _place((5, 64, 6), face=Pair.SOUTH)
    assert _states((5, 64, 6)) == {Pair.FACING: Pair.NORTH, Pair.PAIRED: 0}
    assert _states((5, 64, 5)) == {Pair.FACING: Pair.DOWN, Pair.PAIRED: 0}


def testAThirdOneCannotTakeAPairedTatami():
    _setUp()
    lower, upper = _pair()
    _place((6, 65, 5), face=Pair.EAST)
    assert _states((6, 65, 5)) == {Pair.FACING: Pair.WEST, Pair.PAIRED: 0}
    assert _states(lower) == {Pair.FACING: Pair.UP, Pair.PAIRED: 1} and _states(upper) == {Pair.FACING: Pair.DOWN, Pair.PAIRED: 1}


def testPlacedAgainstOtherBlocksOrByMobsItStaysAlone():
    _setUp()
    world.setBlock(5, 63, 5, "minecraft:stone")
    _place((5, 64, 5), face=Pair.UP)
    assert _states((5, 64, 5)) == {Pair.FACING: Pair.DOWN, Pair.PAIRED: 0}
    _tatami((8, 64, 5))
    _place((8, 65, 5), face=Pair.UP, entityId="e1")
    assert _states((8, 65, 5))[Pair.PAIRED] == 0 and _states((8, 64, 5))[Pair.PAIRED] == 0


# ---- 邻格变化 ----

def testBreakingOneHalfLeavesTheOtherAloneKeepingItsFacing():
    _setUp()
    lower, upper = _pair()
    _neighbor(lower, upper, "minecraft:air")
    assert _states(lower) == {Pair.FACING: Pair.UP, Pair.PAIRED: 0}


def testOtherNeighboursDoNotSplitAPair():
    _setUp()
    lower, upper = _pair()
    _neighbor(lower, (6, 64, 5), "minecraft:stone", fromName="minecraft:air")
    _neighbor(lower, (5, 63, 5), "minecraft:air", fromName="minecraft:stone")
    _neighbor(upper, lower, T)                                     # 另一半还是榻榻米
    assert WRITES == []


def testAPartnerOnItsWayOnAPistonDoesNotSplitThePairUntilItIsGone():
    _setUp()
    lower, upper = _pair()
    _neighbor(lower, upper, Pair.MOVING_BLOCK)
    assert WRITES == []
    _neighbor(lower, upper, "minecraft:piston_arm_collision", fromName=Pair.MOVING_BLOCK)
    assert _states(lower)[Pair.PAIRED] == 0


def testAPairWithNothingWhereItFacesSplitsOnAnyNeighbourChange():
    # 活塞推来的、/setblock 摆出来的不成对的状态：随便哪个邻格变了都理顺
    _setUp()
    _tatami((5, 64, 5), Pair.NORTH, 1)
    _neighbor((5, 64, 5), (5, 63, 5), "minecraft:dirt", fromName="minecraft:stone")
    assert _states((5, 64, 5)) == {Pair.FACING: Pair.NORTH, Pair.PAIRED: 0}


def testLoneTatamiIgnoreTheirNeighbours():
    _setUp()
    _tatami((5, 64, 5))
    _neighbor((5, 64, 5), (5, 63, 5), "minecraft:air", fromName="minecraft:stone")
    assert WRITES == []


def testTheModuleIsImportedByModServer():
    path = os.path.join(fdtest.BP, fdtest.SCRIPTS, "Server", "ModServer.py")
    with io.open(path, encoding="utf-8") as f:
        source = f.read()
    assert "from . import TatamiPairs" in source and '@Listen("EntityPlaceBlockAfterServerEvent")' in source


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
