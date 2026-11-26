# -*- coding: utf-8 -*-
# runner: both
"""门面上配方以外的登记口和 ext.tags（Api/ExtensionApi/Registries.py）：

- registerKnife / registerHeatSource / registerStove 往旧接口的表里追加（同一个列表对象），名字写法不对拒绝，已经有的不重复加；
  加的刀所有刀切的砧板配方都认；registerCompostable 写进堆肥表，概率要在 (0, 100]；客户端一律 server_only；
- registerHeatSource 带 states：只写进状态条件表（不进名单），写法不对是 invalid_states（带 message、表不动），和不带 states 的旧调用并存；
- ext.tags 就是 ItemTags 的答案，带词表的名字常量。
"""
from __future__ import print_function

import fdtest

Facade = fdtest.load("Api.ExtensionApi.Facade")
Cutting = fdtest.load("Shared.Data.Cutting")
Cooking = fdtest.load("Shared.Data.Cooking")
Farming = fdtest.load("Shared.Data.Farming")
Station = fdtest.load("Shared.Rules.CuttingStation")
HeatSources = fdtest.load("Shared.Rules.HeatSources")
Tags = fdtest.load("Shared.Data.Tags")
SERVER, CLIENT = Facade.getExtensionApi("server"), Facade.getExtensionApi("client")


class Kept(object):
    """进去时记下几张表，出来时放回（就地，对象不换）。"""

    def __enter__(self):
        self.saved = [(table, list(table)) for table in (Cutting.knifeList, Cooking.CanProvideHeatBlockList, Cooking.StoveList)]
        self.maps = [(table, dict(table)) for table in (Farming.ComposterItemDict, Cooking.HeatSourceStateDict, Cooking.HeatSourceAuxDict)]
        return self

    def __exit__(self, *exc):
        for table, items in self.saved:
            table[:] = items
        for table, items in self.maps:
            table.clear()
            table.update(items)
        return False


def testTheListsGrowInPlace():
    with Kept():
        knives = Cutting.knifeList
        assert SERVER.registerKnife("mymod:jade_knife") == {"ok": True, "error": None, "id": "mymod:jade_knife"}
        assert SERVER.registerKnife(u"mymod:jade_knife")["ok"] and knives.count("mymod:jade_knife") == 1, "不重复加；py2 的 unicode 也收"
        assert Cutting.knifeList is knives
        beef = Cutting.CuttingBoardDict[("minecraft:beef", 0)]
        assert Station.fitsTool("mymod:jade_knife", "sword", beef, lambda name: False), "刀切的配方的工具表就是 knifeList"
        assert SERVER.registerHeatSource("mymod:hot_rock")["ok"] and "mymod:hot_rock" in Cooking.CanProvideHeatBlockList
        assert SERVER.registerStove("mymod:brick_stove")["ok"] and "mymod:brick_stove" in Cooking.StoveList
        for bad in ("jade_knife", "#common:knife", "", None, 3, "a:b:c", "a: b"):
            assert SERVER.registerKnife(bad)["error"] == "invalid_name", bad
        assert SERVER.registerCompostable("mymod:leaf", 30)["ok"] and Farming.ComposterItemDict[("mymod:leaf", 0)] == 30
        assert SERVER.registerCompostable("mymod:leaf", 65, 2)["ok"] and Farming.ComposterItemDict[("mymod:leaf", 2)] == 65
        for chance in (0, 101, -1, "30", True, None):
            assert SERVER.registerCompostable("mymod:leaf", chance)["error"] == "invalid_chance", chance
        assert SERVER.registerCompostable("mymod:leaf", 30, -1)["error"] == "invalid_name"
        for call in (lambda: CLIENT.registerKnife("mymod:x"), lambda: CLIENT.registerHeatSource("mymod:x"), lambda: CLIENT.registerStove("mymod:x"),
                     lambda: CLIENT.registerCompostable("mymod:x", 30)):
            assert call()["error"] == "server_only"


