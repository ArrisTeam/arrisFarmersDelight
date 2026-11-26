# -*- coding: utf-8 -*-
# runner: both
"""下游在服务端追加的数据表怎么到客户端（Shared/Rules/TableDiff + TableMerge + SyncTables）：一份行为包当服务端（Syncer 在下游追加之前建，
下游照 Ends Delight 的写法经联动契约追加），另一份当客户端（tablekit.Package：同一份源码、各自的表），消息经 Wire 规矩核对 + JSON 来回
（tablekit.transport）。核对：客户端的表和服务端的内容一致、tool 引用的是客户端自己的 knifeList、重复并是空操作、之后又追加的补得上、
传不了的值跳过并记下而不抛异常、不是同一版的表不并、坏消息不理。站点客户端的判断认不认得新东西在 test_table_sync_stations.py。
"""
from __future__ import print_function

import fdtest
import tablekit as K


def _pair(limit=None):
    """(服务端包, 客户端包, 服务端的 Syncer)：Syncer 在下游追加之前建，就像模块导入时记基线。"""
    server, client = K.Package(), K.Package()
    diff = server.load("Shared.Rules.TableDiff")
    return server, client, (diff.Syncer() if limit is None else diff.Syncer(limit=limit))


def _sync(server, client, syncer):
    assert syncer.refresh() in (True, False)
    return K.deliver(syncer.messages(), client)


def _ops(syncer):
    return dict((message["table"], len(message["ops"])) for message in syncer.messages())


def testNothingIsSentWhenNobodyAddedAnything():
    server, client, syncer = _pair()
    assert not syncer.changed() and syncer.refresh() is False and syncer.messages() == [] and syncer.rev == 0 and syncer.problems == []
    assert syncer.counts() == {} and K.snapshot(server) == K.snapshot(client), "两份包导入后的表一样：客户端的基线就是服务端的基线"


def testThePristineTablesAllEncodeAndTheirToolListsAreRegistered():
    """基线里编不了的条目会被当成"改动"发出去；内置的砧板配方的 tool 要么没有，要么就是登记过的那几个列表之一（不然新加一个列表忘了登记，客户端拿到的是副本）。"""
    server = K.Package()
    tables = server.load("Shared.Rules.SyncTables")
    for name, kind, container in tables.TABLES:
        for value in (container.values() if kind == "map" else container):
            tables.CODEC.encode(value)
        if kind == "map":
            for key in container:
                tables.CODEC.encode(key)
    registered = [id(obj) for obj in tables.REFS.values()]
    for key, recipe in server.load("Shared.Data.Cutting").CuttingBoardDict.items():
        assert recipe.get("tool") is None or id(recipe["tool"]) in registered, "%r 的 tool 是没登记的列表" % (key,)


def testDownstreamAdditionsReachTheClientAndTheTablesEndUpEqual():
    server, client, syncer = _pair()
    K.downstream(server)
    results = _sync(server, client, syncer)
    assert syncer.rev == 1 and syncer.problems == [] and all(message["rev"] == 1 for message in syncer.messages())
    assert all(not result["problems"] and result["changed"] for result in results), results
    assert K.snapshot(server) == K.snapshot(client), "客户端的表和服务端的内容一模一样（含 (名字, aux) 元组键、配方里的元组、盘装表里的 None）"
    cutting = client.load("Shared.Data.Cutting")
    assert K.KNIFE in cutting.knifeList and K.CUT_KEY in cutting.CuttingBoardDict
    assert all(isinstance(key, tuple) for key in cutting.CuttingBoardDict), "键换回元组"
    assert client.load("Shared.Data.Cooking").CanCookedFoodDict[K.COOKABLE] == K.COOKED
    assert K.STOVE in client.load("Shared.Data.Cooking").StoveList and K.STOVE in client.load("Shared.Data.Cooking").CanProvideHeatBlockList


