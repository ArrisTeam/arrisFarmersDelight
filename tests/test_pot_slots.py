# -*- coding: utf-8 -*-
# runner: both
"""厨锅配方的格子（Shared/Rules/PotSlots.py）：选项的写法、一格收什么、锅里的料和格子一件对一格、一种料占几格、按格子展开写法。

标签用一张假表答（hasTag / membersOf 由调用的人给，离线测试不碰 ItemTags）。
"""
from __future__ import print_function

import fdtest

Slots = fdtest.load("Shared.Rules.PotSlots")

TAGS = {"common:raw_beef": ("minecraft:beef", "arris:minced_beef", "other:steak"),
        "common:vegetable": ("minecraft:carrot", "minecraft:potato", "arris:tomato"),
        "common:empty": ()}
BEEF, MINCED, STEAK = ("minecraft:beef", 0), ("arris:minced_beef", 0), ("other:steak", 0)
CARROT, POTATO, TOMATO = ("minecraft:carrot", 0), ("minecraft:potato", 0), ("arris:tomato", 0)


def hasTag(name, tag):
    return name in TAGS.get(tag, ())


def membersOf(tag):
    return TAGS.get(tag, ())


def testOptionsAreItemsItemsWithAuxOrTags():
    assert Slots.parseOption("minecraft:carrot") == ("item", CARROT)
    assert Slots.parseOption(("minecraft:dye", 4)) == ("item", ("minecraft:dye", 4))
    assert Slots.parseOption(["minecraft:dye", 4]) == ("item", ("minecraft:dye", 4)), "过了线的元组是列表"
    assert Slots.parseOption("#common:raw_beef") == ("tag", "common:raw_beef")
    for bad in ("carrot", "#raw_beef", "", "#", None, 3, ("minecraft:dye",), ("minecraft:dye", -1), ("minecraft:dye", True),
                ("#common:raw_beef", 0), "minecraft:carrot ", {"item": "minecraft:carrot"}):
        assert Slots.parseOption(bad) is None, bad


def testSlotsProblemNamesWhatIsWrong():
    assert Slots.slotsProblem([["minecraft:carrot"], ["#common:raw_beef", ("minecraft:dye", 4)]]) is None
    assert "1 到 6" in Slots.slotsProblem([])
    assert "1 到 6" in Slots.slotsProblem("minecraft:carrot")
    assert "最多 6 格" in Slots.slotsProblem([["minecraft:carrot"]] * 7)
    assert "第 2 格" in Slots.slotsProblem([["minecraft:carrot"], []])
    assert "第 1 格的选项" in Slots.slotsProblem([["carrot"]])
    assert Slots.tagsIn([["#common:raw_beef", "minecraft:carrot"], ["#common:vegetable"]]) == {"common:raw_beef", "common:vegetable"}
    assert Slots.itemsIn([["#common:raw_beef", "minecraft:carrot"], [("minecraft:dye", 4)]]) == {CARROT, ("minecraft:dye", 4)}


def testAccepts():
    slot = ["#common:raw_beef", "minecraft:carrot", ("minecraft:dye", 4)]
    assert Slots.accepts(slot, STEAK, hasTag) and Slots.accepts(slot, CARROT, hasTag)
    assert Slots.accepts(slot, ("minecraft:dye", 4), hasTag) and not Slots.accepts(slot, ("minecraft:dye", 1), hasTag)
    assert not Slots.accepts(slot, ("minecraft:carrot", 3), hasTag), "写成物品名的选项只收 aux 0"
    assert Slots.accepts(["#common:raw_beef"], ("minecraft:beef", 7), hasTag), "标签不看 aux"
    assert not Slots.accepts(slot, POTATO, hasTag)


