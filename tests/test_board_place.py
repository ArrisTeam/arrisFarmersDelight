# -*- coding: utf-8 -*-
# runner: both
"""把一叠东西放上砧板（Shared/Rules/HandsOn/BoardPlace.py + Shared/Rules/BoardStation.py 的 Env）：放的判定树、取回、插工具。

移植自 HoD 的 BoardTests：aBurgerIsBuiltFromTheBreadUp、sixteenBurgersAtOnce、aSaladStartsFromItsBowl、theTopLayerComesBack、
everyCuttableFoodLiesDownToBeCut、cutFoodBecomesItsDishWhenTheNextLayerComes、aKnifeIsNoLayer、aToolThatIsALayerCutsOnlyWhatItCuts、
foodMovesAFinishedDishAside、whatTheHandHeldStaysWhenTheBoardCannotTakeIt、aToolIsStuckIntoTheBoardFromTheStation、
takingACarvedKnifeLeavesTheBoardBare、sixteenAreCutAtOnce（板上能放整叠）。
"""
from __future__ import print_function

import fdtest

Place = fdtest.load("Shared.Rules.HandsOn.BoardPlace")
Station = fdtest.load("Shared.Rules.BoardStation")
Dishes = fdtest.load("Shared.Rules.DishStation")
Data = fdtest.load("Shared.Data.Cutting")


def _typeOf(item):
    name = item["newItemName"]
    for word, kind in (("pickaxe", "pickaxe"), ("axe", "axe"), ("shovel", "shovel"), ("hoe", "hoe"), ("knife", "sword"), ("sword", "sword")):
        if word in name:
            return kind
    return "food" if name != "minecraft:cobblestone" else "block"


def _maxStack(item):
    return 16 if item["newItemName"] in ("minecraft:egg", "arris:milk_bottle") else 64


ENV = Station.Env(lambda name: name in Data.knifeList, _typeOf, _maxStack)


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def _place(carried, board=None, layers=(), one=False, byUse=False, env=ENV):
    return Place.place(carried, board, list(layers), one, byUse, env)


def _kinds(layers):
    return [(layer["newItemName"], layer["count"]) for layer in layers]


def _names(events):
    return [name for name, _data in events]


def testAWholeStackLiesOnABareBoardToBeCutAndTheMarksStartOver():
    result = _place(_item("arris:cabbage", 20))
    assert result.board == _item("arris:cabbage", 20) and result.moved == 20 and result.restart, "整叠放上去，不止 16 个"
    assert _names(result.events) == ["placed"] and result.layers == [] and not result.finish and result.give == []
    one = _place(_item("arris:cabbage", 20), one=True)
    assert one.moved == 1 and one.board["count"] == 1, "右键一个"
    eggs = Station.Env(lambda name: False, _typeOf, _maxStack)
    assert _place(_item("minecraft:egg", 20), env=eggs) is not None
    assert _place(_item("arris:cabbage", 70)).moved == 64, "按物品的最大堆叠，最多 BOARD_MAX"


def testTheSameFoodIsAddedToThePileUpToTheMostItHolds():
    board = _item("arris:cabbage", 60)
    result = _place(_item("arris:cabbage", 10), board)
    assert result.board["count"] == 64 and result.moved == 4 and not result.restart, "放满为止，不重布刀口"
    full = _place(_item("arris:cabbage", 3), _item("arris:cabbage", 64))
    assert full.moved == 0 and _names(full.events) == ["refused"] and full.board["count"] == 64
    one = _place(_item("arris:cabbage", 3), _item("arris:cabbage", 5), one=True)
    assert one.board["count"] == 6 and one.moved == 1


def testOtherFoodBouncesOffFoodWaitingToBeCut():
    result = _place(_item("minecraft:beef", 2), _item("arris:cabbage", 3))
    assert result.board == _item("arris:cabbage", 3) and result.moved == 0, "板上等着切的东西留着"
    assert result.events == [("refused", {"stack": _item("minecraft:beef", 1)})], "弹回的带一个当样子"


def testEveryCuttableFoodLiesDownToBeCutAndComesBack():
    for key in sorted(Data.CuttingBoardDict):
        item = _item(key[0], 3, key[1])
        if ENV.isTool(item, None):
            continue
        result = _place(item)
        assert result.board == item and result.layers == [] and result.moved == 3, key
        back = Place.take(result.board, [], ENV)
        assert back.board is None and back.give == [item] and back.events[0][0] == "taken", key


def testAFoodNoBowlOrBreadIsRefusedOnABareBoard():
    result = _place(_item("arris:tomato", 4))
    assert result.board is None and result.layers == [] and result.moved == 0, "番茄不是底座，板也不切它：留在手里"
    assert _names(result.events) == ["refused"]
    assert _place(_item("minecraft:crimson_fungus", 5)).moved == 0, "菌不是碗"


