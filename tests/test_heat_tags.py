# -*- coding: utf-8 -*-
# runner: both
"""热源的方块标签和状态条件（Shared/Rules/HeatSources，服务端 Server/Helpers/Heat.IsHeatSource / IsNearHeat、客户端的手持煎锅"身边有没有热源"）。

锁的事：
  1. "点着"的规则 isLit：有 lit 或 *:lit 状态且为真，或者有 extinguished 且为假；都没有不算
  2. 名单（CanProvideHeatBlockList）里的照旧（营火看 extinguished、熄着的炉灶不热）；不在名单里的：带 farmersdelight:heat_sources 的，
     有点燃状态（lit、*:lit、extinguished）的要点着（别的模组的营火式、lit 状态式炉灶），没有这类状态的就热（JE 的 isHeated）；什么标签都不带的不热
  3. 手持煎锅身边的热源：名单 ∪ 标签，不看点没点着（JE 的 isPlayerNearHeatSource；名单里的营火熄了也算，标签里的一样）
  4. 传热方块（farmersdelight:heat_conductors）：漏斗（名单）照旧，带这个标签的也把再下面一格的热传上来
  5. 托盘（farmersdelight:tray_heat_sources）：名单 ShelfBlockSet 照旧，带这个标签的方块上面的锅也画托盘
  6. 状态条件表（HeatSourceStateDict）里写了条件的方块只按条件判，锅下面、手持煎锅身边都判；名单里的、标签里的写了条件也一样；
     不在名单、标签里的满足条件就算；客户端按 aux 集合（HeatSourceAuxDict）判，还没拿到集合的当不热
引擎是 fakeengine.py 里的假的，标签由假口答。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = skilletkit.extend(fakeengine.install())
Heat = fdtest.load("Server.Helpers.Heat")
Tags = fdtest.load("Shared.Data.Tags")
Cooking = fdtest.load("Shared.Data.Cooking")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
HeatSources = fdtest.load("Shared.Rules.HeatSources")
Skillet = fdtest.load("Shared.Rules.SkilletRules")

BELOW = (10, 64, 10)
KC_STOVE = "kaleidoscope_cookery:kaleidoscope_cookery_stove"


class Conditions(object):
    """临时往状态条件表（和客户端的 aux 集合）里写几条：进去时写、出来时放回原样（就地改，表对象不换）。"""

    def __init__(self, entries, aux=None):
        self.entries, self.aux = entries, aux or {}

    def __enter__(self):
        self.saved = [(table, dict(table)) for table in (Cooking.HeatSourceStateDict, Cooking.HeatSourceAuxDict)]
        Cooking.HeatSourceStateDict.update(self.entries)
        Cooking.HeatSourceAuxDict.update(self.aux)
        return self

    def __exit__(self, *exc):
        for table, saved in self.saved:
            table.clear()
            table.update(saved)
        return False


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


def _near(name):
    """手持煎锅身边（不看点燃状态）：状态里就算写着熄了也不管。"""
    return HeatSources.heats(name, lambda: {"extinguished": True, "lit": False}, lit=False)


def testNearHeatIgnoresWhetherItIsLit():
    _reset()
    assert _near("minecraft:campfire") and _near("arris:stove"), "名单里的：熄了也算"
    assert not _near("arris:stove_extinguish") and not _near("minecraft:air") and not _near(None)
    ItemTags.setPort("client", BlockTagPort(members={Tags.HEAT_SOURCES: ["mymod:burner", KC_STOVE]}))
    assert _near("mymod:burner") and _near(KC_STOVE), "标签里的，不看点没点着"
    assert HeatSources.heatsByAux(KC_STOVE, 0) and HeatSources.heatsByAux("mymod:burner", 3), "客户端：没写条件的按名字认"

    def isHeat(pos):
        return HeatSources.heatsByAux(KC_STOVE if pos == (1, 63, 1) else "minecraft:air", 0)

    assert Skillet.nearHeat((1.5, 64.0, 1.5), isHeat), "脚下 3x3x3 里有一座带标签的炉灶"
    _reset()


def testWrittenConditionsDecideEverywhereEvenForListedAndTaggedBlocks():
    """写了状态条件的方块只按条件判，锅下面（lit=True）和手持煎锅身边（lit=False）都判；名单里的、标签里的写了条件也一样；
    哪里都不在的满足条件就算。条件拿掉以后照旧。"""
    _reset()
    ItemTags.setPort("server", BlockTagPort(members={Tags.HEAT_SOURCES: [KC_STOVE]}))
    entries = {"minecraft:campfire": {"extinguished": False, "direction": [0, 1]},        # 名单里的
               KC_STOVE: {"kaleidoscope_cookery:lit": True},                            # 标签里的
               "mymod:brazier": {"mymod:coals": {"min": 1}}}                          # 名单、标签里都没有
    with Conditions(entries):
        assert _hot("minecraft:campfire", {"extinguished": False, "direction": 1})
        assert not _hot("minecraft:campfire", {"extinguished": False, "direction": 2}), "名单里的方块写了条件也按条件判"
        assert not _hot("minecraft:campfire"), "读不到状态：不满足"
        assert _hot(KC_STOVE, {"kaleidoscope_cookery:lit": True}) and not _hot(KC_STOVE, {"kaleidoscope_cookery:lit": False})
        assert not _hot(KC_STOVE), "标签里的方块：没写条件时读不到状态就算热（JE），写了条件就不算"
        assert _hot("mymod:brazier", {"mymod:coals": 3}) and not _hot("mymod:brazier", {"mymod:coals": 0}) and not _hot("mymod:brazier")
        for name, states, hot in (("minecraft:campfire", {"extinguished": True, "direction": 0}, False),
                                  ("minecraft:campfire", {"extinguished": False, "direction": 0}, True),
                                  ("mymod:brazier", {"mymod:coals": 2}, True), ("mymod:brazier", {"mymod:coals": 0}, False)):
            assert HeatSources.heats(name, lambda: dict(states), lit=False) is hot, ("手持煎锅身边也按条件判", name, states)
    assert _hot("minecraft:campfire", {"extinguished": False, "direction": 2}) and not _hot("mymod:brazier", {"mymod:coals": 3}), "条件拿掉了：照旧"
    assert _hot(KC_STOVE), "标签里、读不到状态：又算热了"
    _reset()


def testTheClientJudgesWrittenConditionsByTheAuxSetAndWithoutOneSaysCold():
    _reset()
    with Conditions({"mymod:brazier": {"mymod:coals": {"min": 1}}, "minecraft:campfire": {"extinguished": False}},
                    aux={"minecraft:campfire": [0, 1, 2, 3]}):
        assert HeatSources.heatsByAux("minecraft:campfire", 3) and not HeatSources.heatsByAux("minecraft:campfire", 4), "写了条件：查 aux 集合"
        assert not HeatSources.heatsByAux("mymod:brazier", 1), "服务端还没把这个方块的 aux 集合发来：当不热"
        assert HeatSources.heatsByAux("minecraft:soul_campfire", 4) and not HeatSources.heatsByAux("minecraft:stone", 0), "没写条件的照名单 / 标签"
    assert HeatSources.heatsByAux("minecraft:campfire", 4), "条件拿掉了：名单里的营火照旧按名字认"
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
