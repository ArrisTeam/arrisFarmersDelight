# -*- coding: utf-8 -*-
# runner: both
"""按标签认东西（Shared/Rules/ItemTags.py）和引擎口（Shared/Rules/TagPort.py，两端的 Server/Helpers/Tags.py、Client/Tags.py 用它）。

锁的事：
  1. 没有口时等于静态词表（Shared/Data/Tags：农夫乐事单独在场时的答案），原版自带的 minecraft:egg 也答得出
  2. 口没准备好时枚举（itemsOf / blocksOf）只给静态表、不问它，按单件问的照样问引擎、并上静态表、不缓存；准备好的那一刻换代，
     之后是静态表 ∪ 引擎、缓存住；refresh() 换代、重新问
  3. 两个口都在（单机）用服务端的；口答 None、抛异常、答读不懂的东西时不炸，按静态表答
  4. EnginePort：引擎返回值的形状（[{"itemName"}] / [{"blockName"}] / [标签名] / None）；3.10 以前没有的接口当答不了；
     准备好 = 反查探针标签里出现了那件原版物品（没有反查接口时 = GetItemTags 答得了那件原版物品）；探测限频、算好之后不再探
  5. 两端的入口最先导入各自的引擎口，口装上了
"""
from __future__ import print_function

import io
import os
import sys
import types

import fdtest

Tags = fdtest.load("Shared.Data.Tags")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
TagPort = fdtest.load("Shared.Rules.TagPort")

PROBE_TAG, PROBE_ITEM = Tags.READY_PROBE


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)


class FakePort(object):
    """ItemTags 的口：answers 是 {(种类, 键): 答案}，种类 items / tags / blocks / blocktags；没写的答 None。calls 记每种问了几次。"""

    def __init__(self, ready=True, answers=None, error=None):
        self.isReady = ready
        self.answers = dict(answers or {})
        self.error = error
        self.calls = {}

    def _answer(self, kind, key):
        self.calls[kind] = self.calls.get(kind, 0) + 1
        if self.error is not None:
            raise self.error
        return self.answers.get((kind, key))

    def ready(self):
        return self.isReady

    def itemsOf(self, tag):
        return self._answer("items", tag)

    def tagsOf(self, itemName, aux=0):
        return self._answer("tags", itemName)

    def blocksOf(self, tag):
        return self._answer("blocks", tag)

    def blockTagsOf(self, blockName):
        return self._answer("blocktags", blockName)


def testWithoutAPortItAnswersFromTheStaticTable():
    _reset()
    assert not ItemTags.ready()
    assert ItemTags.itemsOf(Tags.RAW_BEEF) == ("minecraft:beef", "arris:minced_beef")
    assert ItemTags.itemsOf(Tags.RAW_MEAT) == Tags.ITEM_TAGS[Tags.RAW_MEAT], "顺序就是表里的顺序"
    assert ItemTags.itemsOf(Tags.EGG) == ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"), "原版自带的标签也答得出"
    assert ItemTags.itemsOf("kaleidoscope_cookery:meat") == () and ItemTags.blocksOf("nobody:tag") == frozenset()
    assert ItemTags.has("arris:minced_beef", Tags.RAW_BEEF) and ItemTags.has("minecraft:brown_egg", Tags.EGG)
    assert ItemTags.has("arris:iron_knife", Tags.KNIFE) and ItemTags.has("arris:iron_knife", Tags.LEGACY_KNIFE)
    assert not ItemTags.has("minecraft:pufferfish", Tags.RAW_FISH) and not ItemTags.has(None, Tags.RAW_FISH)
    assert ItemTags.tagsOf("arris:rice") == frozenset((Tags.RICE, Tags.CROPS, Tags.SEEDS))
    assert ItemTags.tagsOf("minecraft:apple") == frozenset()
    assert ItemTags.blocksOf(Tags.HEAT_SOURCES) >= frozenset(("minecraft:campfire", "minecraft:soul_campfire", "minecraft:magma"))
    assert ItemTags.blockHas("arris:stove", Tags.HEAT_SOURCES) and not ItemTags.blockHas("arris:stove_extinguish", Tags.HEAT_SOURCES)
    assert ItemTags.blockTagsOf("minecraft:magma") == frozenset((Tags.HEAT_SOURCES,))
    assert ItemTags.blockTagsOf("minecraft:campfire") == frozenset((Tags.HEAT_SOURCES, Tags.TRAY_HEAT_SOURCES)), "营火点没点着看状态"