def testABurgerIsBuiltFromTheBreadUp():
    layers = []
    result = _place(_item("minecraft:bread", 3))
    assert _kinds(result.layers) == [("minecraft:bread", 3)] and result.moved == 3 and result.finish, "三个面包整叠当第 0 层"
    assert result.events == [("placed", {"at": 0})]
    layers = result.layers
    for name in ("arris:beef_patty", "arris:cabbage_leaf", "arris:tomato"):
        result = _place(_item(name), None, layers)
        assert result.moved == 1 and result.finish
        layers = result.layers
    assert _kinds(layers) == [("minecraft:bread", 3), ("arris:beef_patty", 1), ("arris:cabbage_leaf", 1), ("arris:tomato", 1)]
    carrot = _place(_item("minecraft:carrot"), None, layers)
    assert carrot.moved == 0 and carrot.layers == layers and _names(carrot.events) == ["refused"], "胡萝卜不属于任何汉堡"
    onion = _place(_item("arris:onion"), None, layers)
    assert onion.moved == 1 and len(onion.layers) == 5 and Dishes.completed([(layer["newItemName"], layer["newAuxValue"]) for layer in onion.layers])


def testSixteenBurgersAtOnce():
    layers = []
    leftovers = []
    for name in ("minecraft:bread", "arris:beef_patty", "arris:cabbage_leaf", "arris:tomato", "arris:onion"):
        carried = _item(name, 20)
        result = _place(carried, None, layers)
        layers = result.layers
        leftovers.append(20 - result.moved)
    assert _kinds(layers)[0] == ("minecraft:bread", 16) and all(count == 16 for _name, count in _kinds(layers))
    assert leftovers[-1] == 4, "多出的洋葱留在手里"


def testASaladStartsFromItsBowlAndTheThinnestLayerSaysHowMany():
    layers = _place(_item("minecraft:bowl", 3)).layers
    fungus = _place(_item("minecraft:crimson_fungus", 5), None, layers)
    assert fungus.moved == 3 and _kinds(fungus.layers)[-1] == ("minecraft:crimson_fungus", 3), "三个碗，三个菌；手上剩 2"
    warped = _place(_item("minecraft:warped_fungus", 2), None, fungus.layers)
    assert warped.moved == 2 and len(warped.layers) == 3
    complete = Dishes.completed([(layer["newItemName"], layer["newAuxValue"]) for layer in warped.layers])
    assert complete["result"][0] == "arris:nether_salad"
    assert Dishes.roundsOf(complete, [((layer["newItemName"], layer["newAuxValue"]), layer["count"]) for layer in warped.layers]) == 2, "两个，看最薄的"


def testRightClickPutsOneLayerAndALayerIsAtMostTheBase():
    layers = _place(_item("minecraft:bread", 5)).layers
    one = _place(_item("arris:beef_patty", 9), None, layers, one=True)
    assert one.moved == 1 and one.layers[-1]["count"] == 1
    many = _place(_item("arris:beef_patty", 9), None, layers)
    assert many.moved == 5, "以后的层最多和底座一样多"


def testTheTopLayerComesBackAndThenTheFoodOnTheBoard():
    layers = [_item("minecraft:bread", 1), _item("arris:tomato", 1)]
    result = Place.take(None, layers, ENV)
    assert _kinds(result.layers) == [("minecraft:bread", 1)] and result.give == [layers[1]]
    assert result.events == [("taken", {"stack": layers[1], "at": 1, "carved": False})], "带层号，客户端把那一层抬起来"
    last = Place.take(None, result.layers, ENV)
    assert last.layers == [] and last.events[0][1]["at"] == 0
    assert Place.take(None, [], ENV).events == [] and Place.take(None, [], ENV).give == []


def testFoodWaitingToBeCutBecomesLayerZeroWhenTheNextLayerComes():
    Dishes.rebuildIndex([{"ingredients": [("arris:cabbage", 0), ("arris:tomato", 0), ("minecraft:bowl", 0)], "result": ("x:salad", 0)},
                         {"ingredients": [("arris:cabbage", 0), ("arris:tomato", 0)], "result": ("x:slaw", 0)}])
    try:
        cabbage = _place(_item("arris:cabbage", 3))
        assert cabbage.board["count"] == 3 and cabbage.layers == [], "能切的先躺下等切，哪怕它是某道菜的底座"
        result = _place(_item("arris:tomato", 2), _item("arris:cabbage", 20))
        assert result.board is None and result.restart
        assert _kinds(result.layers)[0] == ("arris:cabbage", 16), "至多一整批 16 个当第 0 层"
        assert result.give == [_item("arris:cabbage", 4)], "多的还给厨师"
        assert result.moved == 2 and _kinds(result.layers)[1] == ("arris:tomato", 2)
    finally:
        Dishes.rebuildIndex()


def testAKnifeIsNoLayerItKnocksAndStaysInTheHand():
    bowl = _place(_item("minecraft:bowl")).layers
    result = _place(_item("arris:iron_knife"), None, bowl)
    assert result.ignored and result.moved == 0 and result.events == [] and result.layers == bowl, "什么都不发生"
    assert _place(_item("arris:iron_knife")).ignored and _place(_item("minecraft:iron_axe"), _item("arris:cabbage")).ignored