def testTheToolOfAnAddedRecipeIsTheClientsOwnKnifeListNotACopy():
    server, client, syncer = _pair()
    K.downstream(server)
    _sync(server, client, syncer)
    cutting = client.load("Shared.Data.Cutting")
    assert cutting.CuttingBoardDict[K.CUT_KEY]["tool"] is cutting.knifeList, "和服务端一样：下游拿到 knifeList 就把它当 tool"
    assert cutting.CuttingBoardDict[K.CUT_AXE_KEY]["tool"] is cutting.axeList
    assert cutting.CuttingBoardDict[("minecraft:beef", 0)]["tool"] is cutting.knifeList, "内置的原来就是"
    station = client.load("Shared.Rules.CuttingStation")
    assert station.isKnifeRecipe(cutting.CuttingBoardDict[K.CUT_KEY]) and not station.isKnifeRecipe(cutting.CuttingBoardDict[K.CUT_AXE_KEY])
    server_cutting = server.load("Shared.Data.Cutting")
    assert server_cutting.CuttingBoardDict[K.CUT_KEY]["tool"] is server_cutting.knifeList, "（联动契约没有被动过：服务端下游拿到的还是同一个对象）"


def testTheDiffCarriesOnlyWhatWasAddedOrChanged():
    server, client, syncer = _pair()
    clientRows = client.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
    rows = len(clientRows)
    stewAt = [index for index, row in enumerate(clientRows) if row["CookResult"][0] == "minecraft:mushroom_stew"][0]
    K.downstream(server)
    syncer.refresh()
    assert _ops(syncer) == {"CuttingBoardDict": 2, "knifeList": 1, "axeList": 1, "CanCookedFoodDict": 1, "StoveList": 1,
                            "CanProvideHeatBlockList": 1, "CookingPotRecipeList": 3, "platePackagedFoodDict": 2}, _ops(syncer)
    by = dict((message["table"], message) for message in syncer.messages())
    pot = by["CookingPotRecipeList"]
    assert pot["base"] == rows and [op["at"] for op in pot["ops"]] == [stewAt, rows, rows + 1], "下标：新加的两行 + 被 AddCookingPotRecipe 加了一种写法的蘑菇煲"
    assert by["knifeList"]["ops"] == [K.KNIFE] and by["StoveList"]["ops"] == [K.STOVE] and by["axeList"]["ops"] == ["ends_delight:chorus_axe"]
    assert sorted(op["k"]["$pair"] for op in by["CuttingBoardDict"]["ops"]) == ["ends_delight:chorus_log|0", "ends_delight:ender_pearl|0"], "内置的几百条一条也不发"


def testApplyingTheSameMessagesAgainChangesNothing():
    server, client, syncer = _pair()
    K.downstream(server)
    _sync(server, client, syncer)
    cutting, pots = client.load("Shared.Data.Cutting"), client.load("Shared.Data.CookingPotRecipes")
    entry, row, tool = cutting.CuttingBoardDict[K.CUT_KEY], pots.CookingPotRecipeList[-1], cutting.CuttingBoardDict[K.CUT_KEY]["tool"]
    before = K.snapshot(client)
    for _ in range(2):
        again = K.deliver(syncer.messages(), client)
        assert all(not result["changed"] and not result["problems"] for result in again), again
    assert K.snapshot(client) == before == K.snapshot(server)
    assert cutting.CuttingBoardDict[K.CUT_KEY] is entry and pots.CookingPotRecipeList[-1] is row and entry["tool"] is tool, "已经有一样的就不动它"


def testTablesInAnyOrderAndRepeatedConverge():
    server, client, syncer = _pair()
    K.downstream(server)
    syncer.refresh()
    messages = syncer.messages()
    K.deliver(list(reversed(messages)) + messages + list(reversed(messages)), client)
    assert K.snapshot(client) == K.snapshot(server)