def testANotReadyPortAnswersSingleItemsUncachedButNoEnumerationsThenTakesOver():
    """口没准备好：枚举（itemsOf / blocksOf）只给静态表、不问它（客户端进世界前反查漏成员）；按单件问的照样问、并上静态表、不缓存
    （那时引擎按单件给的可能不全，但不会多给）。准备好的那一刻换代，之后枚举也接上引擎、都缓存住；refresh() 换代、重新问。"""
    _reset()
    port = FakePort(ready=False, answers={("items", Tags.TOMATO): [u"kaleidoscope_cookery:tomato", "arris:tomato"],
                                          ("tags", "kaleidoscope_cookery:tomato"): ["common:tomato", "kaleidoscope_cookery:vegetable"],
                                          ("blocks", Tags.HEAT_SOURCES): ["mymod:burner"],
                                          ("blocktags", "mymod:oven"): ["farmersdelight:heat_sources"]})
    ItemTags.setPort("client", port)
    first = ItemTags.generation()
    assert not ItemTags.ready()
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato",)
    assert ItemTags.blocksOf(Tags.HEAT_SOURCES) == frozenset(Tags.BLOCK_TAGS[Tags.HEAT_SOURCES])
    assert not ItemTags.blockHas("mymod:burner", Tags.HEAT_SOURCES), "只在反查里的：没准备好不认"
    assert "items" not in port.calls and "blocks" not in port.calls, "没准备好时不问枚举"
    assert ItemTags.has("kaleidoscope_cookery:tomato", Tags.TOMATO), "按单件问的照样问引擎"
    assert ItemTags.blockHas("mymod:oven", Tags.HEAT_SOURCES) and Tags.HEAT_SOURCES in ItemTags.blockTagsOf("mymod:oven")
    assert ItemTags.tagsOf("arris:tomato") == frozenset((Tags.TOMATO, Tags.VEGETABLE, Tags.CROPS)), "引擎没答（None）：静态表的"
    asked = port.calls["tags"]
    ItemTags.tagsOf("kaleidoscope_cookery:tomato")
    ItemTags.has("kaleidoscope_cookery:tomato", Tags.TOMATO)
    assert port.calls["tags"] == asked + 2, "没准备好时不缓存：每次都问"
    assert ItemTags.generation() == first
    port.isReady = True
    port.calls = {}
    assert ItemTags.generation() == first + 1, "准备好的那一刻换代"
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "kaleidoscope_cookery:tomato"), "静态表的在前，引擎多出来的接在后面"
    assert ItemTags.has("kaleidoscope_cookery:tomato", Tags.TOMATO)
    assert ItemTags.tagsOf("kaleidoscope_cookery:tomato") == frozenset(("common:tomato", "kaleidoscope_cookery:vegetable"))
    for _ in range(3):
        ItemTags.itemsOf(Tags.TOMATO)
        ItemTags.tagsOf("kaleidoscope_cookery:tomato")
    assert port.calls == {"items": 1, "tags": 1}, port.calls
    port.answers[("items", Tags.TOMATO)] = ["arris:tomato", "kaleidoscope_cookery:tomato", "mymod:tomato"]
    assert ItemTags.itemsOf(Tags.TOMATO)[-1] == "kaleidoscope_cookery:tomato", "缓存住了"
    ItemTags.refresh()
    assert ItemTags.generation() == first + 2
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "kaleidoscope_cookery:tomato", "mymod:tomato")
    _reset()


