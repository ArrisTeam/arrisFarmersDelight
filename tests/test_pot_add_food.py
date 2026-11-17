# -*- coding: utf-8 -*-
# runner: both
"""经典界面的配方书"放入食材"（Server/CookingPot.CookingPotAddFood）：把背包里指定下标的物品各取 1 个放进厨锅前几格。
格子是整格读出来、加一个、整格写回去的：读的时候要连 userData 一起读（GetContainerItem 的 getUserData 缺省是 False），不然锅里原来那叠
改过的名字 / 自定义数据一写回去就没了；数据不一样的两叠也不能并在一起（JE 的 isSameItemSameTags）。"""
from __future__ import print_function

import potkit as K
import fdtest
import panfake  # noqa: F401 - 给假引擎补上整包读写背包（GetPlayerAllItems / SetPlayerAllItems），放入食材用它

fake = K.fake
NAMED = {"display": {"Name": "x"}}
TOMATO = K.TOMATO


def _add(indexList, pos=None):
    K.CookingPot.CookingPotAddFood("a", {"blockPos": list(K.POT if pos is None else pos), "indexList": list(indexList)})


def _slot(index):
    return fake.containers[(0, K.POT)][index]


def testOneOfEachNamedInventorySlotGoesIntoTheFirstSlots():
    K.setup()
    fake.give("a", 3, TOMATO, 5)
    fake.give("a", 4, "minecraft:carrot", 2)
    _add([3, 4])
    assert (_slot(0)["newItemName"], _slot(0)["count"]) == (TOMATO, 1) and (_slot(1)["newItemName"], _slot(1)["count"]) == ("minecraft:carrot", 1)
    assert fake.count("a", TOMATO) == 4 and fake.count("a", "minecraft:carrot") == 1


def testTheStackAlreadyInThePotKeepsItsData():
    K.setup()
    fake.containers[(0, K.POT)][0] = {"newItemName": TOMATO, "newAuxValue": 0, "count": 2, "userData": dict(NAMED)}
    fake.give("a", 3, TOMATO, 5, userData=dict(NAMED))
    _add([3])
    assert _slot(0)["count"] == 3 and _slot(0).get("userData") == NAMED, "同样数据的并进去，名字还在：%r" % (_slot(0),)


def testStacksWithDifferentDataAreNotMerged():
    K.setup()
    fake.containers[(0, K.POT)][0] = {"newItemName": TOMATO, "newAuxValue": 0, "count": 2, "userData": dict(NAMED)}
    fake.give("a", 3, TOMATO, 5)
    _add([3])
    assert _slot(0)["count"] == 2 and _slot(0).get("userData") == NAMED and fake.count("a", TOMATO) == 5, "改过名的和普通的不叠在一起，什么都没动"


def testCoordinatesThatAreNotNumbersAreIgnored():
    K.setup()
    fake.give("a", 3, TOMATO, 5)
    for bad in ([None, 1, 2], ["x", 1, 2], [float("nan"), 1, 2], [float("inf"), 1, 2], [True, 1, 2]):
        _add([3], pos=bad)
    assert fake.count("a", TOMATO) == 5


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