def testAVariantAddedToABuiltInRecipeIsMergedInPlaceAndKeepsTheSlots():
    server, client, syncer = _pair()
    stew, ways = K.mushroomStew(client), K.mushroomStew(client)["Recipe"]
    slots = stew["Slots"]
    assert slots and K.MUSHROOM_VARIANT not in ways
    K.downstream(server)
    _sync(server, client, syncer)
    assert K.mushroomStew(client) is stew and stew["Recipe"] is ways, "对象不换"
    assert K.MUSHROOM_VARIANT in ways and stew["Slots"] == slots, "客户端的这条配方还带着每格的选项（Slots）：食谱书一格一格轮换备选要读它"
    assert K.snapshot(server)["CookingPotRecipeList"] == K.snapshot(client)["CookingPotRecipeList"]


def testTheClientRebuildsWhatItCachesFromTheTables():
    """厨锅配方的索引（哪些是食材 / 容器、怎么配、煮多久）和砧板的工具表要在并表之后重算，不然站点读到的还是旧的。"""
    server, client, syncer = _pair()
    pot, board = client.load("Shared.Rules.CookingPot"), client.load("Shared.Rules.BoardStation")
    tea, sauceKey = ("ends_delight:chorus_flower", 0), tuple(sorted([K.SUCCULENT, K.CHORUS_FRUIT]))
    assert pot.lookupRecipe(sauceKey) is None and not pot.isIngredient(K.SUCCULENT) and not pot.isIngredient(tea)
    assert pot.cookSecondsOf("ends_delight:chorus_tea") == pot.DEFAULT_COOK_SECONDS
    assert "ends_delight:chorus_axe" not in board._tools()[0], "先算一遍，缓存起来"
    K.downstream(server)
    _sync(server, client, syncer)
    assert pot.lookupRecipe(sauceKey)[0] == K.SAUCE
    assert pot.isIngredient(K.SUCCULENT) and pot.isIngredient(tea) and pot.cookSecondsOf("ends_delight:chorus_tea") == 5.0
    assert pot.lookupRecipe(tuple(sorted(K.MUSHROOM_VARIANT)))[0] == ("minecraft:mushroom_stew", 0)
    assert "ends_delight:chorus_axe" in board._tools()[0] and K.KNIFE in board._tools()[0]


def testALaterKnifeCompletesTheSharedListWithoutResendingTheRecipes():
    server, client, syncer = _pair()
    knives = K.downstream(server)
    _sync(server, client, syncer)
    knives.append("ends_delight:late_knife")
    assert syncer.changed() and syncer.refresh() is True and syncer.rev == 2
    assert _ops(syncer)["CuttingBoardDict"] == 2 and _ops(syncer)["knifeList"] == 2, "tool 是引用：配方的条目没变，只是 knifeList 多了一把"
    later = syncer.messages(since=1)
    assert [(message["table"], message["rev"]) for message in later] == [("knifeList", 2)], "已经收过第 1 版的人只补变了的那张表"
    assert later[0]["ops"] == [K.KNIFE, "ends_delight:late_knife"], "补发的是这张表累计的差异（不是只有新的一把）"
    assert len(syncer.messages()) == 8 and syncer.messages(since=2) == [], "新进服的要全部；已经是最新的什么也不用补"
    K.deliver(syncer.messages(), client)
    cutting = client.load("Shared.Data.Cutting")
    assert "ends_delight:late_knife" in cutting.knifeList and cutting.CuttingBoardDict[K.CUT_KEY]["tool"] is cutting.knifeList
    assert K.snapshot(server) == K.snapshot(client)


def testAChangedBuiltInEntryReplacesTheClientsOne():
    server, client, syncer = _pair()
    cooking, cutting = server.load("Shared.Data.Cooking"), server.load("Shared.Data.Cutting")
    cooking.CanCookedFoodDict["minecraft:beef"] = "ends_delight:dragon_steak"
    cutting.CuttingBoardDict[("minecraft:beef", 0)] = {"itemList": [{"itemName": "arris:minced_beef", "count": 3}], "tool": cutting.knifeList}
    _sync(server, client, syncer)
    assert client.load("Shared.Data.Cooking").CanCookedFoodDict["minecraft:beef"] == "ends_delight:dragon_steak"
    assert client.load("Shared.Data.Cutting").CuttingBoardDict[("minecraft:beef", 0)]["itemList"][0]["count"] == 3
    assert K.snapshot(server) == K.snapshot(client)