def testAHeatSourceWithStatesOnlyWritesItsConditions():
    """带 states：只写进状态条件表（规整过：unicode → str、tuple → list），不进旧接口的名单；满足条件才热，锅下面、手持煎锅身边都判；
    同一个方块再登记换成新的条件。"""
    with Kept():
        states = {u"mymod:coals": {"min": 1}, "mymod:fuel": ("coal", u"charcoal")}
        assert SERVER.registerHeatSource(u"mymod:brazier", states=states) == {"ok": True, "error": None, "id": "mymod:brazier"}
        assert Cooking.HeatSourceStateDict["mymod:brazier"] == {"mymod:coals": {"min": 1}, "mymod:fuel": ["coal", "charcoal"]}
        assert "mymod:brazier" not in Cooking.CanProvideHeatBlockList, "只登记条件：不进旧接口那张不看状态的名单"
        hot, cold = {"mymod:coals": 2, "mymod:fuel": "coal"}, {"mymod:coals": 0, "mymod:fuel": "coal"}
        for lit in (True, False):
            assert HeatSources.heats("mymod:brazier", lambda: hot, lit) and not HeatSources.heats("mymod:brazier", lambda: cold, lit), lit
        assert SERVER.registerHeatSource("mymod:brazier", states={"mymod:coals": 3})["ok"]
        assert Cooking.HeatSourceStateDict["mymod:brazier"] == {"mymod:coals": 3} and not HeatSources.heats("mymod:brazier", lambda: hot)
        assert SERVER.hasCapability("heat_source_states") and not CLIENT.hasCapability("heat_source_states")


def testStatesAndThePlainCallLiveSideBySide():
    """同一个方块：不带 states 的旧调用进名单，带 states 的写条件，谁先谁后都一样——名单里只有一份，写明的条件照样算数；
    已经在名单、标签里的方块（炉灶）也能只登记条件。"""
    with Kept():
        for first, second in (("plain", "states"), ("states", "plain")):
            Cooking.HeatSourceStateDict.pop("mymod:oven", None)
            for step in (first, second, "states", "plain"):
                if step == "plain":
                    assert SERVER.registerHeatSource("mymod:oven")["ok"]
                else:
                    assert SERVER.registerHeatSource("mymod:oven", states={"mymod:lit": True})["ok"]
            assert Cooking.CanProvideHeatBlockList.count("mymod:oven") == 1, (first, second)
            assert HeatSources.heats("mymod:oven", lambda: {"mymod:lit": True}) and not HeatSources.heats("mymod:oven", lambda: {"mymod:lit": False})
            assert not HeatSources.heats("mymod:oven", lambda: {"mymod:lit": False}, lit=False), "手持煎锅身边也按写明的条件判"
        assert SERVER.registerHeatSource("arris:stove", states={"arris:fuel": {"min": 1}})["ok"]
        assert Cooking.CanProvideHeatBlockList.count("arris:stove") == 1 and not HeatSources.heats("arris:stove", lambda: {})
    assert "mymod:oven" not in Cooking.HeatSourceStateDict and HeatSources.heats("arris:stove", lambda: {}), "放回原样"


def testWrongStatesAreRefusedAndChangeNothing():
    with Kept():
        before = (dict(Cooking.HeatSourceStateDict), list(Cooking.CanProvideHeatBlockList))
        for bad in ({}, [], "lava", False, {"x": None}, {"x": 1.5}, {"x": []}, {"x": [1, None]}, {"x": {}}, {"x": {"least": 1}},
                    {"x": {"min": 3, "max": 1}}, {"x": {"min": "1"}}, {"": 1}, {3: 1}):
            answer = SERVER.registerHeatSource("mymod:oven", states=bad)
            assert answer["ok"] is False and answer["error"] == "invalid_states" and answer["id"] == "mymod:oven", (bad, answer)
            assert answer["message"], bad
        assert (dict(Cooking.HeatSourceStateDict), list(Cooking.CanProvideHeatBlockList)) == before, "写错了：两张表都不动"
        assert SERVER.registerHeatSource("oven", states={"x": 1})["error"] == "invalid_name"
        assert CLIENT.registerHeatSource("mymod:oven", states={"x": 1})["error"] == "server_only"
        assert CLIENT.registerHeatSource("mymod:oven", states={})["error"] == "server_only", "客户端先答 server_only，不看写法"


