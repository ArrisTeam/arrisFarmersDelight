# -*- coding: utf-8 -*-
# runner: both
"""联动契约里给站点用的三张表（2026-11-19 加进白名单，Api/LegacyModAttr.py）：DishList 砧板上摆的菜、OneSidedList 煎锅上只煎一面的、NotOnGrillList 炉灶的烤架不收的。
HoD 里后两样是物品标签（KitchenTags.ONE_SIDED / NOT_ON_GRILL，数据包能加），摆盘的菜是配方（数据包能加）；我们这边下游模组原来够不着——规则里写死的 frozenset、
生成的表不在白名单里。现在：obtain 拿到的是规则真在读的那个对象（活引用），interface 追加之后规则立刻认；摆盘菜写坏的行整体拒绝（不然重建索引半路出错）；
服务端追加的经表同步发给客户端（Shared/Rules/SyncTables），客户端的规则跟着认。原有的 21 个名字一个不动（tests/test_legacy_modattr_contract.py 锁着）。
"""
from __future__ import print_function

import tablekit as K

import fdtest

Legacy = fdtest.load("Api.LegacyModAttr")
Cooking = fdtest.load("Shared.Data.Cooking")
Dishes = fdtest.load("Shared.Data.Dishes")
Pan = fdtest.load("Shared.Rules.PanStation")
Grill = fdtest.load("Shared.Rules.GrillStation")
DishStation = fdtest.load("Shared.Rules.DishStation")
Tables = fdtest.load("Shared.Rules.SyncTables")
PRISTINE = K.Pristine(K.DEFAULT)
WRAP = ("test:veggie_wrap", 0)
BREAD, CABBAGE, PATTY = ("minecraft:bread", 0), ("arris:cabbage_leaf", 0), ("test:patty", 0)


def _row(result=WRAP, ingredients=(BREAD, CABBAGE, PATTY), **extra):
    return dict({"result": result, "count": 2, "ingredients": list(ingredients), "extras": [], "keeps": [], "source": "test"}, **extra)


def _clean(test):
    def run():
        PRISTINE.restore()
        try:
            test()
        finally:
            PRISTINE.restore()
    run.__name__ = test.__name__
    return run


# ---------------------------------------------------------------- 契约

def testObtainHandsOutTheVeryObjectsTheRulesRead():
    assert Legacy.ArrisFarmersDelightObtain("DishList") is Dishes.DishList
    assert Legacy.ArrisFarmersDelightObtain("OneSidedList") is Cooking.OneSidedList is Pan.ONE_SIDED
    assert Legacy.ArrisFarmersDelightObtain("NotOnGrillList") is Cooking.NotOnGrillList is Grill.NOT_ON_GRILL
    assert Cooking.OneSidedList == ["minecraft:egg"] and Cooking.NotOnGrillList == ["minecraft:egg"], "HoD 的缺省：两样都只有蛋"
    assert len(Legacy._TARGETS) == 25, "原有 21 个名字加这三个，再加 2026-11-26 的 CuttingTagDict（按标签切的砧板配方）"


@_clean
def testANameAddedToOneSidedIsFriedOnOneSideOnly():
    assert not Pan.isOneSided("test:crepe")
    assert Legacy.ArrisFarmersDelightInterface("OneSidedList", "test:crepe") is Cooking.OneSidedList
    assert Pan.isOneSided("test:crepe") and Pan.isOneSided("minecraft:egg")


@_clean
def testANameAddedToNotOnGrillIsRefusedByTheGrillOnly():
    assert Grill.canGrill("minecraft:beef") and Pan.canFry("minecraft:beef")
    assert Legacy.ArrisFarmersDelightInterface("NotOnGrillList", ["minecraft:beef"]) is Cooking.NotOnGrillList
    assert not Grill.canGrill("minecraft:beef") and Pan.canFry("minecraft:beef"), "烤架不收了，煎锅照收"