def testRemovalsAreNotSynced():
    """联动契约只有追加：下游直接从表里删东西，客户端留着（多认一个不会坏事），差异里也没有这条。"""
    server, client, syncer = _pair()
    knives = server.load("Shared.Data.Cutting").knifeList
    gone = knives.pop(0)
    assert syncer.changed() and syncer.refresh() is False and syncer.messages() == [] and syncer.rev == 0
    assert gone in client.load("Shared.Data.Cutting").knifeList


def testTheRevOnlyMovesWhenTheDiffChanges():
    server, client, syncer = _pair()
    assert syncer.refresh() is False and syncer.rev == 0
    stoves = server.load("Shared.Data.Cooking").StoveList
    stoves.append("x:stove")
    assert syncer.refresh() is True and syncer.rev == 1
    assert syncer.refresh() is False and syncer.rev == 1, "没变不重算"
    stoves.append("x:stove")
    assert syncer.changed() and syncer.refresh() is False and syncer.rev == 1, "变了但差异一样（重复的名字）：不算新的一版"
    stoves.append("x:stove2")
    assert syncer.refresh() is True and syncer.rev == 2 and syncer.messages()[0]["ops"] == ["x:stove", "x:stove2"]


def testTheSyncerNeverTouchesTheTablesItWatches():
    server, client, syncer = _pair()
    tables = server.load("Shared.Rules.SyncTables").TABLES
    ids = [(name, id(container)) for name, _kind, container in tables]
    K.downstream(server)
    before = K.snapshot(server)
    syncer.refresh()
    syncer.messages()
    syncer.refresh()
    assert [(name, id(container)) for name, _kind, container in tables] == ids and K.snapshot(server) == before
    legacy, outside = server.load("Api.LegacyModAttr"), server.load("Shared.Rules.SyncTables").OUTSIDE_CONTRACT
    cooking = server.load("Shared.Data.Cooking")
    for name, _kind, container in tables:
        if name in outside:
            assert getattr(cooking, name) is container, "契约之外的表登记的也是 Shared/Data 里的那个对象：%s" % name
            continue
        assert legacy.ArrisFarmersDelightObtain(name) is container, "联动契约交出去的还是同一个对象：%s" % name


def testSharedObjectsAreNotReplacedWhenBothEndsLiveInOneProcess():
    """单机联机时两端的脚本可能在同一个解释器里共用一份表：并表发现本端已经有一样的东西就不动它（不能把下游手里的配方字典换成副本）。"""
    one = K.Package()
    syncer = one.load("Shared.Rules.TableDiff").Syncer()
    K.downstream(one)
    row = one.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList[-1]
    syncer.refresh()
    results = K.deliver(syncer.messages(), one)
    assert all(not result["changed"] and not result["problems"] for result in results), results
    assert one.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList[-1] is row