def testAToolThatIsAlsoALayerCutsOnlyWhatItCuts():
    bottle = Station.Env(lambda name: name == "x:bottle", lambda item: "food")
    saved = dict(Data.CuttingBoardDict)
    Data.CuttingBoardDict[("x:mould", 0)] = {"itemList": [{"itemName": "x:drink", "count": 1}], "tool": ["x:bottle"]}
    Dishes.rebuildIndex([{"ingredients": [("x:bottle", 0), ("x:fruit", 0)], "result": ("x:juice", 0)}])
    try:
        assert bottle.isTool(_item("x:bottle"), _item("x:mould")), "能切板上的东西：是工具"
        assert not bottle.isTool(_item("x:bottle"), None), "板上没有它能切的：是摆盘菜的一层"
        mould = _place(_item("x:mould"), env=bottle)
        assert mould.board["newItemName"] == "x:mould"
        knock = _place(_item("x:bottle"), mould.board, env=bottle)
        assert knock.ignored and knock.layers == [], "它是工具：不放"
        bare = _place(_item("x:bottle"), env=bottle)
        assert _kinds(bare.layers) == [("x:bottle", 1)], "空板上它当第一层放下"
    finally:
        Data.CuttingBoardDict.clear()
        Data.CuttingBoardDict.update(saved)
        Dishes.rebuildIndex()


def testFoodMovesAFinishedDishAsideAndBeefWaitingToBeCutStays():
    burgers = _item("arris:hamburger", 2)
    result = _place(_item("minecraft:beef", 3), burgers)
    assert result.board == _item("minecraft:beef", 3) and result.give == [burgers], "做好的菜给了厨师，牛肉躺下"
    assert result.events[0][0] == "taken" and result.events[0][1] == {"stack": burgers, "at": -1, "carved": False} and result.events[-1][0] == "placed"
    assert result.restart
    again = _place(_item("arris:cabbage"), result.board)
    assert again.board == _item("minecraft:beef", 3) and _names(again.events) == ["refused"], "等着切的牛肉留着，卷心菜弹回"
    block = _place(_item("arris:cabbage"), _item("minecraft:cobblestone"))
    assert block.board["newItemName"] == "arris:cabbage" and block.give == [_item("minecraft:cobblestone")], "没站点时放上去的方块也给厨师"


def testWhatTheHandHeldOnOpeningStaysQuietlyWhenTheBoardCannotTakeIt():
    assert _place(_item("minecraft:cobblestone", 5), byUse=True).events == [], "方块：一声不吭"
    food = _place(_item("arris:cabbage", 4), byUse=True)
    assert food.board["count"] == 4 and food.moved == 4, "食物整叠放下"
    beef = _place(_item("minecraft:beef", 2), food.board, byUse=True)
    assert beef.moved == 0 and beef.events == [], "别的食物留在手里，没有弹回也没有响"
    loud = _place(_item("minecraft:beef", 2), food.board)
    assert _names(loud.events) == ["refused"], "点板放的才会弹回"


def testAnEmptyHandOrAnEmptyStackPlacesNothing():
    assert _place(None).ignored and _place(_item("arris:cabbage", 0)).ignored


def testAToolIsStuckIntoABareBoardOnlyAndTakenOutWithAClick():
    knife = _item("arris:iron_knife", 3)
    result = Place.carve(knife, None, [], ENV)
    assert result.board == _item("arris:iron_knife", 1) and result.moved == 1 and _names(result.events) == ["carved"] and result.restart
    assert Place.carve(_item("arris:cabbage"), None, [], ENV).events[0][0] == "refused", "食物不是插的"
    assert Place.carve(knife, _item("arris:cabbage"), [], ENV).moved == 0, "板上有东西不能插"
    assert Place.carve(knife, None, [_item("minecraft:bowl")], ENV).moved == 0, "有层不能插"
    sword = _item("minecraft:iron_sword", 1)
    assert Place.carve(sword, None, [], ENV).moved == 0 or Place.carve(sword, None, [], ENV).moved == 1
    enchanted = dict(knife, enchantData=[(9, 1)])
    assert Place.carve(enchanted, None, [], ENV).moved == 0, "带附魔的不插：方块里只存名字 aux 数量，拔出来会丢附魔"
    out = Place.take(result.board, [], ENV)
    assert out.board is None and out.give == [result.board] and out.events == [("taken", {"stack": result.board, "at": -1, "carved": True})], \
        "拔出来：带 carved"


def testFoodLaidNextToACarvedKnifeSendsTheKnifeToTheCook():
    carved = _item("arris:iron_knife", 1)
    assert ENV.isCarving(carved) and ENV.isDone(carved)
    result = _place(_item("arris:cabbage", 3), carved)
    assert result.board == _item("arris:cabbage", 3) and result.give == [carved] and result.events[0][1]["carved"], "插着的刀挪给厨师"
    assert not ENV.isCarving(_item("arris:cabbage")) and not ENV.isDone(_item("arris:cabbage")), "等着切的不是没活干的"
    assert ENV.isDone(_item("arris:hamburger")) and not ENV.isDone(None)
    assert not _place(_item("arris:iron_knife"), _item("arris:cabbage")).give, "板上的食物不被刀挪开：刀是工具"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
