# -*- coding: utf-8 -*-
# runner: both
"""板上的东西带着的数据（Shared/Rules/HandsOn/ItemData.py）：存不存得住、写进方块实体数据再读回来、两件算不算同一种。

JE 里板上、层里的东西是整件的 ItemStack，附魔 / 名字 / NBT 原样跟着、取回原样还；基岩这边照煎锅的办法（SkilletRules.storeItem）存进方块实体数据：
元组换列表、py2 的 unicode 换 str，读回来附魔换回元组；存不进去的数据板不收。
"""
from __future__ import print_function

import fdtest

ItemData = fdtest.load("Shared.Rules.HandsOn.ItemData")


def _item(name="minecraft:leather_chestplate", count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def testItemsWithoutDataHaveNoDataAndAreAlwaysStorable():
    assert ItemData.dataOf(_item()) == {} and ItemData.dataOf(None) == {} and ItemData.storable(_item()) and ItemData.storable(None)
    plain = _item(durability=0, customTips="", extraId="", userData={}, enchantData=[], modEnchantData=[], showInHand=True)
    assert ItemData.dataOf(plain) == {}, "没设置的（空串、空列表、耐久 0）不算数据；showInHand 只管显示，不算"


def testTheDataOfAnItemIsPlainListsAndStrings():
    item = _item(durability=33, enchantData=[(9, 1), (17, 3)], customTips=u"好刀", extraId="x1", userData={"display": {"Name": u"小红"}, "n": [1, 2]})
    data = ItemData.dataOf(item)
    assert data["durability"] == 33 and data["enchantData"] == [[9, 1], [17, 3]], "元组换成列表：方块实体数据不收元组"
    assert data["extraId"] == "x1" and data["userData"]["n"] == [1, 2]
    assert type(data["customTips"]) is str and type(data["userData"]["display"]["Name"]) is str, "py2 的 unicode 换成 str"
    assert ItemData.storable(item)


def testWhatTheBlockEntityDataCannotHoldIsNotStorable():
    bad = [{"userData": {"mixed": [1, "a"]}},                    # 列表里类型混着
           {"userData": {1: "int key"}},                          # 键不是 str
           {"userData": {"x": float("nan")}}, {"userData": {"x": float("inf")}},   # 非有限小数
           {"userData": {"x": object()}},                         # 引擎对象之类
           {"userData": {"x": 2 ** 70}},                          # 整数超出 64 位
           {"enchantData": [(9, 1), (17, "three")]},              # 附魔里类型混着
           {"userData": {"a": [[[[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]]]}},   # 嵌套太深
           {"userData": dict(("k%d" % index, index) for index in range(ItemData.MAX_NODES + 5))}]   # 太大
    for extra in bad:
        assert not ItemData.storable(_item(**extra)), extra
    good = [{"userData": {"ok": [1, 2, 3], "f": 1.5, "b": True, "nested": {"a": ["x", "y"]}}}, {"enchantData": [(9, 1)]}, {"customTips": "tips"},
            {"userData": {"emptyList": [], "none": None}}]
    for extra in good:
        assert ItemData.storable(_item(**extra)), extra


def testStoredAndRestoredRoundTripTheWholeItem():
    item = _item(count=3, durability=40, enchantData=[(9, 1), (17, 3)], modEnchantData=[("mod:x", 2)], customTips="t", extraId="id", userData={"d": {"Name": "n"}})
    stored = ItemData.stored(item)
    assert stored["count"] == 3 and stored["enchantData"] == [[9, 1], [17, 3]] and stored["modEnchantData"] == [["mod:x", 2]]
    back = ItemData.restored(stored)
    assert back["enchantData"] == [(9, 1), (17, 3)] and back["modEnchantData"] == [("mod:x", 2)], "附魔换回元组：引擎要这个"
    assert back["durability"] == 40 and back["customTips"] == "t" and back["extraId"] == "id" and back["userData"] == {"d": {"Name": "n"}}
    assert back["newItemName"] == "minecraft:leather_chestplate" and back["count"] == 3 and back["newAuxValue"] == 0
    assert ItemData.same(item, back) and ItemData.stored(back) == stored, "再存一遍还是同一份"
    assert ItemData.stored(item, 1)["count"] == 1 and ItemData.copyOf(item, 2)["count"] == 2 and item["count"] == 3, "不改入参"


def testCopyOfIsDeepAndKeepsTuples():
    item = _item(enchantData=[(9, 1)], userData={"list": [1, 2]})
    copy = ItemData.copyOf(item)
    assert copy["enchantData"] == [(9, 1)] and copy["userData"] == {"list": [1, 2]}
    copy["userData"]["list"].append(3)
    copy["enchantData"].append((1, 1))
    assert item["userData"]["list"] == [1, 2] and item["enchantData"] == [(9, 1)], "深拷贝：改副本不碰原件"
    assert "durability" not in ItemData.copyOf(_item(durability=0)), "耐久 0（不会坏的）不带"


def testOnlyTheSameNameAuxAndDataStacksUp():
    plain, named = _item("arris:cabbage"), _item("arris:cabbage", customTips="Prize")
    assert ItemData.same(plain, _item("arris:cabbage", 5)) and not ItemData.same(plain, named)
    assert ItemData.same(_item(enchantData=[(9, 1), (17, 3)]), _item(enchantData=[[17, 3], [9, 1]])), "附魔按内容比：不看顺序、不分元组和列表"
    assert not ItemData.same(_item(enchantData=[(9, 1)]), _item(enchantData=[(9, 2)]))
    assert ItemData.same(_item(durability=0), _item()), "耐久 0 和没有耐久是一回事"
    assert not ItemData.same(_item(durability=10), _item(durability=11))
    assert ItemData.same(_item(userData={"a": [1]}), _item(userData={"a": [1]})) and not ItemData.same(_item(userData={"a": [1]}), _item(userData={"a": [2]}))


def testTheEventCopyCarriesNoDataButTheDurability():
    light = ItemData.light(_item(count=4, durability=12, enchantData=[(9, 1)], userData={"x": 1}), 1)
    assert light == {"newItemName": "minecraft:leather_chestplate", "newAuxValue": 0, "count": 1, "durability": 12}, "动画用的：事件载荷里不放元组"
    assert ItemData.light(_item(), None) == {"newItemName": "minecraft:leather_chestplate", "newAuxValue": 0, "count": 1}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