def testHeatConditionsAndTheirAuxSetsReachTheClient():
    """热源的状态条件表和它派生的 aux 集合不在契约里，也照常同步：服务端写的条件、算好的 aux 集合到了客户端，客户端的 heatsByAux 就认它；
    内置的炼药锅那一条两端本来一样，不发。"""
    server, client, syncer = _pair()
    cooking = server.load("Shared.Data.Cooking")
    cooking.HeatSourceStateDict["mymod:brazier"] = {"mymod:coals": {"min": 1}, "mymod:kind": ["coal", "charcoal"]}
    cooking.HeatSourceAuxDict["mymod:brazier"] = [1, 2, 3]
    heats = client.load("Shared.Rules.HeatSources")
    assert not heats.heatsByAux("mymod:brazier", 2), "没同步之前：客户端连这个方块写了条件都不知道（不在名单、标签里）"
    _sync(server, client, syncer)
    assert _ops(syncer) == {"HeatSourceStateDict": 1, "HeatSourceAuxDict": 1}, _ops(syncer)
    mine = client.load("Shared.Data.Cooking")
    assert mine.HeatSourceStateDict["mymod:brazier"] == {"mymod:coals": {"min": 1}, "mymod:kind": ["coal", "charcoal"]}
    assert mine.HeatSourceAuxDict["mymod:brazier"] == [1, 2, 3] and heats.heatsByAux("mymod:brazier", 2) and not heats.heatsByAux("mymod:brazier", 0)
    assert mine.HeatSourceAuxDict["minecraft:cauldron"] == [9, 10, 11, 12, 13, 14] and K.snapshot(server) == K.snapshot(client)


def testEveryWhitelistedTableIsEitherSyncedOrExplained():
    """联动契约白名单里的每个变量：要么同步（而且登记的就是契约交出去的那个对象），要么写明为什么客户端不用。新加变量时这里会红。
    契约之外也同步的表（热源的状态条件和它派生的 aux 集合）在 OUTSIDE_CONTRACT 里写明原因，不在白名单里。"""
    package = K.Package()
    legacy, tables = package.load("Api.LegacyModAttr"), package.load("Shared.Rules.SyncTables")
    names, outside = set(legacy._TARGETS), set(tables.OUTSIDE_CONTRACT)
    synced, explained = set(tables.BY_NAME) - outside, set(tables.NOT_SYNCED)
    assert synced | explained == names and not (synced & explained), (sorted(names - synced - explained), sorted((synced | explained) - names))
    assert outside <= set(tables.BY_NAME) and not outside & names, "契约之外的表要真的同步、又不在白名单里"
    assert outside == set(["HeatSourceStateDict", "HeatSourceAuxDict"]) and all(tables.OUTSIDE_CONTRACT[name] for name in outside)
    for name in synced:
        assert tables.BY_NAME[name][1] is legacy._TARGETS[name], name
        assert tables.NOT_SYNCED.get(name) is None
    assert all(tables.NOT_SYNCED[name] for name in explained), "每个不同步的都写了原因"


# ---------------------------------------------------------------- 传不了的值、拆条、不对的消息

def testValuesThatCannotBeSentAreSkippedAndLoggedNotRaised():
    server, client, syncer = _pair()
    legacy = server.load("Api.LegacyModAttr")
    knives = legacy.ArrisFarmersDelightObtain("knifeList")
    legacy.ArrisFarmersDelightInterface("CuttingBoardDict", {
        ("x:good", 0): {"itemList": [{"itemName": "x:out", "count": 1}], "tool": knives},
        ("x:bad", 0): {"itemList": [{"itemName": "x:out", "count": 1}], "tool": knives, "handler": object()},
        ("x:nested", 0): {"itemList": [{"itemName": "x:out", "count": 1}], "extra": {1: "int key"}}})
    knives.append(7)                                    # 不是名字
    legacy.ArrisFarmersDelightInterface("CanCookedFoodDict", {"x:raw": "x:cooked", "x:weird": set(["a"])})
    syncer.refresh()
    assert len(syncer.problems) == 4, syncer.problems
    for problem in syncer.problems:
        assert "x:bad" in problem or "x:nested" in problem or "x:weird" in problem or "7" in problem, problem
    K.deliver(syncer.messages(), client)
    cutting, cooking = client.load("Shared.Data.Cutting"), client.load("Shared.Data.Cooking")
    assert ("x:good", 0) in cutting.CuttingBoardDict and ("x:bad", 0) not in cutting.CuttingBoardDict and ("x:nested", 0) not in cutting.CuttingBoardDict
    assert cooking.CanCookedFoodDict["x:raw"] == "x:cooked" and "x:weird" not in cooking.CanCookedFoodDict and 7 not in cutting.knifeList