def testTheEngineOnlyAddsToTheStaticTable():
    """引擎那边万一没挂上农夫乐事的东西（答的里面没有），静态表的照样认：装了口只会多认，不会少认。"""
    _reset()
    ItemTags.setPort("server", FakePort(answers={("items", Tags.RAW_BEEF): [], ("tags", "arris:minced_beef"): [],
                                                 ("blocks", Tags.HEAT_SOURCES): ["mymod:burner"]}))
    assert ItemTags.ready()
    assert ItemTags.itemsOf(Tags.RAW_BEEF) == ("minecraft:beef", "arris:minced_beef")
    assert ItemTags.has("arris:minced_beef", Tags.RAW_BEEF) and Tags.RAW_BEEF in ItemTags.tagsOf("arris:minced_beef")
    assert ItemTags.blocksOf(Tags.HEAT_SOURCES) == frozenset(Tags.BLOCK_TAGS[Tags.HEAT_SOURCES] + ("mymod:burner",))
    assert ItemTags.blockHas("mymod:burner", Tags.HEAT_SOURCES)
    _reset()


def testHasAsksBothWays():
    """按物品问（3.10 以前的服务端只有 GetItemTags：物品 JSON 里声明的标签）和按标签反查，任一个说带就是带；方块一样。"""
    _reset()
    ItemTags.setPort("server", FakePort(answers={("tags", "mymod:cleaver"): ["arris:knife"],
                                                 ("blocktags", "mymod:oven"): ["farmersdelight:heat_sources"]}))
    assert ItemTags.has("mymod:cleaver", Tags.LEGACY_KNIFE), "反查答不了（None）时按物品问的也算"
    assert "mymod:cleaver" not in ItemTags.itemsOf(Tags.LEGACY_KNIFE)
    assert ItemTags.blockHas("mymod:oven", Tags.HEAT_SOURCES) and Tags.HEAT_SOURCES in ItemTags.blockTagsOf("mymod:oven")
    assert not ItemTags.blockHas("mymod:oven", Tags.TRAY_HEAT_SOURCES)
    _reset()


def testTheServerPortWinsWhenBothAreThere():
    _reset()
    server = FakePort(answers={("items", Tags.TOMATO): ["server:tomato"]})
    client = FakePort(answers={("items", Tags.TOMATO): ["client:tomato"]})
    ItemTags.setPort("client", client)
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "client:tomato")
    before = ItemTags.generation()
    ItemTags.setPort("server", server)
    assert ItemTags.generation() > before, "装上口换代"
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "server:tomato")
    ItemTags.setPort("server", None)
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "client:tomato"), "卸下服务端的口又用客户端的"
    try:
        ItemTags.setPort("both", server)
    except ValueError:
        pass
    else:
        raise AssertionError("端只有 server / client")
    _reset()


def testABrokenPortFallsBackToTheStaticTable():
    _reset()
    for port in (FakePort(error=RuntimeError("engine")),
                 FakePort(answers={("items", Tags.TOMATO): "arris:tomato", ("tags", "arris:tomato"): {"a": 1},
                                   ("blocks", Tags.HEAT_SOURCES): 7, ("items", Tags.MILK): [None, 3, "arris:milk_bottle"]}),
                 object()):
        ItemTags.setPort("server", port)
        ItemTags.itemsOf(Tags.TOMATO)
        assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato",)
        assert ItemTags.tagsOf("arris:tomato") == frozenset((Tags.TOMATO, Tags.VEGETABLE, Tags.CROPS))
        assert ItemTags.blocksOf(Tags.HEAT_SOURCES) == frozenset(Tags.BLOCK_TAGS[Tags.HEAT_SOURCES])
        assert ItemTags.itemsOf(Tags.MILK) == ("minecraft:milk_bucket", "arris:milk_bottle"), "读不懂的成员丢掉，不重复"
        assert ItemTags.has("arris:onion", Tags.VEGETABLE) and ItemTags.blockHas("minecraft:lava", Tags.HEAT_SOURCES)

    class Flaky(FakePort):
        def ready(self):
            raise RuntimeError("not yet")
    ItemTags.setPort("server", Flaky())
    assert not ItemTags.ready() and ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato",)
    _reset()


