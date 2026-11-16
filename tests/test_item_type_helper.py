# -*- coding: utf-8 -*-
# runner: both
"""Server/Helpers/Items.GetItemType：引擎不认识的物品（比如拆掉的附属包留在背包里的）不能让它抛异常。

砧板空手借刀时对整个背包逐件问物品类型（BoardStation.Env.toolSlot -> cutsWith -> typeOf），
GetItemBasicInfo 对没登记的物品若返回 None，原来的 ["itemType"] 就是 TypeError：每次落刀都复现，关站踢掉同站所有人。
"""
from __future__ import print_function

import potfake

fake = potfake.install()
Items = potfake.load("Server.Helpers.Items")
Food = potfake.load("Shared.Data.Food")

_INFO = {"minecraft:iron_hoe": {"itemType": "hoe", "maxStackSize": 1}, "minecraft:bread": {"itemType": "food"},
         "odd:no_type": {"maxStackSize": 64}}
_asked = []


def _basicInfo(self, name, aux=0):
    _asked.append(name)
    return _INFO.get(name)          # 没登记的物品是 None


potfake.Comp.GetItemBasicInfo = _basicInfo


def _item(name):
    return {"newItemName": name, "newAuxValue": 0, "count": 1}


def testAnItemTheEngineDoesNotKnowHasNoTypeInsteadOfRaising():
    assert Items.GetItemType(_item("gone:addon_item")) is None


def testAnItemWithoutATypeKeyHasNoType():
    assert Items.GetItemType(_item("odd:no_type")) is None


def testKnownItemsKeepTheirType():
    assert Items.GetItemType(_item("minecraft:iron_hoe")) == "hoe"
    assert Items.GetItemType(_item("minecraft:bread")) == "food"


def testAPackagedFoodBlockCountsAsFoodWithoutAskingTheEngine():
    del _asked[:]
    name = next(iter(Food.platePackagedFoodDict))
    assert Items.GetItemType(_item(name)) == "food" and _asked == []


def testAnEmptyItemHasNoType():
    assert Items.GetItemType(None) is None and Items.GetItemType({}) is None


def testTheBoardToolSearchSurvivesAnUnknownItemAheadOfTheKnife():
    """review.md B1 的触发：背包里一件不认识的物品排在第一把能用的刀前面，找工具照样往下找。"""
    Rules = potfake.load("Shared.Rules.BoardStation")
    env = Rules.Env(lambda name: name == "arris:iron_knife", Items.GetItemType)
    items = [_item("gone:addon_item"), _item("arris:iron_knife")] + [None] * 34
    cutsCabbage = _item("arris:cabbage")
    assert env.toolSlot(cutsCabbage, items, -1, None) == ("inv", 1)


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
