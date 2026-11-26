# -*- coding: utf-8 -*-
# runner: both
"""热源的方块标签（Shared/Rules/HeatSources，服务端 Server/Helpers/Heat.IsHeatSource、两端的手持煎锅"身边有没有热源"）。

锁的事：
  1. "点着"的规则 isLit：有 lit 或 *:lit 状态且为真，或者有 extinguished 且为假；都没有不算
  2. 名单（CanProvideHeatBlockList）里的照旧（营火看 extinguished、熄着的炉灶不热）；不在名单里的：带 farmersdelight:heat_sources 的，
     有点燃状态（lit、*:lit、extinguished）的要点着（别的模组的营火式、lit 状态式炉灶），没有这类状态的就热（JE 的 isHeated）；什么标签都不带的不热
  3. 手持煎锅身边的热源：名单 ∪ 标签，不看点没点着（JE 的 isPlayerNearHeatSource；名单里的营火熄了也算，标签里的一样）
  4. 传热方块（farmersdelight:heat_conductors）：漏斗（名单）照旧，带这个标签的也把再下面一格的热传上来
  5. 托盘（farmersdelight:tray_heat_sources）：名单 ShelfBlockSet 照旧，带这个标签的方块上面的锅也画托盘
引擎是 fakeengine.py 里的假的，标签由假口答。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = skilletkit.extend(fakeengine.install())
Heat = fdtest.load("Server.Helpers.Heat")
Tags = fdtest.load("Shared.Data.Tags")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
HeatSources = fdtest.load("Shared.Rules.HeatSources")
Skillet = fdtest.load("Shared.Rules.SkilletRules")

BELOW = (10, 64, 10)
KC_STOVE = "kaleidoscope_cookery:kaleidoscope_cookery_stove"


class BlockTagPort(object):
    """只答方块标签：members = {标签: [方块名]}（反查），tagsOf = {方块名: [标签]}（按方块问，服务端的 GetBlockTags）。"""

    def __init__(self, members=None, blockTags=None):
        self.members = members or {}
        self.blockTags = blockTags or {}

    def ready(self):
        return True

    def blocksOf(self, tag):
        return self.members.get(tag)

    def blockTagsOf(self, blockName):
        return self.blockTags.get(blockName)


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)


def _hot(name, states=None):
    world.reset()
    skilletkit.EngineData()
    world.setBlock(BELOW[0], BELOW[1], BELOW[2], name, states=dict(states) if states is not None else None)
    return Heat.IsHeatSource(BELOW, 0)


def testLit():
    for states in ({"lit": True}, {"lit": 1}, {"kaleidoscope_cookery:lit": True}, {"mymod:lit": "true"}, {"extinguished": False},
                   {"extinguished": 0, "direction": 2}):
        assert HeatSources.isLit(states), states
    for states in ({"lit": False}, {"kaleidoscope_cookery:lit": 0}, {"extinguished": True}, {"lit_level": 1}, {"direction": 2}, {}, None):
        assert not HeatSources.isLit(states), states


def testHasLitState():
    for states in ({"lit": False}, {"kaleidoscope_cookery:lit": 1}, {"extinguished": True}, {"extinguished": 0, "direction": 2}):
        assert HeatSources.hasLitState(states), states
    for states in ({"lit_level": 1}, {"direction": 2, "age": 3}, {}, None):
        assert not HeatSources.hasLitState(states), states


def testTaggedBlocksHeatTheBlockAboveThem():
    _reset()
    ItemTags.setPort("server", BlockTagPort(members={Tags.HEAT_SOURCES: ["mymod:burner", KC_STOVE, "mymod:brazier"]}))
    assert _hot("mymod:burner") and _hot("mymod:burner", {"age": 3}), "没有点燃状态的：在标签里就热"
    assert _hot(KC_STOVE, {"kaleidoscope_cookery:lit": True}) and not _hot(KC_STOVE, {"kaleidoscope_cookery:lit": False})
    assert _hot(KC_STOVE), "读不到状态就是没有点燃状态（JE：没有 LIT 属性的在标签里就算）"
    assert _hot("mymod:brazier", {"extinguished": False}) and not _hot("mymod:brazier", {"extinguished": True})
    assert not _hot("mymod:oven", {"lit": True}) and not _hot("mymod:oven"), "不带标签的不热，哪怕有 lit"
    _reset()


def testTheServerAlsoAsksTheBlockForItsTags():
    """按方块问（GetBlockTags：方块 JSON 里的 tag:xxx，3.10 以前也有）也算。"""
    _reset()
    ItemTags.setPort("server", BlockTagPort(blockTags={"mymod:oven": [Tags.HEAT_SOURCES], "mymod:coals": [Tags.HEAT_SOURCES]}))
    assert _hot("mymod:coals") and _hot("mymod:oven", {"mymod:lit": True}) and not _hot("mymod:oven", {"mymod:lit": False})
    _reset()


def testTheListStillDecidesForItsOwnBlocks():
    _reset()
    assert _hot("minecraft:magma") and _hot("arris:stove") and _hot("minecraft:campfire", {"extinguished": False})
    assert not _hot("minecraft:campfire", {"extinguished": True}) and not _hot("arris:stove_extinguish") and not _hot("minecraft:stone")
    _reset()


def testATaggedConductorPassesTheHeatUpLikeAHopper():
    _reset()
    under = (BELOW[0], BELOW[1] - 1, BELOW[2])

    def heated(conductor):
        world.reset()
        skilletkit.EngineData()
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], conductor)
        world.setBlock(under[0], under[1], under[2], "minecraft:fire")
        return Heat.IsHeated(BELOW, 0)

    assert heated("minecraft:hopper") and not heated("create:chute"), "名单里只有漏斗"
    assert HeatSources.conducts("minecraft:hopper") and not HeatSources.conducts("create:chute") and not HeatSources.conducts(None)
    ItemTags.setPort("server", BlockTagPort(members={Tags.HEAT_CONDUCTORS: ["create:chute"]}))
    assert heated("create:chute") and HeatSources.conducts("create:chute"), "机械动力把溜槽登记进 farmersdelight:heat_conductors 就传热"
    assert not heated("minecraft:stone")
    _reset()


def testATaggedBlockBelowGetsTheTray():
    _reset()
    pot = (BELOW[0], BELOW[1] + 1, BELOW[2])

    def shelf(name):
        world.reset()
        data = skilletkit.EngineData()
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], name)
        Heat.RefreshHeat(data, pot, BELOW, 0, name)
        return data["shelfEnable"]

    assert shelf("minecraft:soul_fire") == 1.0 and shelf("mymod:brazier") == 0.0 and shelf("minecraft:magma") == 0.0
    ItemTags.setPort("server", BlockTagPort(members={Tags.TRAY_HEAT_SOURCES: ["mymod:brazier"]}))
    assert shelf("mymod:brazier") == 1.0, "别的模组的火盆登记进 farmersdelight:tray_heat_sources：上面的锅画托盘"
    assert shelf("minecraft:magma") == 0.0
    _reset()


def testNearHeatIgnoresWhetherItIsLit():
    _reset()
    assert "minecraft:campfire" in HeatSources.NEAR and "arris:stove" in HeatSources.NEAR, "名单里的"
    assert "arris:stove_extinguish" not in HeatSources.NEAR and "minecraft:air" not in HeatSources.NEAR and None not in HeatSources.NEAR
    ItemTags.setPort("client", BlockTagPort(members={Tags.HEAT_SOURCES: ["mymod:burner", KC_STOVE]}))
    assert "mymod:burner" in HeatSources.NEAR and KC_STOVE in HeatSources.NEAR, "标签里的，不看点没点着"
    near = Skillet.nearHeat((1.5, 64.0, 1.5), lambda pos: KC_STOVE if pos == (1, 63, 1) else "minecraft:air", HeatSources.NEAR)
    assert near, "脚下 3x3x3 里有一座带标签的炉灶"
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
