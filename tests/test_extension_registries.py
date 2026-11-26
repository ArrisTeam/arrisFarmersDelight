# -*- coding: utf-8 -*-
# runner: both
"""门面上配方以外的登记口和 ext.tags（Api/ExtensionApi/Registries.py）：

- registerKnife / registerHeatSource / registerStove 往旧接口的表里追加（同一个列表对象），名字写法不对拒绝，已经有的不重复加；
  加的刀所有刀切的砧板配方都认；registerCompostable 写进堆肥表，概率要在 (0, 100]；客户端一律 server_only；
- ext.tags 就是 ItemTags 的答案，带词表的名字常量。
"""
from __future__ import print_function

import fdtest

Facade = fdtest.load("Api.ExtensionApi.Facade")
Cutting = fdtest.load("Shared.Data.Cutting")
Cooking = fdtest.load("Shared.Data.Cooking")
Farming = fdtest.load("Shared.Data.Farming")
Station = fdtest.load("Shared.Rules.CuttingStation")
Tags = fdtest.load("Shared.Data.Tags")
SERVER, CLIENT = Facade.getExtensionApi("server"), Facade.getExtensionApi("client")


class Kept(object):
    """进去时记下几张表，出来时放回（就地，对象不换）。"""

    def __enter__(self):
        self.saved = [(table, list(table)) for table in (Cutting.knifeList, Cooking.CanProvideHeatBlockList, Cooking.StoveList)]
        self.compost = dict(Farming.ComposterItemDict)
        return self

    def __exit__(self, *exc):
        for table, items in self.saved:
            table[:] = items
        Farming.ComposterItemDict.clear()
        Farming.ComposterItemDict.update(self.compost)
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


def testTagsAreItemTagsWithTheVocabularyNames():
    tags = SERVER.tags
    assert tags.RAW_BEEF == "common:raw_beef" == Tags.RAW_BEEF and tags.EGG == "minecraft:egg"
    assert tags.has("arris:minced_beef", tags.RAW_BEEF) and not tags.has("minecraft:carrot", tags.RAW_BEEF)
    assert tags.itemsOf(tags.EGG) == ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
    assert tags.RAW_BEEF in tags.tagsOf("minecraft:beef") and tags.blockHas("arris:stove", tags.HEAT_SOURCES)
    assert "common:chili" in tags.names() and "common:raw_beef" in tags.names() and tags.names() == sorted(tags.names())
    assert isinstance(tags.generation(), int) and CLIENT.tags.has("arris:minced_beef", tags.RAW_BEEF)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
