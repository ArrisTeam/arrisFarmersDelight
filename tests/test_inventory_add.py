# -*- coding: utf-8 -*-
# runner: both
"""往背包窗口放东西的落格次序（Shared/Rules/InventoryAdd.py）：原版 Inventory.add。

1.20.1 的 Inventory.add（getSlotWithRemainingSpace / getFreeSlot / addResource，对着 minecraft 的字节码核过）：选中的快捷栏格里是同一种、没满，
先并进它；再（副手：基岩版放不了食物和料，不看）按格号 0..35 并入同一种没满的栈；都没有才放进第一个空格，每格放满一栈。物品的比较和增减
用前置包的 Items（这里直接用真的）。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

Items = dgtest.load("Shared.Items")
Add = fdtest.load("Shared.Rules.InventoryAdd")
APPLE, STICK = "minecraft:apple", "minecraft:stick"


def stack(name, count, **extra):
    return Items.makeItem(name, count, **extra)


def empty():
    return [None] * 36


def counts(window, name=APPLE):
    return dict((index, item["count"]) for index, item in enumerate(window) if item and item["newItemName"] == name)


def testTheSelectedHotbarSlotIsFilledBeforeAnyLowerSlot():
    window = empty()
    window[0], window[5] = stack(APPLE, 10), stack(APPLE, 10)
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64, selected=5) is None
    assert counts(window) == {0: 10, 5: 15}, "选中的 5 号格先并，0 号格没动"


def testWithoutASelectionTheLowestSlotComesFirst():
    window = empty()
    window[0], window[5] = stack(APPLE, 10), stack(APPLE, 10)
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64) is None
    assert counts(window) == {0: 15, 5: 10}


def testTheSelectedSlotIsSkippedWhenItIsFullOrHoldsSomethingElse():
    window = empty()
    window[0], window[3], window[5] = stack(APPLE, 10), stack(APPLE, 64), stack(STICK, 3)
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64, selected=3) is None
    assert counts(window) == {0: 15, 3: 64}, "选中的满了：从 0 号格起"
    window[0] = None
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64, selected=5) is None
    assert counts(window) == {3: 64, 0: 5} and window[5]["newItemName"] == STICK, "选中的是别的东西：不并也不占"


def testAnEmptySelectedSlotAttractsNothingTheFirstEmptySlotIsUsed():
    window = empty()
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64, selected=5) is None
    assert counts(window) == {0: 5}, "选中的格子是空的：不算有位置可并，和别的空格一样，按格号第一个空格放"


def testTheFirstEmptySlotIsOnlyUsedWhenNoStackOfTheSameKindHasRoom():
    window = empty()
    window[0], window[1], window[20] = stack(STICK, 1), stack(APPLE, 64), stack(APPLE, 60)
    assert Add.addToWindow(Items, window, stack(APPLE, 10), 64, selected=0) is None
    assert counts(window) == {1: 64, 20: 64, 2: 6}, "20 号格先补满（4 个），余下 6 个才放进第一个空格（2 号）"


def testTheRemainderIsReturnedWhenThereIsNoRoomAtAll():
    window = [stack(STICK, 64) for _ in range(36)]
    window[7] = stack(APPLE, 60)
    rest = Add.addToWindow(Items, window, stack(APPLE, 20), 64, selected=7)
    assert rest == stack(APPLE, 16) and counts(window) == {7: 64}, "补满 7 号格的 4 个，余下 16 个原样返回"


def testAStackBiggerThanOneSlotIsSplitOverTheEmptySlots():
    window = empty()
    assert Add.addToWindow(Items, window, stack(APPLE, 150), 64, selected=-1) is None
    assert counts(window) == {0: 64, 1: 64, 2: 22}


def testThingsWithDifferentDataDoNotMerge():
    window = empty()
    window[0] = stack(APPLE, 10, userData={"a": 1})
    assert Add.addToWindow(Items, window, stack(APPLE, 5), 64, selected=0) is None
    assert counts(window) == {0: 10, 1: 5}, "不同的数据不是同一种：放进空格"
    assert Add.addToWindow(Items, window, stack(APPLE, 2, userData={"a": 1}), 64, selected=1) is None
    assert counts(window) == {0: 12, 1: 5}, "同样的数据才并（选中的 1 号格是没数据的，不是同一种）"


def testSomethingThatDoesNotStackNeverMerges():
    window = empty()
    window[0] = stack("minecraft:iron_pickaxe", 1)
    assert Add.addToWindow(Items, window, stack("minecraft:iron_pickaxe", 1), 1, selected=0) is None
    assert counts(window, "minecraft:iron_pickaxe") == {0: 1, 1: 1}


def testOnlyTheHotbarCanBeTheSelectedSlot():
    assert Add.mergeOrder(4, 36)[:3] == [4, 0, 1]
    assert Add.mergeOrder(-1, 36) == list(range(36)), "不知道选中的是哪格（-1）"
    assert Add.mergeOrder(9, 36) == list(range(36)) and Add.mergeOrder(35, 36) == list(range(36)), "9 以上不是快捷栏"


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