def testTagsAreItemTagsWithTheVocabularyNames():
    tags = SERVER.tags
    assert tags.RAW_BEEF == "common:raw_beef" == Tags.RAW_BEEF and tags.EGG == "minecraft:egg"
    assert tags.has("arris:minced_beef", tags.RAW_BEEF) and not tags.has("minecraft:carrot", tags.RAW_BEEF)
    assert tags.itemsOf(tags.EGG) == ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
    assert tags.RAW_BEEF in tags.tagsOf("minecraft:beef") and tags.blockHas("arris:stove", tags.HEAT_SOURCES)
    assert "common:fruit" in tags.names() and "common:chili" not in tags.names() and "common:raw_beef" in tags.names() and tags.names() == sorted(tags.names())
    assert isinstance(tags.generation(), int) and CLIENT.tags.has("arris:minced_beef", tags.RAW_BEEF)
    # 团队规范的名字（单数）：蘑菇、骨头改过名，不留旧名；农夫乐事登记了的粗标签有常量，蛋的粗标签叫 ANY_EGG（EGG 是原版的）
    assert tags.MUSHROOM == "common:mushroom" and tags.BONE == "common:bone" and not hasattr(tags, "MUSHROOMS") and not hasattr(tags, "BONES")
    assert (tags.BEEF, tags.PORK, tags.FISH, tags.SEED, tags.ANY_EGG) == (
        "common:beef", "common:pork", "common:fish", "common:seed", "common:egg")
    assert tags.has("arris:beef_patty", tags.BEEF) and "common:egg" in tags.names() and not hasattr(tags, "COOKING_STANDARD")
    # 面条：用户 2026-11-26 定，意面和面条不是一种，农夫乐事不登记 common:noodle
    assert not [name for name in ("CHILI", "FLOUR", "LETTUCE", "MEAT", "MEATBALL", "NOODLE") if hasattr(tags, name)], "规范里农夫乐事不登记的不给常量"
    assert "common:noodle" not in tags.names() and not tags.has("arris:raw_pasta", "common:noodle")
    # 团队的规矩（2026-11-26）：模组的 common: 物品标签一律单数，七个复数名改了名、常量跟着改，不留旧名（复数的 common:seeds 并进了 common:seed）
    assert (tags.CROP, tags.FLOWER, tags.CABBAGE_SEED, tags.TOMATO_SEED, tags.MUTTON_CHOP, tags.COOKED_MUTTON_CHOP) == (
        "common:crop", "common:flower", "common:cabbage_seed", "common:tomato_seed", "common:mutton_chop", "common:cooked_mutton_chop")
    old = ("SEEDS", "CROPS", "FLOWERS", "CABBAGE_SEEDS", "TOMATO_SEEDS", "MUTTON_CHOPS", "COOKED_MUTTON_CHOPS")
    assert not [name for name in old if hasattr(tags, name)] and "common:seeds" not in tags.names()
    assert tags.has("minecraft:wheat_seeds", tags.SEED) and tags.has("arris:cabbage_seeds", tags.SEED)
    odd = sorted(name for name, value in vars(tags).items() if name.isupper() and value.split(":", 1)[1].upper() != name)
    assert odd == ["ANY_EGG", "LEGACY_KNIFE"], "EXTENSION-API.md §7：常量名是冒号后那段的大写，例外就这两个（%s）" % odd


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