def testATableThatCannotBeCopiedStillSyncsTheGoodEntries():
    """下游往表里放了 deepcopy 不认的东西：变没变的快速检查退成"每次都重算"，坏条目照样只是被跳过，好的照发，没变时版本不动。"""
    class Uncopyable(object):
        def __deepcopy__(self, memo):
            raise TypeError("no copy")

    server, client, syncer = _pair()
    legacy = server.load("Api.LegacyModAttr")
    knives = legacy.ArrisFarmersDelightObtain("knifeList")
    legacy.ArrisFarmersDelightInterface("CuttingBoardDict", {
        ("x:good", 0): {"itemList": [{"itemName": "x:out", "count": 1}], "tool": knives},
        ("x:bad", 0): {"itemList": [{"itemName": "x:out", "count": 1}], "tool": knives, "handler": Uncopyable()}})
    assert syncer.refresh() is True and syncer.rev == 1 and len(syncer.problems) == 1 and "x:bad" in syncer.problems[0]
    assert syncer.changed() is True and syncer.refresh() is False and syncer.rev == 1, "每次都重算，差异没变就不是新的一版"
    K.deliver(syncer.messages(), client)
    cutting = client.load("Shared.Data.Cutting")
    assert ("x:good", 0) in cutting.CuttingBoardDict and ("x:bad", 0) not in cutting.CuttingBoardDict
    legacy.ArrisFarmersDelightObtain("StoveList").append("x:stove")
    assert syncer.refresh() is True and syncer.rev == 2 and [message["table"] for message in syncer.messages(since=1)] == ["StoveList"]


def testABadNewRecipeIsReplacedByAnEmptyRowSoTheOthersKeepTheirIndices():
    """食谱书页的键就是厨锅配方的下标，客户端放料时发的也是它：中间一行传不了，后面几行的下标不能错位。"""
    server, client, syncer = _pair()
    legacy = server.load("Api.LegacyModAttr")
    for index in range(3):
        row = K.recipe(("x:dish%d" % index, 0), [[("x:ingredient%d" % index, 0)]], text="菜%d" % index)
        if index == 1:
            row["PushItem"] = [object()]
        legacy.ArrisFarmersDelightInterface("CookingPotRecipeList", row)
    syncer.refresh()
    assert len(syncer.problems) == 1 and "用空行占着下标" in syncer.problems[0]
    K.deliver(syncer.messages(), client)
    serverRows = server.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
    clientRows = client.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
    assert len(clientRows) == len(serverRows)
    for index in (len(serverRows) - 3, len(serverRows) - 1):
        assert clientRows[index]["CookResult"] == serverRows[index]["CookResult"], index
    hole = clientRows[len(serverRows) - 2]
    assert hole["Recipe"] == [] and hole["CookResult"] == ("", 0)
    books = client.load("Shared.Rules.StationBooks")
    keys = [page["key"] for page in books.potPages()]
    assert len(serverRows) - 1 in keys and len(serverRows) - 3 in keys and len(serverRows) - 2 not in keys, "空行不出书页，别的页的键还是服务端的下标"
    assert books.potRecipe(len(serverRows) - 1)["CookResult"] == ("x:dish2", 0)


def testABigDiffIsSplitIntoSeveralMessagesAndStillConverges():
    server, client, syncer = _pair(limit=400)
    legacy = server.load("Api.LegacyModAttr")
    legacy.ArrisFarmersDelightInterface("CuttingBoardDict", dict(
        ((("x:cut%d" % index, 0), {"itemList": [{"itemName": "x:out%d" % index, "count": 2}], "tool": legacy.ArrisFarmersDelightObtain("knifeList")})
         for index in range(40))))
    for index in range(25):
        legacy.ArrisFarmersDelightInterface("CookingPotRecipeList", K.recipe(("x:dish%d" % index, 0), [[("x:a%d" % index, 0), ("x:b%d" % index, 0)]]))
        legacy.ArrisFarmersDelightInterface("StoveList", "x:stove%d" % index)
    syncer.refresh()
    messages = syncer.messages()
    tables = [message["table"] for message in messages]
    assert tables.count("CuttingBoardDict") > 1 and tables.count("CookingPotRecipeList") > 1 and tables.count("StoveList") >= 1, tables
    for message in messages:
        assert len(repr(message["ops"])) < 400 * 2, "单条消息不大"
    K.deliver(messages, client)
    assert K.snapshot(server) == K.snapshot(client)
    K.deliver(messages, client)
    assert K.snapshot(server) == K.snapshot(client)


