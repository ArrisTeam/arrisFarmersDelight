# -*- coding: utf-8 -*-
# runner: both
"""绳上的番茄藤（Shared/Rules/TomatoVine.py + Server/Crops.py 的 OnCropNeighborChanged / OnVineRemoved）对照 JE 的
HangingTomatoBlock / TomatoBlock（FD 1.3.4）：下面是番茄（地上那株第 3 级起）或者另一节藤才撑得住，撑不住碎掉；
藤没了（不是长一级、摘果子那种换成另一节藤）就在原地放回绳子（enableTomatoRopePermanence 缺省开）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest
import farmengine

LEVEL = farmengine.Level()
farmengine.install(LEVEL)

Registry = fdtest.load("Server.EventRegistry")
Crops = fdtest.load("Server.Crops")
TomatoVine = fdtest.load("Shared.Rules.TomatoVine")

ROPE = "arris:rope"
AIR = "minecraft:air"
BASE = "arris:budding_tomatoes_stage"
VINE = "arris:tomatoes_vine_stage"


def _fresh():
    LEVEL.__init__()
    return LEVEL


# ---- 规则 ----

def testWhatHoldsAVine():
    for stage in range(4):
        assert TomatoVine.holds(VINE + str(stage))
    for stage in (3, 4, 5, 6):
        assert TomatoVine.holds(BASE + str(stage)), stage            # JE 的 TOMATO_CROP：budding 长到头以后
    for stage in (0, 1, 2):
        assert not TomatoVine.holds(BASE + str(stage)), stage        # JE 的 BuddingTomatoBlock 不是 TOMATO_CROP
    for name in (AIR, ROPE, "minecraft:farmland", "minecraft:stone", None, ""):
        assert not TomatoVine.holds(name), name


def testTheRopeComesBackOnlyWhereTheVineIsGone():
    for name in (AIR, "minecraft:water", "minecraft:flowing_water"):
        assert TomatoVine.ropeBack(name), name
    for name in (VINE + "0", VINE + "3", "minecraft:stone", ROPE, None):
        assert not TomatoVine.ropeBack(name), name                   # 长一级 / 摘果子（换成另一节藤）、/setblock 换上的不管


def testTheVineBlocksTellTheScriptWhenRemoved():
    assert TomatoVine.VINES == tuple(VINE + str(stage) for stage in range(4))
    for name in TomatoVine.VINES:
        path = os.path.join(fdtest.BP, "netease_blocks", name.replace("arris:", "arris_") + ".json")
        with io.open(path, encoding="utf-8") as handle:
            components = json.load(handle)["minecraft:block"]["components"]
        assert components["netease:listen_block_remove"] == {"value": True}, name
        assert components["netease:neighborchanged_sendto_script"] == {"value": True}, name


# ---- 服务端 ----

def _neighbor(name, pos, toName):
    args = {"blockName": name, "posX": pos[0], "posY": pos[1], "posZ": pos[2], "dimensionId": 0,
            "neighborPosX": pos[0], "neighborPosY": pos[1] - 1, "neighborPosZ": pos[2], "toBlockName": toName}
    Registry.dispatch("BlockNeighborChangedServerEvent", args, name)


def _removed(name, pos):
    args = {"fullName": name, "x": pos[0], "y": pos[1], "z": pos[2], "auxValue": 0, "dimension": 0}
    Registry.dispatch("BlockRemoveServerEvent", args, name)


def testHarvestingTheTomatoBelowKeepsTheVine():
    level = _fresh().put((0, 1, 0), BASE + "3").put((0, 2, 0), VINE + "3")
    _neighbor(VINE + "3", (0, 2, 0), BASE + "3")                     # 地上那株摘完回到第 3 级
    _neighbor(VINE + "3", (0, 2, 0), VINE + "1")
    assert level.nameAt((0, 2, 0)) == VINE + "3" and level.setCalls == []


def testAVineWithNothingUnderItBreaksWithDrops():
    level = _fresh().put((0, 2, 0), VINE + "3")
    _neighbor(VINE + "3", (0, 2, 0), AIR)
    assert level.setCalls == [((0, 2, 0), AIR, 0, 1, True)]          # handling 1：照常掉东西


def testOtherCropsStillNeedFarmland():
    level = _fresh().put((0, 1, 0), "arris:cabbages_stage2")
    _neighbor("arris:cabbages_stage2", (0, 1, 0), "minecraft:farmland")
    assert level.setCalls == []
    _neighbor("arris:cabbages_stage2", (0, 1, 0), "minecraft:dirt")
    assert level.nameAt((0, 1, 0)) == AIR


def testARemovedVineLeavesItsRope():
    level = _fresh()                                                 # 挖掉以后那一格是空气
    _removed(VINE + "2", (0, 3, 0))
    assert level.nameAt((0, 3, 0)) == AIR                            # 下一刻才看
    level.runTimers()
    assert level.nameAt((0, 3, 0)) == ROPE


def testGrowingOrPickingDoesNotPutARope():
    level = _fresh().put((0, 3, 0), VINE + "0")                      # 摘果子：第 3 级换成第 0 级
    _removed(VINE + "3", (0, 3, 0))
    level.runTimers()
    assert level.nameAt((0, 3, 0)) == VINE + "0" and level.setCalls == []
    level.put((0, 3, 0), "minecraft:stone")                          # 被 /setblock 换掉：不盖
    _removed(VINE + "0", (0, 3, 0))
    level.runTimers()
    assert level.nameAt((0, 3, 0)) == "minecraft:stone"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
