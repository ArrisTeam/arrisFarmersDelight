# -*- coding: utf-8 -*-
# runner: both
"""厨锅 / 煎锅下面的热源（Server/Helpers/Heat.py）对 FD 的 HeatableBlockEntity.isHeated（java:15-36）和两个标签：

heat_sources = 岩浆块、熔岩炼药锅、炉灶、tray_heat_sources（熔岩、营火、火）；带 LIT 状态的要点着才算。
heat_conductors = 漏斗：正下方是它时改看再下面一格。支架（托盘）只认正下方那一格（CookingPotBlock.getTrayState、SkilletBlock，tray_heat_sources）。
基岩版的对应：岩浆块 minecraft:magma、熔岩炼药锅是 cauldron 的 cauldron_liquid = lava（引擎里没有 lava_cauldron，Strata 知识库的方块表里 cauldron
有 fill_level 和 cauldron_liquid = water / lava / powder_snow 两个状态）、营火的 LIT 是 extinguished 取反、炉灶的 LIT 是两个方块。引擎是 fakeengine.py 里的假的。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = skilletkit.extend(fakeengine.install())       # extend 补上 reset 和方块实体数据的假对象
Heat = fdtest.load("Server.Helpers.Heat")
Cooking = fdtest.load("Shared.Data.Cooking")

POT, BELOW, FURTHER = (10, 65, 10), (10, 64, 10), (10, 63, 10)
HOPPER, STONE = "minecraft:hopper", "minecraft:stone"
LAVA_CAULDRON = ("minecraft:cauldron", {"cauldron_liquid": "lava", "fill_level": 6})
# FD heat_sources.json 的全部（连 #tray_heat_sources 里的）在基岩版里的样子：(方块名, 状态)
SOURCES = [("minecraft:magma", None), ("minecraft:lava", None), ("minecraft:flowing_lava", None), ("minecraft:fire", None),
           ("minecraft:soul_fire", None), ("minecraft:campfire", {"extinguished": False}), ("minecraft:soul_campfire", {"extinguished": False}),
           ("arris:stove", None), LAVA_CAULDRON]
# 看着像、但不热的：熄了的营火和炉灶、盛的不是熔岩的炼药锅、空了的炼药锅、别的方块
COLD = [("minecraft:campfire", {"extinguished": True}), ("minecraft:soul_campfire", {"extinguished": True}), ("arris:stove_extinguish", None),
        ("minecraft:cauldron", {"cauldron_liquid": "water", "fill_level": 6}), ("minecraft:cauldron", {"cauldron_liquid": "powder_snow", "fill_level": 6}),
        ("minecraft:cauldron", {"cauldron_liquid": "lava", "fill_level": 0}), ("minecraft:cauldron", {"fill_level": 0}),
        (STONE, None), (HOPPER, None), ("minecraft:air", None)]


def _put(pos, block):
    name, states = block
    world.setBlock(pos[0], pos[1], pos[2], name, states=dict(states) if states else None)


def _fresh():
    world.reset()
    return skilletkit.EngineData()


def testEverySourceInFarmersDelightsHeatTagHeatsTheBlockAboveIt():
    for block in SOURCES:
        _fresh()
        _put(BELOW, block)
        assert Heat.IsHeatSource(BELOW, 0) is True, block
        assert Heat.IsHeated(BELOW, 0) is True, block


def testWhatOnlyLooksLikeASourceDoesNotHeat():
    for block in COLD:
        _fresh()
        _put(BELOW, block)
        assert Heat.IsHeatSource(BELOW, 0) is False, block
        assert Heat.IsHeated(BELOW, 0) is False, block


def testALavaCauldronIsACauldronHoldingLavaNotABlockOfItsOwn():
    """没有 minecraft:lava_cauldron 这个方块：读的是 cauldron 的状态，所以光看名字（下游追加的热源名单那样）认不出它。"""
    _fresh()
    _put(BELOW, LAVA_CAULDRON)
    assert "minecraft:cauldron" not in Cooking.CanProvideHeatBlockList and "minecraft:lava_cauldron" not in Cooking.CanProvideHeatBlockList
    assert Heat.IsHeatSource(BELOW, 0) is True
    world.setBlock(BELOW[0], BELOW[1], BELOW[2], "minecraft:cauldron", states={"cauldron_liquid": "lava", "fill_level": 6})
    assert Heat.IsHeatSource(BELOW, 0, "minecraft:cauldron") is True, "给了方块名也要再读状态"
    world.setBlock(BELOW[0], BELOW[1], BELOW[2], "minecraft:cauldron", states=None)
    assert Heat.IsHeatSource(BELOW, 0) is False, "读不到状态：不热"


def testAHopperPassesTheHeatOfTheBlockBelowItUp():
    for block in SOURCES:
        _fresh()
        _put(BELOW, (HOPPER, None))
        _put(FURTHER, block)
        assert Heat.IsHeated(BELOW, 0) is True, block
        assert Heat.IsHeated(BELOW, 0, HOPPER) is True, "调用方已经读过正下方的方块名：不再读第二遍也一样"
    for block in COLD:
        _fresh()
        _put(BELOW, (HOPPER, None))
        _put(FURTHER, block)
        assert Heat.IsHeated(BELOW, 0) is False, block


def testOnlyAHopperConductsAndOnlyOneBlockDeep():
    _fresh()
    _put(FURTHER, ("minecraft:campfire", {"extinguished": False}))
    _put(BELOW, (STONE, None))
    assert Heat.IsHeated(BELOW, 0) is False, "石头不传热：火在两格以下的普通方块下面不算"
    _put(BELOW, (HOPPER, None))
    _put(FURTHER, (HOPPER, None))
    world.setBlock(FURTHER[0], FURTHER[1] - 1, FURTHER[2], "minecraft:campfire", states={"extinguished": False})
    assert Heat.IsHeated(BELOW, 0) is False, "漏斗下面又是漏斗：JE 只往下看一格（stateFurtherBelow 不是热源）"
    assert Cooking.HeatConductorList == ["minecraft:hopper"]


def testTheShelfOnlyFollowsTheBlockDirectlyBelowNotTheHeatSourceBehindTheHopper():
    data = _fresh()
    _put(BELOW, (HOPPER, None))
    _put(FURTHER, ("minecraft:campfire", {"extinguished": False}))
    assert Heat.RefreshHeat(data, POT, BELOW, 0, HOPPER) is True
    assert data["heatEnable"] is True and data["heatParticleEnable"] == 1.0, "漏斗下面的营火烧热了锅"
    assert data["shelfEnable"] == 0.0, "托盘只在正下方是熔岩 / 营火 / 火时画（JE 的 getTrayState 只看 pos.below()）"
    sent = dict((call[2]["name"], call[2]["molang"]) for call in world.calls if call[1] == "SetEntityBlockMolang")
    assert sent == {"variable.mod_heat": 1.0, "variable.mod_shelf": 0.0}, sent
    for block, shelf in (("minecraft:campfire", 1.0), ("minecraft:soul_fire", 1.0), ("minecraft:lava", 1.0), ("minecraft:magma", 0.0), ("arris:stove", 0.0)):
        data = _fresh()
        _put(BELOW, (block, {"extinguished": False} if "campfire" in block else None))
        assert Heat.RefreshHeat(data, POT, BELOW, 0, block) is True, block
        assert data["shelfEnable"] == shelf, block


def testAnUnlitCampfireBelowKeepsTheShelfButGivesNoHeat():
    data = _fresh()
    _put(BELOW, ("minecraft:campfire", {"extinguished": True}))
    assert Heat.RefreshHeat(data, POT, BELOW, 0, "minecraft:campfire") is False
    assert data["heatEnable"] is False and data["shelfEnable"] == 1.0, "JE 的托盘按方块（tray_heat_sources），不看有没有点着"


def testTheRefreshStillSendsTheTwoMolangVariablesToEveryClientAfterTheDelay():
    data = _fresh()
    _put(BELOW, ("minecraft:lava", None))
    world.setBlock(POT[0], POT[1], POT[2], "arris:cooking_pot", data=data)
    Heat.RefreshHeat(data, POT, BELOW, 0, "minecraft:lava", delay=0.1)
    assert [call for call in world.calls if call[1] == "SetEntityBlockMolang"] == [], "方块刚放下时客户端的方块实体还没建好：要等"
    assert len(world.timers) == 1, "一份延后的推送：到点时现读方块实体数据"
    world.runTimers()
    sent = dict((call[2]["name"], call[2]["molang"]) for call in world.calls if call[1] == "SetEntityBlockMolang")
    assert sent == {"variable.mod_heat": 1.0, "variable.mod_shelf": 1.0}, sent


def testTheDelayedPushSendsWhatTheBlockIsWhenItFiresNotWhenItWasQueued():
    """排着的这一会儿里方块又变了（刚放下就切了支架、下面的火灭了）：到点发的是现在的值。方块已经不在了就什么都不发。"""
    data = _fresh()
    _put(BELOW, ("minecraft:lava", None))
    world.setBlock(POT[0], POT[1], POT[2], "arris:cooking_pot", data=data)
    Heat.RefreshHeat(data, POT, BELOW, 0, "minecraft:lava", delay=0.1)
    data["shelfEnable"], data["heatParticleEnable"] = 0.0, 0.0
    world.runTimers()
    sent = dict((call[2]["name"], call[2]["molang"]) for call in world.calls if call[1] == "SetEntityBlockMolang")
    assert sent == {"variable.mod_heat": 0.0, "variable.mod_shelf": 0.0}, sent
    data = _fresh()
    _put(BELOW, ("minecraft:lava", None))
    world.setBlock(POT[0], POT[1], POT[2], "arris:cooking_pot", data=data)
    Heat.RefreshHeat(data, POT, BELOW, 0, "minecraft:lava", delay=0.1)
    world.setBlock(POT[0], POT[1], POT[2], "minecraft:air")
    world.runTimers()
    assert [call for call in world.calls if call[1] == "SetEntityBlockMolang"] == [], "锅已经拆了：不发"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
