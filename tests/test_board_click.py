# -*- coding: utf-8 -*-
# runner: both
"""点砧板这一下算什么（Shared/Rules/BoardClick.py）和手空着时借背包里哪把刀（BoardStation.Env.toolSlot）。

对应 HoD 的 BoardBehavior.onItemClick / onEvent、Cutting.toolSlot，和 BoardTests 的 anEmptyHandCutsWithTheKnifeInTheInventory、
aKnifeInTheOffHandCuts、anEmptyHandWithoutAKnifeCutsNothing。
"""
from __future__ import print_function

import fdtest

Click = fdtest.load("Shared.Rules.BoardClick")
Station = fdtest.load("Shared.Rules.BoardStation")
Data = fdtest.load("Shared.Data.Cutting")


def _typeOf(item):
    name = item["newItemName"]
    return "sword" if "knife" in name else ("axe" if name.endswith("_axe") else "food")


ENV = Station.Env(lambda name: name in Data.knifeList, _typeOf)


def _item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


CABBAGE, KNIFE, AXE, BREAD = _item("arris:cabbage", 3), _item("arris:iron_knife"), _item("minecraft:iron_axe"), _item("minecraft:bread", 2)


def _with(hand, button=0, shift=False, board=None, layers=(), ready=False, cutsBoard=False):
    return Click.withStack(ENV, hand, button, shift, board, list(layers), ready, cutsBoard)


def testFoodInHandIsPlacedAllWithTheLeftButtonAndOneWithTheRight():
    assert _with(CABBAGE) == (Click.PLACE, False) and _with(CABBAGE, button=1) == (Click.PLACE, True)
    assert _with(BREAD, board=None) == (Click.PLACE, False), "放得下放不下由服务端说，点一下都是 place"


def testAKnifeInHandOverFoodCutsAndWithTheRightButtonGoesBackToTheBag():
    assert _with(KNIFE, board=CABBAGE, cutsBoard=True) == (Click.CHOP,)
    assert _with(KNIFE, button=1, board=CABBAGE, cutsBoard=True) == (Click.PUT_AWAY,), "右键手上的工具：放回背包"
    assert _with(AXE, board=CABBAGE, cutsBoard=False) == (Click.KNOCK,), "斧头切不了卷心菜：敲一声，留在手里"
    assert _with(KNIFE, board=None) == (Click.KNOCK,), "板上没有东西：敲一声"


def testAKnifeIsNeverLaidAsALayerAndFinishesADishThatIsReady():
    layers = [_item("minecraft:bread"), _item("arris:beef_patty")]
    assert _with(KNIFE, layers=layers, ready=False) == (Click.KNOCK,)
    assert _with(KNIFE, layers=layers, ready=True) == (Click.ASSEMBLE,), "刀落在凑成菜的层上：做成"
    assert _with(KNIFE, button=1, layers=layers, ready=True) == (Click.PUT_AWAY,)
    assert _with(_item("arris:tomato"), layers=layers, ready=True) == (Click.PLACE, False), "别的东西接着往上放"


def testShiftWithAToolOnABareBoardSticksItInButNotOnFoodOrLayers():
    assert _with(KNIFE, shift=True) == (Click.CARVE,)
    assert _with(KNIFE, shift=True, board=CABBAGE, cutsBoard=True) == (Click.CHOP,)
    assert _with(KNIFE, shift=True, layers=[_item("minecraft:bread")]) == (Click.KNOCK,)
    assert _with(CABBAGE, shift=True) == (Click.PLACE, False), "食物不是插的"
    carved = _item("arris:iron_knife")
    assert _with(AXE, shift=True, board=carved) == (Click.KNOCK,), "板上已经插着一把：不再插"


def testABareHandTakesBackOrFinishesOrCuts():
    assert Click.bareHand(0, CABBAGE, [], False, toolBorrowed=True, carved=False) == (Click.CHOP,), "左键 + 背包里有刀：落刀（要光标在食物上才算）"
    assert Click.bareHand(0, CABBAGE, [], False, toolBorrowed=False, carved=False) == (Click.TAKE,), "没有刀的左键：取回"
    assert Click.bareHand(1, CABBAGE, [], False, toolBorrowed=True, carved=False) == (Click.TAKE,), "右键：取回"
    layers = [_item("minecraft:bread")]
    assert Click.bareHand(0, None, layers, True, False, False) == (Click.ASSEMBLE,) and Click.bareHand(1, None, layers, True, False, False) == (Click.TAKE,)
    assert Click.bareHand(0, None, layers, False, False, False) == (Click.TAKE,), "凑不成：拿最上一层"
    assert Click.bareHand(0, KNIFE, [], False, True, True) == (Click.TAKE,) and Click.bareHand(1, KNIFE, [], False, False, True) == (Click.TAKE,), "插着的刀：任一键都拔出来"
    assert Click.bareHand(0, None, [], False, True, False) == (Click.NOTHING,)


def testTheKnifeOfTheSelectedSlotIsBorrowedBeforeTheOffHandAndThenTheRestInOrder():
    items = [None] * 36
    items[2], items[7] = _item("arris:iron_knife"), _item("arris:flint_knife")
    offhand = _item("arris:iron_knife")
    assert ENV.toolSlot(CABBAGE, items, 7, offhand) == ("inv", 7)
    assert ENV.toolSlot(CABBAGE, items, 5, offhand) == ("offhand",), "选中的格子里没有：副手"
    assert ENV.toolSlot(CABBAGE, items, 5, None) == ("inv", 2), "再按 0..35 的顺序"
    assert ENV.toolSlot(CABBAGE, items, -1, None) == ("inv", 2)
    items[2] = items[7] = None
    assert ENV.toolSlot(CABBAGE, items, 7, None) is None, "没有刀：不能切"
    items[30] = _item("arris:iron_knife")
    assert ENV.toolSlot(CABBAGE, items, 30, None) == ("inv", 30), "选中格只看快捷栏（0-8），30 号格是按序找到的"
    assert ENV.toolSlot(_item("minecraft:oak_log"), items, 7, None) is None, "刀削不了原木"
    items[31] = _item("minecraft:iron_axe")
    assert ENV.toolSlot(_item("minecraft:oak_log"), items, 7, None) == ("inv", 31)
    assert ENV.toolSlot(None, items, 7, None) is None, "板上没东西"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