@_clean
def testADishRowAddedIsBuiltOnTheBoardRightAway():
    assert not DishStation.isDishResult(WRAP[0])
    assert Legacy.ArrisFarmersDelightInterface("DishList", _row()) is Dishes.DishList and Dishes.DishList[-1]["result"] == WRAP
    assert DishStation.isDishResult(WRAP[0]), "索引跟着重建"
    done = DishStation.completed([BREAD, CABBAGE, PATTY])
    assert done is not None and tuple(done["result"]) == WRAP and done["count"] == 2, "面包打底、往上叠：做成的就是它"
    assert DishStation.fitsNext([BREAD], CABBAGE) and DishStation.fitsNext([BREAD, CABBAGE], PATTY)


@_clean
def testABrokenDishRowIsRefusedAndNothingChanges():
    before, known = list(Dishes.DishList), len(DishStation.dishes())
    broken = ["not a row", {"ingredients": [BREAD]}, _row(result="test:wrap"), _row(ingredients=()), _row(ingredients=[BREAD] * 10),
              _row(ingredients=[BREAD, "arris:cabbage_leaf"]), dict(_row(), ingredients=None)]
    for row in broken:
        assert Legacy.ArrisFarmersDelightInterface("DishList", row) is False, row
    assert Legacy.ArrisFarmersDelightInterface("DishList", [_row(), broken[1]]) is False, "一批里有一行坏的：整批不要"
    assert Dishes.DishList == before and len(DishStation.dishes()) == known, "表和索引都没动"


# ---------------------------------------------------------------- 同步给客户端

def testTheThreeTablesAreSyncedAsTheContractHandsThemOut():
    assert Tables.BY_NAME["DishList"] == (Tables.ROWS, Dishes.DishList)
    assert Tables.BY_NAME["OneSidedList"] == (Tables.ITEMS, Cooking.OneSidedList)
    assert Tables.BY_NAME["NotOnGrillList"] == (Tables.ITEMS, Cooking.NotOnGrillList)
    assert not Tables.HOLES["DishList"]["ingredients"], "占下标的空行没有配料：两端的索引都跳过它"


@_clean
def testWhatTheServerAddsReachesTheClientsRules():
    server = K.Package()
    syncer = server.load("Shared.Rules.TableDiff").Syncer()
    legacy = server.load("Api.LegacyModAttr")
    assert legacy.ArrisFarmersDelightInterface("DishList", _row())
    assert legacy.ArrisFarmersDelightInterface("OneSidedList", "test:crepe") and legacy.ArrisFarmersDelightInterface("NotOnGrillList", "minecraft:beef")
    assert syncer.refresh() and not syncer.problems
    assert not DishStation.isDishResult(WRAP[0]) and not Pan.isOneSided("test:crepe") and Grill.canGrill("minecraft:beef"), "前提：客户端还不认"
    results = K.deliver(syncer.messages(), K.DEFAULT)
    assert all(not result["problems"] for result in results) and sorted(result["table"] for result in results if result["changed"]) == \
        ["DishList", "NotOnGrillList", "OneSidedList"]
    assert DishStation.isDishResult(WRAP[0]) and tuple(DishStation.completed([BREAD, CABBAGE, PATTY])["result"]) == WRAP, "客户端：摆得出这道菜"
    assert Dishes.DishList[-1]["ingredients"] == [BREAD, CABBAGE, PATTY], "配料换回 (物品名, aux) 元组"
    assert Pan.isOneSided("test:crepe") and not Grill.canGrill("minecraft:beef")
    again = K.deliver(syncer.messages(), K.DEFAULT)
    assert not any(result["changed"] for result in again), "重复收：不重复加"


@_clean
def testADishRowTheWireCannotCarryHoldsItsPlaceWithAnEmptyRow():
    server = K.Package()
    syncer = server.load("Shared.Rules.TableDiff").Syncer()
    dishes = server.load("Shared.Data.Dishes").DishList
    dishes.append(_row(result=("test:odd", 0), source=object()))       # 直接改表（没经契约的校验）、带着传不了的东西
    dishes.append(_row())
    assert syncer.refresh() and syncer.problems
    K.deliver(syncer.messages(), K.DEFAULT)
    assert Dishes.DishList[-2] == Tables.HOLES["DishList"] and Dishes.DishList[-1]["result"] == WRAP, "传不了的那一行用空行占着下标"
    assert DishStation.isDishResult(WRAP[0]) and not DishStation.isDishResult(""), "空行不是一道菜"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