class FakeClock(object):
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class FakeItemComp(object):
    """引擎的物品组件。tags：{物品名: [标签]}（没有的物品 None）；members：{标签: [物品名]}；legacy=True 是 3.10 以前（没有反查接口）。"""

    def __init__(self, tags=None, members=None, legacy=False):
        self.tags = tags if tags is not None else {}
        self.members = members if members is not None else {}
        self.lookups = 0
        if not legacy:
            self.LookupItemsByItemTag = self._lookup

    def GetItemTags(self, itemName, auxValue=0):
        return self.tags.get(itemName)

    def _lookup(self, tag):
        self.lookups += 1
        return [{"itemName": name} for name in self.members.get(tag, ())]


class FakeBlockComp(object):
    def __init__(self, members):
        self.members = members

    def LookupBlocksByBlockTag(self, tag):
        return [{"blockName": name} for name in self.members.get(tag, ())]


class FakeBlockInfo(object):
    def GetBlockTags(self, blockName):
        return {"minecraft:magma": ["farmersdelight:heat_sources", "minecraft:is_pickaxe_item_destructible"]}.get(blockName)


def testTheEnginePortReadsTheEnginesShapes():
    items = FakeItemComp(tags={"minecraft:beef": ["minecraft:is_meat", PROBE_TAG]},
                         members={PROBE_TAG: [PROBE_ITEM, "arris:minced_beef", PROBE_ITEM]})
    port = TagPort.EnginePort(lambda: items, lambda: FakeBlockComp({Tags.HEAT_SOURCES: ["arris:stove"]}), FakeBlockInfo)
    assert port.itemsOf(PROBE_TAG) == (PROBE_ITEM, "arris:minced_beef") and port.itemsOf("nobody:tag") == ()
    assert port.tagsOf("minecraft:beef") == ("minecraft:is_meat", PROBE_TAG) and port.tagsOf("nosuchmod:nothing") is None
    assert port.blocksOf(Tags.HEAT_SOURCES) == ("arris:stove",)
    assert port.blockTagsOf("minecraft:magma")[0] == "farmersdelight:heat_sources" and port.blockTagsOf("nosuchmod:block") is None
    assert port.ready()
    client = TagPort.EnginePort(lambda: items, lambda: FakeBlockComp({}))
    assert client.blockTagsOf("minecraft:magma") is None, "客户端没有 GetBlockTags"

    def broken():
        raise RuntimeError("no component")
    for getter in (broken, lambda: object(), None):
        empty = TagPort.EnginePort(getter, getter, getter)
        assert (empty.itemsOf("a:b"), empty.tagsOf("a:b"), empty.blocksOf("a:b"), empty.blockTagsOf("a:b")) == (None,) * 4
        assert not empty.ready()


def testTheEnginePortIsReadyOnlyWhenTheProbeMemberHasArrived():
    clock, items = FakeClock(), FakeItemComp(members={PROBE_TAG: ["arris:minced_beef"]})    # 客户端进世界前：反查漏掉原版成员
    port = TagPort.EnginePort(lambda: items, clock=clock, every=1.0)
    assert not port.ready() and items.lookups == 1
    clock.now += 0.5
    assert not port.ready() and items.lookups == 1, "限频：一秒探一次"
    items.members[PROBE_TAG] = [PROBE_ITEM, "arris:minced_beef"]
    assert not port.ready(), "还没到下一次探的时候"
    clock.now += 0.6
    assert port.ready() and items.lookups == 2
    items.members.clear()
    assert port.ready() and items.lookups == 2, "算好之后一直算好、不再探"
    assert (port.probes, port.firstProbeAt, port.readyAt) == (2, 100.0, clock.now), "给游戏内自检看的记录"


