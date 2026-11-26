# -*- coding: utf-8 -*-
# runner: both
"""标签的游戏内自检（Server/Debug/McdkTagsTest.py、Client/Debug/McdkTagsTest.py）离线能跑通、报得出差：引擎口换成假的（答的是静态表，
外加别的包登记的一件），全部 ok；口少了本包登记的成员时 ok 是假、报出是哪个标签。真正的数在游戏里跑（见两个文件的说明）。"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest

fakeengine.install()
Tags = fdtest.load("Shared.Data.Tags")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Grilling = fdtest.load("Shared.Rules.Grilling")
ServerTest = fdtest.load("Server.Debug.McdkTagsTest")
ServerPort = fdtest.load("Server.Helpers.Tags")


def _loadClient():
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId, engine.clientApi = object(), "level", object()
    saved = sys.modules.get(engine.__name__)
    sys.modules[engine.__name__] = engine
    try:
        return fdtest.load("Client.Debug.McdkTagsTest"), fdtest.load("Client.Tags")
    finally:
        if saved is not None:
            sys.modules[engine.__name__] = saved
        else:
            sys.modules.pop(engine.__name__, None)


ClientTest, ClientPort = _loadClient()


class FullPort(object):
    """引擎口：答的是静态表（番茄里多一件别的包的），drop = (标签, 成员) 时少答那一件。"""

    def __init__(self, drop=None):
        self.drop = drop
        self.probes, self.firstProbeAt, self.readyAt = 1, 10.0, 12.5

    def ready(self):
        return True

    def itemsOf(self, tag):
        members = [name for name in (Tags.ITEM_TAGS.get(tag) or Tags.VANILLA_TAGS.get(tag) or ()) if (tag, name) != self.drop]
        return tuple(members) + (("mymod:tomato",) if tag == Tags.TOMATO else ())

    def blocksOf(self, tag):
        return tuple(Tags.BLOCK_TAGS.get(tag, ()))

    def tagsOf(self, itemName, aux=0):
        return tuple(tag for tag, members in Tags.ITEM_TAGS.items() if itemName in members)

    def blockTagsOf(self, blockName):
        return tuple(tag for tag, members in Tags.BLOCK_TAGS.items() if blockName in members)

    def campfireRecipes(self, itemName, aux=0):
        return [{"output": "minecraft:cooked_beef:0"}] if itemName == "minecraft:beef" else []


class NoBlockTagsPort(FullPort):
    """按方块问（GetBlockTags）什么都答不出：反查照常。"""

    def blockTagsOf(self, blockName):
        return None


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)
        Grilling.setPort(side, None)


def testTheServerSelfTestsPassOnAFullEngine():
    saved = ServerPort.PORT
    ServerPort.PORT = FullPort()
    try:
        members = ServerTest.mcdk_test_tags_members()
        assert members["ok"] and members["items"][Tags.TOMATO]["extra"] == ["mymod:tomato"], members["missing"]
        assert ServerTest.mcdk_test_tags_knives()["ok"]
        campfire = ServerTest.mcdk_test_tags_campfire()
        assert campfire["ok"] and campfire["recipes"]["minecraft:beef"]["parsed"] == "minecraft:cooked_beef"
        assert campfire["recipes"]["arris:minced_beef"]["result"] == "arris:beef_patty", "表里有的照表"
        assert ServerTest.mcdk_test_tags_heat()["ok"]
        assert members["items"][Tags.MEALS]["missing"] == [] and members["items"][Tags.MEALS]["engine"] == len(Tags.ITEM_TAGS[Tags.MEALS])
        blocks = ServerTest.mcdk_test_tags_blocks()
        own = sorted(tag for tag in Tags.BLOCK_TAGS if tag.startswith("farmersdelight:"))
        assert blocks["ok"] and sorted(blocks["tags"]) == own and len(own) == 7, sorted(blocks["tags"])
        assert all(row["notTagged"] == [] and row["missing"] == [] for row in blocks["tags"].values())
        ServerPort.PORT = NoBlockTagsPort()
        blocks = ServerTest.mcdk_test_tags_blocks()
        assert blocks["ok"], "按方块问不认只报，反查认得就算过"
        assert blocks["tags"][Tags.DROPS_CAKE_SLICE]["notTagged"] == sorted(Tags.BLOCK_TAGS[Tags.DROPS_CAKE_SLICE])
        ServerPort.PORT = FullPort(drop=(Tags.RAW_BEEF, "minecraft:beef"))
        members = ServerTest.mcdk_test_tags_members()
        assert not members["ok"] and members["missing"] == [Tags.RAW_BEEF], members["missing"]
        assert members["items"][Tags.RAW_BEEF]["missing"] == ["minecraft:beef"]
    finally:
        ServerPort.PORT = saved
        _reset()


def testTheClientSelfTestReportsItsTimeline():
    saved = ClientPort.PORT
    ClientPort.PORT = FullPort()
    try:
        result = ClientTest.mcdk_test_tags_client()
        assert result["ok"], result["missing"]
        assert result["timing"]["probes"] == 1 and result["timing"]["secondsAfterLoad"] == 12.5 - ClientPort.LOADED_AT
        assert result["beefCampfire"]["parsed"] == "minecraft:cooked_beef" and all(result["knives"].values())
    finally:
        ClientPort.PORT = saved
        _reset()


class ItemFactory(object):
    """compFactory 的替身：CreateItem(levelId).GetItemBasicInfo(名字, aux) 认得 items 里的（给 {"itemName": 名字}），别的 None。"""

    def __init__(self, items):
        self.items = items

    def CreateItem(self, _levelId):
        return self

    def GetItemBasicInfo(self, name, aux=0):
        return {"itemName": name} if name in self.items else None


class ThreadPort(object):
    """Grilling 的口，answers=False 是在这个线程里答不了（单机时另一端的口：什么都给 None）。"""

    def __init__(self, answers):
        self.answers = answers

    def ready(self):
        return True

    def campfireRecipes(self, itemName, aux=0):
        name, product = ServerTest.PROBE_GRILL
        if not self.answers:
            return None
        return [{"input": itemName, "output": product}] if itemName == name else []


def testTheProbeGrillSelfTestOnBothThreads():
    """mcdk_test_tags_probe_grill（两端各一份）：探针包的番茄只靠营火配方能烤；客户端线程里服务端的口答不了（None），先在客户端线程、
    再在服务端线程调，两边都该拿到产物（以前客户端线程先问时把 None 记进缓存，服务端跟着不认）。没装探针包时跳过。"""
    name, product = ServerTest.PROBE_GRILL
    assert ClientTest.PROBE_GRILL == ServerTest.PROBE_GRILL
    saved = ServerTest.compFactory, ClientTest.compFactory
    server, client = ThreadPort(False), ThreadPort(True)                   # 客户端线程：服务端的口答不了
    _reset()
    Grilling.setPort("server", server)
    Grilling.setPort("client", client)
    try:
        ServerTest.compFactory = ClientTest.compFactory = ItemFactory(())
        assert ClientTest.mcdk_test_tags_probe_grill()["skipped"] and ServerTest.mcdk_test_tags_probe_grill()["skipped"], "没装探针包"
        ServerTest.compFactory = ClientTest.compFactory = ItemFactory((name,))
        first = ClientTest.mcdk_test_tags_probe_grill()
        assert first["ok"] and first["raw"]["server"] == "None" and first["cachedAfter"] == repr(product), first
        server.answers, client.answers = True, False                        # 服务端线程：服务端的口答得出
        second = ServerTest.mcdk_test_tags_probe_grill()
        assert second["ok"] and second["result"] == product and second["cachedBefore"] == repr(product), second
    finally:
        ServerTest.compFactory, ClientTest.compFactory = saved
        _reset()


class ModuleApi(object):
    """serverApi / clientApi 的替身：ImportModule(名字) 给 modules 里的（没有给 None），记下问过的名字。"""

    def __init__(self, modules=None):
        self.modules, self.asked = dict(modules or {}), []

    def ImportModule(self, name):
        self.asked.append(name)
        return self.modules.get(name)


# 装了森罗物语厨房时引擎里的样子：规范的粗标签多了森罗自己的东西，common:meat 是它用 # 引的四种肉（农夫乐事登记进去的也在）加兔肉
THEIRS = {Tags.BEEF: ("kaleidoscope_cookery:raw_cow_offal",), Tags.FISH: ("kaleidoscope_cookery:sashimi",)}


class StandardPort(FullPort):
    """规范标签的引擎口：答静态表（# 都展开了）。kc 为真是装着森罗：粗标签多了它的东西，有 common:meat；lose = (标签, 成员) 时少答那一件，
    extra = {标签: 多答的}（别的包登记进细标签、却没并进粗标签时用）。"""

    def __init__(self, kc=True, lose=None, extra=None):
        FullPort.__init__(self)
        self.kc, self.lose, self.extra = kc, lose, extra or {}

    def itemsOf(self, tag):
        if tag == "common:meat":
            parts = (Tags.BEEF, Tags.CHICKEN, Tags.LAMB, Tags.PORK) if self.kc else ()
            found = (("minecraft:rabbit",) if self.kc else ()) + tuple(name for part in parts for name in self.itemsOf(part))
        else:
            found = tuple(Tags.ITEM_TAGS.get(tag) or Tags.VANILLA_TAGS.get(tag) or ()) + (THEIRS.get(tag, ()) if self.kc else ()) \
                + self.extra.get(tag, ())
        return tuple(name for name in found if (tag, name) != self.lose)


class KaleidoscopeMatcher(object):
    """森罗服务端认料模块的替身：item_matches_ingredient 照引擎口答，_TAG_ITEMS_CACHE 是它问过的标签（cache 给了就用它）。"""

    def __init__(self, port, cache=None):
        self.port = port
        self._TAG_ITEMS_CACHE = dict(cache or {})

    def item_matches_ingredient(self, itemName, ingredient):
        tag = ingredient[1:]
        self._TAG_ITEMS_CACHE.setdefault(tag, list(self.port.itemsOf(tag)))
        return itemName in self._TAG_ITEMS_CACHE[tag]


def testTheStandardSelfTestReportsBothPacks():
    """mcdk_test_tags_standard（服务端）：规范的 18 个标签引擎里的成员；没装森罗时只看农夫乐事这边；装着时它的认料函数认农夫乐事登记进去的
    每件东西（common:meat 认四种肉）、不认火腿和河豚，它的标签缓存没过时；少并一件、# 漏了、缓存过时都报出来、ok 是假。"""
    saved = ServerPort.PORT, ServerTest.serverApi
    try:
        ServerPort.PORT, ServerTest.serverApi = StandardPort(kc=False), ModuleApi()
        alone = ServerTest.mcdk_test_tags_standard()
        assert alone["ok"] and alone["meatLost"] is None and "没装" in alone["kaleidoscope"], alone
        assert sorted(alone["tags"]) == sorted(Tags.COOKING_STANDARD) and alone["tags"]["common:chili"]["engine"] == 0
        assert ServerTest.serverApi.asked == [ServerTest.KC_MATCHER]
        port = StandardPort()
        ServerPort.PORT = port
        ServerTest.serverApi = ModuleApi({ServerTest.KC_MATCHER: KaleidoscopeMatcher(port, {Tags.BEEF: list(port.itemsOf(Tags.BEEF))})})
        both = ServerTest.mcdk_test_tags_standard()
        assert both["ok"] and both["meatLost"] == [] and both["nestedLost"] == {}, both
        assert both["tags"][Tags.BEEF]["extra"] == ["kaleidoscope_cookery:raw_cow_offal"]
        kc = both["kaleidoscope"]
        assert kc["refused"] == [] and kc["acceptedWrongly"] == [] and kc["stale"] == [] and kc["cachedBefore"] == [Tags.BEEF], kc
        assert kc["asked"] > 40
        # 引擎里生意面进了 common:noodle（用户 2026-11-26 定了不进：意面和面条不是一种）：森罗认了它就是认错了
        port = StandardPort(lose=("common:meat", "arris:minced_beef"), extra={Tags.RAW_BEEF: ("mymod:steak",), "common:noodle": ("arris:raw_pasta",)})
        ServerPort.PORT = port
        ServerTest.serverApi = ModuleApi({ServerTest.KC_MATCHER: KaleidoscopeMatcher(port, {Tags.FISH: ["minecraft:cod"]})})
        broken = ServerTest.mcdk_test_tags_standard()
        assert not broken["ok"] and broken["meatLost"] == ["arris:minced_beef"], broken["meatLost"]
        assert broken["nestedLost"] == {"common:beef <- #common:raw_beef": ["mymod:steak"]}, broken["nestedLost"]
        refused = broken["kaleidoscope"]["refused"]
        assert broken["kaleidoscope"]["stale"] == [Tags.FISH] and "arris:minced_beef common:meat" in refused, broken["kaleidoscope"]
        assert "arris:cod_slice common:fish" in refused and "minecraft:cod common:fish" not in refused, "缓存过时：鱼片它不认了"
        assert broken["kaleidoscope"]["acceptedWrongly"] == ["arris:raw_pasta common:noodle"], broken["kaleidoscope"]
    finally:
        ServerPort.PORT, ServerTest.serverApi = saved
        _reset()


