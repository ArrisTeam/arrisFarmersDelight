# -*- coding: utf-8 -*-
# runner: both
"""Items 物品字典取值测试，并和 PotMatch / Assembly 串起来用一遍。"""
from __future__ import print_function


import fdtest

Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
Items = fdtest.load("Shared.Rules.HandsOn.Items")
PotMatch = fdtest.load("Shared.Rules.HandsOn.PotMatch")


def testEmptySlots():
    assert Items.isEmpty(None) and Items.isEmpty({}) and Items.isEmpty(Items.make("minecraft:beef", 0, 0))
    assert not Items.isEmpty(Items.make("minecraft:beef"))
    assert Items.countOf(None) == 0 and Items.countOf({}) == 0 and Items.countOf(Items.make("a", 0, 5)) == 5
    assert Items.keyOf(None) is None and Items.keyOf({}) is None


def testIdentityIsNameAndAux():
    assert Items.keyOf(Items.make("minecraft:beef", 0, 3)) == ("minecraft:beef", 0)
    assert Items.keyOf(Items.make("minecraft:dye", 4)) == ("minecraft:dye", 4)
    assert Items.keyOf({"newItemName": "minecraft:beef", "count": 1}) == ("minecraft:beef", 0), "aux 缺省 0"
    assert Items.keyOf(Items.make("a")) != Items.keyOf(Items.make("a", 1))


def testSlotsToCountsAndKeys():
    slots = [Items.make("minecraft:beef", 0, 4), None, Items.make("minecraft:carrot", 0, 4), {}, Items.make("minecraft:potato", 0, 1)]
    assert Items.countsOf(slots) == [4, 0, 4, 0, 1]
    assert Items.keysOf(slots) == [("minecraft:beef", 0), None, ("minecraft:carrot", 0), None, ("minecraft:potato", 0)]


def testWiredIntoThePotBatch():
    # 牛肉 4、胡萝卜 4、马铃薯 1 的锅：配方的三个配料各接受一种 (名字, aux)
    slots = [Items.make("minecraft:beef", 0, 4), Items.make("minecraft:carrot", 0, 4), None, Items.make("minecraft:potato", 0, 1)]
    keys = Items.keysOf(slots)
    ingredients = [set([("minecraft:beef", 0)]), set([("minecraft:carrot", 0)]), set([("minecraft:potato", 0)])]
    accepts = lambda ingredient, slot: keys[slot] in ingredients[ingredient]
    assert PotMatch.servingsLeft(Items.countsOf(slots), len(ingredients), accepts) == 1, "one potato makes one stew"


def testWiredIntoTheBoardLayers():
    burger = {"ingredients": [set([("minecraft:bread", 0)]), set([("arris:beef_patty", 0)])], "base": 0}
    layers = Items.keysOf([Items.make("minecraft:bread", 0, 20), Items.make("arris:beef_patty", 0, 6)])
    accepts = lambda ingredient, layer: layer in ingredient
    assert Assembly.complete([burger], layers, accepts) is burger
    assert Assembly.rounds(Items.countsOf([Items.make("a", 0, 20), Items.make("b", 0, 6)])) == 6


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