def testBeforeTenThePortIsReadyWhenVanillaItemsAnswer():
    """3.10 以前没有 LookupItemsByItemTag（也没有 netease_tags）：GetItemTags 答得了原版物品（不是 None）就算好；反查答不了。"""
    items = FakeItemComp(legacy=True)
    port = TagPort.EnginePort(lambda: items)
    assert not port.ready()
    items.tags[PROBE_ITEM] = ["minecraft:is_meat"]
    items.tags["mymod:cleaver"] = ["arris:knife"]
    assert port.ready() and port.itemsOf(PROBE_TAG) is None
    _reset()
    ItemTags.setPort("server", port)
    assert ItemTags.has("mymod:cleaver", Tags.LEGACY_KNIFE), "物品 JSON 里声明了 arris:knife 的刀照旧认（和以前的 IsKnife 一样）"
    assert ItemTags.itemsOf(Tags.LEGACY_KNIFE) == Tags.ITEM_TAGS[Tags.LEGACY_KNIFE]
    _reset()


def testTheClientTakesOverWhenItsTagsArrive():
    """客户端的整个过程：进世界前枚举按静态表，按单件问的引擎答多少算多少（原版物品那时是 None）；探针到了换代，枚举换成引擎的
    （别的模组的番茄），原版物品的标签也有了——早先的答案没留在缓存里。"""
    _reset()
    clock = FakeClock()
    items = FakeItemComp(tags={"kaleidoscope_cookery:tomato": ["common:tomato"]},
                         members={Tags.TOMATO: ["arris:tomato", "kaleidoscope_cookery:tomato"], PROBE_TAG: ["arris:minced_beef"]})
    ItemTags.setPort("client", TagPort.EnginePort(lambda: items, clock=clock))
    early = ItemTags.generation()
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato",)
    assert ItemTags.has("kaleidoscope_cookery:tomato", Tags.TOMATO), "自定义物品按单件问，早就答得全"
    assert ItemTags.tagsOf(PROBE_ITEM) == frozenset((Tags.RAW_BEEF, Tags.RAW_MEAT)), "原版物品那时引擎答 None：只有静态表的"
    items.members[PROBE_TAG].append(PROBE_ITEM)
    items.tags[PROBE_ITEM] = ["minecraft:is_meat", PROBE_TAG]
    clock.now += 1.0
    assert ItemTags.generation() == early + 1
    assert ItemTags.itemsOf(Tags.TOMATO) == ("arris:tomato", "kaleidoscope_cookery:tomato")
    assert "minecraft:is_meat" in ItemTags.tagsOf(PROBE_ITEM), "早先的答案没缓存"
    _reset()


def _source(*parts):
    with io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, *parts), encoding="utf-8") as handle:
        return handle.read()


def testBothEntryPointsInstallTheirPortFirst():
    server, client = _source("Server", "ModServer.py"), _source("Client", "ModClient.py")
    serverImports = [line for line in server.splitlines() if line.startswith("from .") and "noqa: F401" in line]
    clientImports = [line for line in client.splitlines() if line.startswith("from .") and "noqa: F401" in line]
    assert serverImports[0].startswith("from .Helpers import Tags "), serverImports[:2]
    assert clientImports[0].startswith("from . import Tags "), clientImports[:2]


def testTheTwoEnginePortsInstallThemselves():
    _reset()
    import fakeengine
    fakeengine.install()
    ServerTags = fdtest.load("Server.Helpers.Tags")
    assert ItemTags._ports["server"] is ServerTags.PORT
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId = object(), "level"
    saved = sys.modules.get(engine.__name__)
    sys.modules[engine.__name__] = engine
    try:
        ClientTags = fdtest.load("Client.Tags")
    finally:
        if saved is not None:
            sys.modules[engine.__name__] = saved
        else:
            sys.modules.pop(engine.__name__, None)
    assert ItemTags._ports["client"] is ClientTags.PORT and ItemTags._ports["server"] is ServerTags.PORT
    assert not ItemTags.ready(), "假引擎没有标签接口：两个口都答不了，按静态表"
    assert ItemTags.itemsOf(Tags.RAW_BEEF) == Tags.ITEM_TAGS[Tags.RAW_BEEF]
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