def testTheClientStandardSelfTestReadsTheJeiCacheOnly():
    """mcdk_test_tags_standard（客户端）：客户端引擎里的成员；装了森罗时只读它 JEI 的标签缓存（不替它问），记着的和引擎现在的不一样就是过时。"""
    saved = ClientPort.PORT, ClientTest.clientApi
    try:
        ClientPort.PORT, ClientTest.clientApi = StandardPort(kc=False), ModuleApi()
        alone = ClientTest.mcdk_test_tags_standard()
        assert alone["ok"] and "没装" in alone["kaleidoscopeJei"] and sorted(alone["tags"]) == sorted(Tags.COOKING_STANDARD)
        jei = types.ModuleType("kc_jei")
        jei._ITEM_TAG_CACHE = {Tags.TOMATO: ["arris:tomato"], Tags.RICE: ["arris:rice"]}       # 番茄记早了：没有别的包的那一件
        ClientPort.PORT = StandardPort(kc=False, extra={Tags.TOMATO: ("mymod:tomato",)})
        ClientTest.clientApi = ModuleApi({ClientTest.KC_JEI: jei})
        result = ClientTest.mcdk_test_tags_standard()
        assert not result["ok"] and result["kaleidoscopeJei"] == {"cached": [Tags.RICE, Tags.TOMATO], "stale": [Tags.TOMATO]}, result
        assert sorted(jei._ITEM_TAG_CACHE) == [Tags.RICE, Tags.TOMATO], "只读，不替它问"
    finally:
        ClientPort.PORT, ClientTest.clientApi = saved
        _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