def testItemsFitOneASlotInAnyOrderTryingEveryWay():
    slots = [["#common:vegetable"], ["minecraft:carrot"]]
    assert Slots.fits(slots, [CARROT, POTATO], hasTag) and Slots.fits(slots, [POTATO, CARROT], hasTag)
    assert Slots.fits(slots, [CARROT, CARROT], hasTag), "胡萝卜也算蔬菜：两格都给胡萝卜"
    assert not Slots.fits(slots, [POTATO, POTATO], hasTag), "第二格只收胡萝卜"
    assert not Slots.fits(slots, [CARROT], hasTag) and not Slots.fits(slots, [CARROT, POTATO, TOMATO], hasTag), "件数要正好等于格数"
    # 先到先得会配错的：标签格先拿走了胡萝卜，胡萝卜格就空了（HoD 注释里的泡菜）
    greedy = [["#common:vegetable"], ["minecraft:carrot"], ["#common:raw_beef"]]
    assert Slots.fits(greedy, [CARROT, TOMATO, MINCED], hasTag)


def testPartsOfListsEveryWayTheKindsFillTheSlots():
    slots = [["#common:raw_beef"], ["#common:raw_beef"], ["#common:vegetable"]]
    assert Slots.partsOf(slots, [BEEF, CARROT], hasTag) == [{BEEF: 2, CARROT: 1}]
    assert Slots.partsOf(slots, [BEEF, MINCED, CARROT], hasTag) == [{BEEF: 1, MINCED: 1, CARROT: 1}]
    assert Slots.partsOf(slots, [BEEF], hasTag) == [], "蔬菜格没人填"
    assert Slots.partsOf(slots, [BEEF, POTATO, CARROT, MINCED], hasTag) == [], "种类比格子多"
    assert Slots.partsOf(slots, [BEEF, ("x:y", 0)], hasTag) == [], "有一种料没有格子收"
    twice = [["#common:vegetable"], ["#common:vegetable"], ["#common:vegetable"]]
    assert Slots.partsOf(twice, [CARROT, POTATO], hasTag) == [{CARROT: 1, POTATO: 2}, {CARROT: 2, POTATO: 1}], "按拆法的字典序"


def testOptionsAndExpansionFollowTheTableOrder():
    slot = ["minecraft:carrot", "#common:vegetable", ("minecraft:dye", 4)]
    assert Slots.optionsOf(slot, membersOf) == [CARROT, POTATO, TOMATO, ("minecraft:dye", 4)], "去重、照写的先后"
    assert Slots.optionsOf(["#common:empty"], membersOf) == []
    ways = Slots.expand([["#common:raw_beef"], ["minecraft:carrot", "minecraft:potato"]], membersOf, 64)
    assert ways == [[BEEF, CARROT], [BEEF, POTATO], [MINCED, CARROT], [MINCED, POTATO], [STEAK, CARROT], [STEAK, POTATO]], "最后一格变得最快"
    assert Slots.expand([["#common:vegetable"], ["#common:vegetable"]], membersOf, 64) == [
        [CARROT, CARROT], [CARROT, POTATO], [CARROT, TOMATO], [POTATO, POTATO], [POTATO, TOMATO], [TOMATO, TOMATO]], "排好序一样的只留一种"
    assert len(Slots.expand([["#common:vegetable"]] * 6, membersOf, 5)) == 5, "封顶"
    assert Slots.expand([["#common:raw_beef"], ["#common:empty"]], membersOf, 64) == [], "某格一个成员都没有：空"


def testConcretizeUsesOnlyWhatIsAtHand():
    slots = [["#common:raw_beef"], ["#common:vegetable"], ["minecraft:carrot"]]
    assert Slots.concretize(slots, [STEAK, CARROT, None, POTATO], hasTag, 64) == [[STEAK, CARROT, CARROT], [STEAK, POTATO, CARROT]]
    assert Slots.concretize(slots, [STEAK, POTATO], hasTag, 64) == [], "胡萝卜格没有胡萝卜"
    assert Slots.concretize(slots, [BEEF, MINCED, CARROT, POTATO, TOMATO], hasTag, 3) == [
        [BEEF, CARROT, CARROT], [BEEF, POTATO, CARROT], [BEEF, TOMATO, CARROT]]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