def testTheClientRefusesARowsMessageFromADifferentVersionOfTheTable():
    server, client, syncer = _pair()
    K.downstream(server)
    syncer.refresh()
    message = [m for m in syncer.messages() if m["table"] == "CookingPotRecipeList"][0]
    before = K.snapshot(client)
    stale = dict(message, base=len(client.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList) + 5)
    result = client.load("Shared.Rules.TableMerge").apply(K.transport(stale))
    assert not result["changed"] and len(result["problems"]) == 1 and "不是同一版" in result["problems"][0]
    gap = dict(message, ops=[dict(message["ops"][0], at=message["base"] + 3)])
    result = client.load("Shared.Rules.TableMerge").apply(K.transport(gap))
    assert not result["changed"] and "前面缺了几行" in result["problems"][0]
    assert K.snapshot(client) == before


def testLongIntegersInTheMessageFromAPyTwoEngineAreAccepted():
    """引擎在 py2 里给的整数（base、at、rev、值里的整数）可能是 long。"""
    big = fdtest.load("Shared.Rules.TableWire").INT_TYPES[-1]
    server, client, syncer = _pair()
    K.downstream(server)
    syncer.refresh()

    def longs(value):
        if isinstance(value, dict):
            return dict((key, longs(item)) for key, item in value.items())
        if isinstance(value, list):
            return [longs(item) for item in value]
        return big(value) if isinstance(value, int) and not isinstance(value, bool) else value

    results = K.deliver([longs(message) for message in syncer.messages()], client)
    assert all(result["changed"] and not result["problems"] for result in results), results
    assert K.snapshot(server) == K.snapshot(client)
    row = client.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList[-1]
    assert row["CookCount"] == 2 and type(row["CookCount"]) is int and type(row["CookResult"][1]) is int, "long 换回 int"


def testBadMessagesAreIgnoredWithoutRaising():
    server, client, syncer = _pair()
    merge = client.load("Shared.Rules.TableMerge")
    before = K.snapshot(client)
    good = {"proto": 1, "table": "StoveList", "kind": "items", "ops": ["x:stove"]}
    for bad in (None, [], "text", 7, {}, dict(good, proto=2), dict(good, proto=None), dict(good, table="noSuchTable"), dict(good, table=["list"]),
                dict(good, kind="map"), dict(good, ops="x:stove"), dict(good, ops=None), {"proto": 1, "table": "StoveList"},
                dict(good, ops=[{"$weird": 1}, 5, None, ["a"]]),
                {"proto": 1, "table": "CuttingBoardDict", "kind": "map", "ops": [None, {"k": 1}, {"k": {"$ref": "nope"}, "v": 1}, {"k": ["a"], "v": 1}]},
                {"proto": 1, "table": "CookingPotRecipeList", "kind": "rows", "base": "x", "ops": []},
                {"proto": 1, "table": "CookingPotRecipeList", "kind": "rows", "base": 0, "ops": [{"at": "1", "v": {}}, {"at": -1, "v": {}}, {"at": 0, "v": 3}]}):
        result = merge.apply(bad)
        assert not result["changed"] and result["problems"], bad
    assert K.snapshot(client) == before
    ok = merge.apply(good)
    assert ok["changed"] and not ok["problems"] and "x:stove" in client.load("Shared.Data.Cooking").StoveList


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
