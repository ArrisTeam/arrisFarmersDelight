# -*- coding: utf-8 -*-
# runner: both
"""砧板站点的服务端逻辑（Compat/Diegesis/BoardLogic.py + BoardChop / BoardAssemble / BoardGive / BoardSlots，前置包的 Manager 是真的）：
放上去、一刀刀切、整叠切开、工具磨损、摆盘做成、取回、插工具、书里放料。引擎是 potfake 的假引擎（boardkit 补了物品类型和耐久）。
用例照 HoD 的 BoardTests：sixteenAreCutAtOnce、anEmptyHandCutsWithTheKnifeInTheInventory、aKnifeInTheOffHandCuts、marksAreCutInOrderAtNewPlaces、
anIgnoredChopIsAnswered、anotherCookKeepsTheMarks、aBurgerIsBuiltFromTheBreadUp、aSaladStartsFromItsBowl、theBookLaysADishFromTheInventory、
theTopLayerComesBack、aToolIsStuckIntoTheBoardFromTheStation、whatTheHandHeldStaysWhenTheBoardCannotTakeIt。
"""
from __future__ import print_function

import random

import dgtest
import boardkit as K
from boardkit import fake

KNIFE = "arris:iron_knife"
CABBAGE = "arris:cabbage"
Dishes = K.potfake.load("Shared.Rules.DishStation")


def _knife(slot, durability=100, playerId="a"):
    fake.give(playerId, slot, KNIFE, 1)
    fake.world.players[playerId]["inv"][slot]["durability"] = durability


def _chop(manager, mark, playerId="a", **extra):
    return K.do(manager, playerId, K.custom("chop", mark=mark, at=8.0, **extra))


def _logic(manager):
    return manager.stations[(0, K.BOARD)].logic


def _state(manager):
    return manager.stations[(0, K.BOARD)].state


def _names(events):
    return [name for name, _data in events]


def _inv(slot, playerId="a"):
    return fake.world.players[playerId]["inv"][slot]


def _place(manager, name, count, slot=3, **data):
    """背包放好、点托盘拿到光标栈上、点板放上去；返回 place 动作被不被接受。"""
    K.carry(manager, slot, name, count)
    return K.do(manager, "a", K.custom("place", **data))


def testAnOldPrerequisiteGetsNoBoardStation():
    assert K.BoardLogic.register(type("OldApi", (), {"API_VERSION": 2})) is None, "太旧的前置包：不登记，砧板走经典玩法"
    assert K.BoardLogic.register(type("NoVersion", (), {})) is None


def testOpeningBindsTheBoardAndLayerSlotsAndSendsTheMarks():
    manager, data = K.setup()
    data["cuttingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3}
    payload = K.opened(manager)
    state = payload["state"]
    assert sorted(state["slots"]) == ["board", "layers"] and state["slots"]["board"]["0"]["count"] == 3
    shared = state["data"]
    assert shared["marks"] == 0 and shared["plan"] == 1 and shared["style"] == "across" and shared["stroke"] == "cut" and shared["dish"] == ""
    assert len(shared["spots"]) == 1 and len(shared["angles"]) == 1


def testAWholeStackIsCarriedToTheBoardAndLiesThereToBeCut():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 20)
    assert K.board(data) == (CABBAGE, 20) and K.hand(manager) is None and _inv(3) is None, "整叠放上去，不止 16 个"
    assert _names(K.effects()) == ["placed"]
    assert _state(manager).getItem(("board", 0))["count"] == 20, "站点的槽就是方块里的那份"
    broadcast = [c for c in fake.calls if c[1] == "OnBlockItems"][-1][2][0]
    assert broadcast["items"]["0"]["count"] == 20, "旁观的人靠这条广播画"


def testRightClickPutsOneAndShiftClickFromTheTrayPutsTheWholeSlot():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 5, one=True)
    assert K.board(data) == (CABBAGE, 1) and K.hand(manager)["count"] == 4
    fake.give("a", 5, CABBAGE, 7)
    assert K.do(manager, "a", K.custom("place", **{"from": 5}))
    assert K.board(data) == (CABBAGE, 8) and _inv(5) is None, "Shift 点托盘：那一格整叠放上去"
    assert K.hand(manager)["count"] == 4, "光标栈上的没动"
    fake.give("a", 6, "minecraft:bread", 2)
    K.do(manager, "a", K.custom("place", **{"from": 6}))
    assert _inv(6)["count"] == 2 and K.board(data) == (CABBAGE, 8), "面包不放在等着切的菜上"
    assert K.do(manager, "a", K.custom("place", **{"from": 99})) and K.do(manager, "a", K.custom("place", **{"from": 20}))
    assert K.board(data) == (CABBAGE, 8), "越界的格号、空的格子：什么也不放"


def testWhatTheBoardRefusesBouncesBackAndTheHandKeepsIt():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "arris:tomato", 4)
    assert K.hand(manager)["count"] == 4 and K.board(data) is None
    assert K.effects() == [("refused", {"stack": {"newItemName": "arris:tomato", "newAuxValue": 0, "count": 1}})], "手上的留着，弹回的带一个当样子"


def testTheStackHeldAsTheBoardIsOpenedStaysQuietlyWhenTheBoardCannotTakeIt():
    manager, data = K.setup()
    K.opened(manager)
    fake.give("a", 0, "minecraft:cobblestone", 5)
    assert K.do(manager, "a", K.custom("place", **{"from": 0, "by_use": True}))
    assert _inv(0)["count"] == 5 and K.board(data) is None and K.effects() == [], "方块：一声不吭"
    fake.give("a", 1, CABBAGE, 4)
    K.do(manager, "a", K.custom("place", **{"from": 1, "by_use": True}))
    assert K.board(data) == (CABBAGE, 4) and _inv(1) is None, "食物整叠放下"
    K.effects()
    fake.give("a", 2, "minecraft:beef", 2)
    K.do(manager, "a", K.custom("place", **{"from": 2, "by_use": True}))
    assert _inv(2)["count"] == 2 and K.effects() == [], "别的食物留在手里，没有弹回也没有响"


def testOneChopCutsTheWholeStackOfCabbagesAndThePiecesGoToTheCook():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 2)
    K.effects()
    _knife(5)
    K.do(manager, "a", K.click(K.inv(5)))                    # 刀拿到光标栈上
    assert _chop(manager, 0)
    assert K.board(data) is None and K.count("arris:cabbage_leaf") == 4, "一刀把两个卷心菜都切开，叶子给厨师"
    assert K.hand(manager)["durability"] == 98, "每切一个磨损一次"
    events = K.effects()
    assert _names(events) == ["chopped"] and events[0][1]["tool"] == KNIFE and events[0][1]["item"] == CABBAGE
    assert events[0][1]["count"] == 2 and events[0][1]["done"] is True and events[0][1]["at"] == 8.0 and events[0][1]["yaw"] == 0


def testAnEmptyHandCutsWithTheKnifeInTheInventoryAndItStaysInItsSlot():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 2)
    _knife(7)
    assert K.hand(manager) is None
    assert _chop(manager, 0)
    assert K.board(data) is None and K.count("arris:cabbage_leaf") == 4
    assert _inv(7)["newItemName"] == KNIFE and _inv(7)["durability"] == 98, "刀留在原来的格子里"
    assert K.hand(manager) is None, "手上还是空的"


def testTheSelectedSlotsKnifeIsPickedBeforeTheOffHandAndTheRest():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 1)
    _knife(2, 50)
    _knife(7, 60)
    fake.world.players["a"]["offhand"] = {"newItemName": KNIFE, "newAuxValue": 0, "count": 1, "durability": 70}
    fake.world.players["a"]["selected"] = 7
    assert _chop(manager, 0)
    assert _inv(7)["durability"] == 59 and _inv(2)["durability"] == 50, "先选中的快捷栏格"
    assert fake.world.players["a"]["offhand"]["durability"] == 70


def testAKnifeInTheOffHandCutsWhenNothingElseHasOne():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 2)
    fake.world.players["a"]["offhand"] = {"newItemName": KNIFE, "newAuxValue": 0, "count": 1, "durability": 70}
    assert _chop(manager, 0)
    assert K.board(data) is None and K.count("arris:cabbage_leaf") == 4
    assert fake.world.players["a"]["offhand"]["durability"] == 68, "刀留在副手"


def testNoKnifeNoCutAndAWrongToolDoesNotCutEither():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 1)
    K.effects()
    assert _chop(manager, 0) and _names(K.effects()) == ["refused"] and K.board(data) == (CABBAGE, 1), "没刀：refused，菜还在"
    K.advance(0.2)
    fake.give("a", 6, "minecraft:iron_axe", 1)
    assert _chop(manager, 0) and _names(K.effects()) == ["refused"] and K.board(data) == (CABBAGE, 1), "斧切不了卷心菜"
    K.advance(0.2)
    _knife(7)
    K.do(manager, "a", K.click(K.inv(6)))                    # 光标栈上拿着斧，背包里有刀
    assert _chop(manager, 0) and _names(K.effects()) == ["refused"], "光标栈上拿着不对的工具：不去背包里找（HoD 一样当没有刀）"
    K.do(manager, "a", K.click(K.inv(6)))
    K.advance(0.2)
    assert _chop(manager, 0) and K.board(data) is None, "手空了：背包里的刀切"


def testAChopWithGarbageIsRefusedNotARaise():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 1)
    _knife(7)
    K.effects()
    for bad in (None, "0", -1, 5, True, 1.5):
        assert K.do(manager, "a", K.custom("chop", mark=bad, at=8.0)) and _names(K.effects()) == ["refused"], bad
        K.advance(0.2)
    assert K.do(manager, "a", K.custom("chop", mark=0, at="x", yaw=7)), "位置、朝向是坏的：夹成缺省，照切"
    assert K.board(data) is None
    look = K.effects()[0][1]
    assert look["at"] == 8.0 and look["yaw"] == 0 and "at_x" not in look


def testSixteenAreCutAtOnceAndTheRestWaitsForTheNextChop():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 20)
    _knife(7, 250)
    assert _chop(manager, 0)
    assert K.board(data) == (CABBAGE, 4) and K.count("arris:cabbage_leaf") == 32, "一刀切 16 个，每个两片叶子"
    assert _logic(manager).cut.marks == 0, "下一个有自己的刀口"
    K.advance(0.2)
    assert _chop(manager, 0) and K.board(data) is None and K.count("arris:cabbage_leaf") == 40


def testHamTakesTwoChopsOneAtATimeInOrderAndNeverTwoInOneInstant():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "arris:ham", 2)
    _knife(7, 250)
    K.effects()
    assert _chop(manager, 1) and _names(K.effects()) == ["refused"], "第二刀在第一刀之前：拒绝"
    K.advance(0.2)
    assert _chop(manager, 0) and _names(K.effects()) == ["chopped"] and K.board(data) == ("arris:ham", 2), "一刀切不开火腿"
    assert _chop(manager, 1) and _names(K.effects()) == ["refused"], "两刀间隔不到 0.15 秒"
    K.advance(0.2)
    assert _chop(manager, 0) and _names(K.effects()) == ["refused"], "同一刀不能再落"
    K.advance(0.2)
    assert _chop(manager, 1) and K.board(data) is None
    assert K.count("minecraft:porkchop") == 4 and K.count("minecraft:bone") == 2, "产物和骨头都给厨师"


def testAKnifeThatBreaksStopsTheBatchAndLeavesItsSlotEmpty():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 12)
    _knife(7, 5)
    sounds = len([c for c in fake.calls if c[1] == "OnPlaySound"])
    assert _chop(manager, 0)
    assert K.board(data) == (CABBAGE, 7) and K.count("arris:cabbage_leaf") == 10, "刀还剩 5 次：只切 5 个"
    assert _inv(7) is None, "刀坏了，那一格是空的（产物没有落进去被盖掉）"
    assert len([c for c in fake.calls if c[1] == "OnPlaySound"]) >= sounds + 2, "刀声和破碎声"


def _unbreaking(slot, level, picks):
    """背包第 slot 格的刀带上"耐久"附魔；picks 是耐久附魔掷骰子的结果（换掉 random.randint）。"""
    fake.world.players["a"]["inv"][slot]["enchantData"] = [(17, level)]
    saved = random.randint
    random.randint = lambda low, high: picks(low, high)
    return saved


def testAnUnbreakingKnifeCutsPastItsDurabilityAndLosesNoneOfIt():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 12)
    _knife(7, 5)
    saved = _unbreaking(7, 3, lambda low, high: high)               # 每一下都免磨
    try:
        assert _chop(manager, 0)
    finally:
        random.randint = saved
    assert K.board(data) is None and K.count("arris:cabbage_leaf") == 24, "耐久只剩 5 的刀把 12 个都切了"
    assert _inv(7)["durability"] == 5, "一点没磨"


def testAnUnbreakingKnifeStillBreaksWhenTheRollsSayWear():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, CABBAGE, 12)
    _knife(7, 5)
    saved = _unbreaking(7, 3, lambda low, high: low)                # 每一下都要磨
    try:
        assert _chop(manager, 0)
    finally:
        random.randint = saved
    assert K.board(data) == (CABBAGE, 7) and K.count("arris:cabbage_leaf") == 10 and _inv(7) is None, "和没有附魔一样：切 5 个、刀坏了"


def testCreativeModeWearsNothing():
    manager, data = K.setup(creative=True)
    K.opened(manager)
    assert _place(manager, CABBAGE, 2)
    _knife(7, 100)
    assert _chop(manager, 0)
    assert _inv(7)["durability"] == 100


def testAnotherCookKeepsTheMarksAndTheLastOneLeavingStartsOver():
    manager, data = K.setup()
    K.opened(manager)
    K.opened(manager, "b")
    assert _place(manager, "arris:ham", 2)
    _knife(7, 250)
    assert _chop(manager, 0) and _logic(manager).cut.marks == 1
    manager.close("a")
    assert _logic(manager).cut.marks == 1, "一个人离开不动刀口"
    assert _state(manager).getItem(("board", 0))["count"] == 2
    manager.close("b")
    K.opened(manager)
    assert _logic(manager).cut.marks == 0, "最后一个人离开，刀口重布"


def testTheMarksStartOverWhenTheBoardIsChangedFromOutsideButNotWhenOnlyTheCountIs():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "arris:ham", 2)
    _knife(7, 250)
    assert _chop(manager, 0) and _logic(manager).cut.marks == 1
    data["cuttingDict"] = {"newItemName": "arris:ham", "newAuxValue": 0, "count": 5}           # 往一叠上接着放（经典玩法 / 漏斗）
    manager.tick(0.3)
    assert _logic(manager).cut.marks == 1, "数量变了不重布刀口"
    data["cuttingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}      # 换了东西
    manager.tick(0.3)
    assert _logic(manager).cut.marks == 0 and _logic(manager).cut.plan.marks == 1


def testTheTopLayerComesBackAndThenWhatLiesOnTheBoard():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:bread", 1)
    assert _place(manager, "arris:tomato", 1, slot=4)
    assert K.layers(data) == [("minecraft:bread", 1), ("arris:tomato", 1)]
    K.effects()
    assert K.do(manager, "a", K.custom("take"))
    assert K.layers(data) == [("minecraft:bread", 1)] and K.count("arris:tomato") == 1, "最上一层回到厨师手里"
    assert K.effects() == [("taken", {"stack": {"newItemName": "arris:tomato", "newAuxValue": 0, "count": 1}, "at": 1, "carved": False})]
    K.do(manager, "a", K.custom("take"))
    assert K.layers(data) == [] and K.count("minecraft:bread") == 1 and K.board(data) is None
    assert _place(manager, CABBAGE, 3, slot=5)
    K.do(manager, "a", K.custom("take"))
    assert K.board(data) is None and K.count(CABBAGE) == 3, "没有层：板上的整个还回去"


def testABurgerIsBuiltFromTheBreadUpAndTheBreadNotUsedGoesBack():
    manager, data = K.setup()
    K.opened(manager)
    for slot, (name, count) in enumerate((("minecraft:bread", 3), ("arris:beef_patty", 1), ("arris:cabbage_leaf", 1), ("arris:tomato", 1))):
        assert _place(manager, name, count, slot=10 + slot)
    assert K.layers(data) == [("minecraft:bread", 3), ("arris:beef_patty", 1), ("arris:cabbage_leaf", 1), ("arris:tomato", 1)]
    assert [c["count"] for c in manager.stations[(0, K.BOARD)].state.getItems("layers") if c] == [3, 1, 1, 1]
    K.effects()
    assert _place(manager, "minecraft:carrot", 1, slot=20)
    assert len(K.layers(data)) == 4 and _names(K.effects()) == ["refused"], "胡萝卜不属于任何汉堡"
    K.do(manager, "a", K.click(K.inv(0), kind="PUT_AWAY"))
    assert _place(manager, "arris:onion", 1, slot=21)
    events = _names(K.effects())
    assert K.layers(data) == [] and K.board(data) == ("arris:hamburger", 1), "最后一层放对：直接做成，一份"
    assert "assembled" in events and K.count("minecraft:bread") == 2, "没用上的面包还给厨师"
    K.do(manager, "a", K.custom("take"))
    assert K.count("arris:hamburger") == 1 and K.board(data) is None, "点一下拿走"


def testTheAssembledEventSaysHowTheDishWasFinished():
    # JE BoardTests.everyFoodCraftComesToTheBoard：碗里有肉的菜是"摆"不是"拌"，盛宴 / 蛋糕是整块（block）
    for name, finish, block, layers in (
            ("arris:steak_and_potatoes", "arrange", False, ("minecraft:bowl", "arris:cooked_rice", "minecraft:cooked_beef", "minecraft:baked_potato", "arris:onion")),
            ("arris:mixed_salad", "toss", False, ("minecraft:bowl", "arris:cabbage", "minecraft:beetroot", "arris:tomato")),
            ("minecraft:cake", "press", True, ("minecraft:wheat", "arris:milk_bottle", "arris:milk_bottle", "arris:milk_bottle", "minecraft:sugar", "minecraft:egg",
                                               "minecraft:sugar", "minecraft:wheat", "minecraft:wheat"))):
        manager, data = K.setup()
        K.opened(manager)
        K.effects()
        for index, layer in enumerate(layers):
            assert _place(manager, layer, 1, slot=10 + index), (name, layer)
        if K.layers(data):                       # 还能长成更大的菜（沙拉长成闪耀沙拉）：等厨师点一下（JE 的 finishIfItWaits）
            assert K.do(manager, "a", K.custom("assemble")), name
        assert K.board(data) == (name, 1), name
        assembled = [payload for event, payload in K.effects() if event == "assembled"]
        assert len(assembled) == 1 and assembled[0]["finish"] == finish and assembled[0]["block"] is block, (name, assembled)


def testASaladStartsFromItsBowlAndTheThinnestLayerSaysHowManyAreMade():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:crimson_fungus", 5)
    assert K.layers(data) == [] and K.board(data) is None and K.hand(manager)["count"] == 5, "菌不是碗"
    K.do(manager, "a", K.click(K.inv(0), kind="PUT_AWAY"))
    assert _place(manager, "minecraft:bowl", 3, slot=4)
    assert K.do(manager, "a", K.custom("place", **{"from": 3}))
    assert K.layers(data) == [("minecraft:bowl", 3), ("minecraft:crimson_fungus", 3)] and _inv(3)["count"] == 2, "三个碗，三个菌；剩 2"
    fake.give("a", 6, "minecraft:warped_fungus", 2)
    assert K.do(manager, "a", K.custom("place", **{"from": 6}))
    assert K.layers(data) == [] and K.board(data) == ("arris:nether_salad", 2), "最后一个做成：两份，和最少的一层一样多"
    assert K.count("minecraft:bowl") == 1 and K.count("minecraft:crimson_fungus") == 3, "一个碗和一个菌还回来（另外 2 个菌本来就没放）"


def testADishThatCouldGrowBiggerWaitsForTheCooksWordUnlessItIsThePicked():
    Dishes.rebuildIndex([{"ingredients": [("minecraft:bowl", 0), ("x:a", 0)], "result": ("x:small", 0)},
                         {"ingredients": [("minecraft:bowl", 0), ("x:a", 0), ("x:b", 0)], "result": ("x:big", 0)}])
    try:
        manager, data = K.setup()
        K.opened(manager)
        assert _place(manager, "minecraft:bowl", 2)
        assert _place(manager, "x:a", 2, slot=4)
        assert K.layers(data) == [("minecraft:bowl", 2), ("x:a", 2)] and "assembled" not in _names(K.effects()), "还能长成更大的：等厨师点一下"
        assert _state(manager).getData()["dish"] == "x:small", "站点数据里写着层现在能做成哪道"
        assert K.do(manager, "a", K.custom("assemble"))
        assert K.board(data) == ("x:small", 2) and K.layers(data) == []
        assert not K.do(manager, "a", K.custom("assemble")) and "refused" in _names(K.effects()), "没有层凑不成菜：拒绝"
        K.do(manager, "a", K.custom("take"))
        fake.world.players["a"]["inv"][:] = [None] * 36
        fake.give("a", 8, "minecraft:bowl", 2)
        fake.give("a", 9, "x:a", 2)
        assert K.do(manager, "a", K.custom("bookFill", key="d:x:small", sets=1)), "书里点的那道：层一凑齐就做成，哪怕还能长"
        assert K.board(data) == ("x:small", 1) and K.layers(data) == []
    finally:
        Dishes.rebuildIndex()


def testAnAssembledDishThatDoesNotFitTheBoardGoesToTheCook():
    manager, data = K.setup()
    K.opened(manager)
    fake.give("a", 5, "minecraft:honey_bottle", 16)
    fake.give("a", 6, "minecraft:wheat", 40)
    assert K.do(manager, "a", K.custom("bookFill", key="d:arris:honey_cookie", sets=16))
    assert K.board(data) == ("arris:honey_cookie", 64) and K.count("arris:honey_cookie") == 64, "16 份 x 8 块 = 128：板上放一叠，其余给厨师"
    assert K.count("minecraft:glass_bottle") == 16 and K.count("minecraft:wheat") == 8, "每份的空瓶还回来，小麦用了 32"


def testTheBookLaysADishFromTheInventoryAndADishMadeBeforeIsTakenOff():
    manager, data = K.setup()
    K.opened(manager)
    fake.give("a", 5, "minecraft:bowl", 20)
    fake.give("a", 6, "minecraft:crimson_fungus", 20)
    fake.give("a", 7, "minecraft:warped_fungus", 20)
    assert K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=16))
    assert K.board(data) == ("arris:nether_salad", 16), "Shift 点书：16 份"
    assert K.count("minecraft:bowl") == 4 and K.count("minecraft:warped_fungus") == 4, "料从背包里取"
    assert K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1))
    assert K.board(data) == ("arris:nether_salad", 1) and K.count("arris:nether_salad") == 16, "再点一份：做好的 16 份还给厨师"
    fake.world.players["a"]["inv"][:] = [None] * 36
    K.do(manager, "a", K.custom("take"))
    assert not K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1)), "背包里什么也没有：板上也什么都没有"
    assert K.board(data) is None and K.layers(data) == []
    assert _place(manager, "minecraft:bowl", 3, slot=1)
    fake.give("a", 2, "minecraft:crimson_fungus", 5)
    fake.give("a", 3, "minecraft:warped_fungus", 5)
    assert K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1))
    assert K.board(data) == ("arris:nether_salad", 3), "已经摆着三个碗：书里补齐三份"


def testTheBookLeavesFoodWaitingToBeCutAndTakesAnyKeyOnlyAsARequest():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:beef", 2)
    fake.give("a", 5, "minecraft:bowl", 4)
    fake.give("a", 6, "minecraft:crimson_fungus", 4)
    fake.give("a", 7, "minecraft:warped_fungus", 4)
    assert not K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=16))
    assert K.board(data) == ("minecraft:beef", 2), "等着切的牛肉留着板"
    for key in (None, 3, "d:nothing", "c:minecraft:beef:0", {"x": 1}):
        assert not K.do(manager, "a", K.custom("bookFill", key=key, sets=1)), key
    assert K.board(data) == ("minecraft:beef", 2)


def testAToolIsStuckIntoTheBareBoardAndPulledOutByAClick():
    manager, data = K.setup()
    K.opened(manager)
    _knife(3, 77)
    K.do(manager, "a", K.click(K.inv(3)))
    K.effects()
    assert K.do(manager, "a", K.custom("carve"))
    assert K.board(data) == (KNIFE, 1) and K.hand(manager) is None and data["cuttingDict"]["durability"] == 77
    assert _names(K.effects()) == ["carved"]
    K.do(manager, "a", K.custom("take"))
    assert K.board(data) is None and K.count(KNIFE) == 1 and _inv(0)["durability"] == 77, "拔出来：耐久还在"
    assert K.effects()[0] == ("taken", {"stack": {"newItemName": KNIFE, "newAuxValue": 0, "count": 1, "durability": 77}, "at": -1, "carved": True})


def testFoodLaidNextToACarvedKnifeSendsTheKnifeToTheCook():
    manager, data = K.setup()
    data["cuttingDict"] = {"newItemName": KNIFE, "newAuxValue": 0, "count": 1}
    K.opened(manager)
    assert _place(manager, CABBAGE, 3)
    assert K.board(data) == (CABBAGE, 3) and K.count(KNIFE) == 1


def testAFinishedDishFromBeforeGivesWayToFood():
    manager, data = K.setup()
    data["cuttingDict"] = {"newItemName": "arris:hamburger", "newAuxValue": 0, "count": 2}
    K.opened(manager)
    assert _place(manager, "minecraft:beef", 3)
    assert K.board(data) == ("minecraft:beef", 3) and K.count("arris:hamburger") == 2, "做好的菜挪给厨师，牛肉躺下等切"


def _give(slot, name, count=1, **data):
    """背包第 slot 格放一件带数据（附魔、改名……）的东西，不点它。"""
    fake.give("a", slot, name, count)
    _inv(slot).update(data)


def _stacks(name):
    """玩家背包里所有 name 的格子（物品字典）。"""
    return [item for item in fake.world.players["a"]["inv"] if item and item["newItemName"] == name]


def testAnEnchantedAndDyedItemLiesOnTheBoardWholeAndComesBackWhole():
    manager, data = K.setup()
    K.opened(manager)
    _give(5, "minecraft:leather_chestplate", enchantData=[(0, 3)], userData={"customColor": 123}, customTips="mine", extraId="id7")
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert K.do(manager, "a", K.custom("place")) and K.board(data) == ("minecraft:leather_chestplate", 1)
    saved = data["cuttingDict"]
    assert saved["enchantData"] == [[0, 3]] and saved["userData"] == {"customColor": 123} and saved["extraId"] == "id7", "方块实体数据里是列表、字典，不是元组"
    assert saved["customTips"] == "mine"
    assert _state(manager).getItem(("board", 0))["enchantData"] in ([[0, 3]], [(0, 3)]), "站点的槽也带着"
    assert K.do(manager, "a", K.custom("take")) and K.board(data) is None
    back = _stacks("minecraft:leather_chestplate")
    assert len(back) == 1 and back[0]["enchantData"] == [(0, 3)] and back[0]["userData"] == {"customColor": 123} and back[0]["extraId"] == "id7",         "取回的还是那件：附魔换回元组交给引擎"
    assert back[0]["customTips"] == "mine"


def testAnEnchantedKnifeIsStuckIntoTheBoardAndPulledOutAgainWithItsEnchantsAndExtraId():
    manager, data = K.setup()
    K.opened(manager)
    _knife(3, 77)
    _inv(3).update(enchantData=[(9, 2), (17, 1)], extraId="knife-1")
    K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("carve")) and K.board(data) == (KNIFE, 1), "附魔的刀也插得进"
    assert data["cuttingDict"]["extraId"] == "knife-1" and data["cuttingDict"]["durability"] == 77
    K.do(manager, "a", K.custom("take"))
    knife = _stacks(KNIFE)[0]
    assert knife["durability"] == 77 and knife["enchantData"] == [(9, 2), (17, 1)] and knife["extraId"] == "knife-1", "拔出来：耐久、附魔、extraId 都在（审查 B7）"


def testWhatCannotBeKeptStaysInTheHandAndTheBoardTakesNoLeftovers():
    manager, data = K.setup()
    K.opened(manager)
    _give(5, CABBAGE, 3, userData={"weird": [1, "a"]})
    assert K.do(manager, "a", K.custom("place", **{"from": 5, "by_use": True}))
    assert K.board(data) is None and _inv(5)["count"] == 3 and K.effects() == [], "开站时手里的：存不住就一声不吭留在手里"
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert K.do(manager, "a", K.custom("place")) and K.board(data) is None and K.hand(manager)["count"] == 3
    assert _names(K.effects()) == ["refused"], "拿在光标栈上点板：弹回"


def testTheBreadNotUsedGoesBackWithItsOwnData():
    manager, data = K.setup()
    K.opened(manager)
    _give(10, "minecraft:bread", 3, customTips="fresh")
    assert K.do(manager, "a", K.click(K.inv(10))) and K.do(manager, "a", K.custom("place"))
    assert data["dishLayers"][0]["customTips"] == "fresh" and K.layers(data) == [("minecraft:bread", 3)]
    for slot, (name, count) in enumerate((("arris:beef_patty", 1), ("arris:cabbage_leaf", 1), ("arris:tomato", 1), ("arris:onion", 1))):
        assert _place(manager, name, count, slot=11 + slot)
    assert K.board(data) == ("arris:hamburger", 1)
    bread = _stacks("minecraft:bread")
    assert len(bread) == 1 and bread[0]["count"] == 2 and bread[0]["customTips"] == "fresh", "没用上的面包带着自己的数据还回来"


def testTheBookDoesNotUseTheItemsThatCarryDataItWouldLose():
    manager, data = K.setup()
    K.opened(manager)
    for slot, name in enumerate(("minecraft:bowl", "minecraft:crimson_fungus", "minecraft:warped_fungus")):
        fake.give("a", 5 + slot, name, 4)
    _inv(6)["customTips"] = "special"
    assert not K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1)), "料不够（带数据的那格不算）：什么也没放"
    assert K.board(data) is None and _inv(6)["count"] == 4 and _inv(6)["customTips"] == "special"
    fake.give("a", 9, "minecraft:crimson_fungus", 4)
    assert K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1)) and K.board(data) == ("arris:nether_salad", 1)
    assert _inv(6)["count"] == 4 and _inv(9)["count"] == 3, "用的是不带数据的那格"


def testAKnifeIsNoLayerAndKnocksWithoutAnythingHappening():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:bowl", 1)
    _knife(5)
    K.do(manager, "a", K.click(K.inv(5)))
    K.effects()
    assert K.do(manager, "a", K.custom("place"))
    assert K.layers(data) == [("minecraft:bowl", 1)] and K.hand(manager)["newItemName"] == KNIFE and K.effects() == [], "刀留在手里，什么事件也没有"


def testALegacyFinishedDishIsMovedOntoTheBoardWhenItIsOpened():
    manager, data = K.setup()
    data["dishDone"] = {"newItemName": "arris:hamburger", "newAuxValue": 0, "count": 3}
    K.opened(manager)
    assert K.board(data) == ("arris:hamburger", 3) and data["dishDone"] is None


def testTheStateFollowsTheBlocksDataWhetherTheStationOrAnotherPathChangedIt():
    manager, data = K.setup()
    K.opened(manager)
    data["cuttingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}
    manager.tick(0.3)
    sent = fake.world.take("a", K.Protocol.EP_STATE)
    assert sent and sent[-1][2]["state"]["slots"]["board"]["0"]["newItemName"] == "minecraft:beef", "漏斗 / 经典玩法改的，使用者也马上看到"
    assert _logic(manager).cut.plan.marks == 1


def testTheKernelCanTakeFromTheBoardSlotButNeverPutIntoIt():
    manager, data = K.setup()
    data["cuttingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}
    K.opened(manager)
    slot = {"kind": "station", "group": "board", "index": 0}
    assert K.do(manager, "a", K.click(slot))
    assert K.hand(manager)["count"] == 2 and K.board(data) is None, "mayTake：整叠拿到光标栈上"
    assert not K.do(manager, "a", K.click(slot)) and K.board(data) is None and K.hand(manager)["count"] == 2, "什么也放不进去：mayPlace 一律 false"
    layer = {"kind": "station", "group": "layers", "index": 0}
    assert not K.do(manager, "a", K.click(layer)), "层的槽也不收"


def testPlacingOnAnUnfinishedStackOfLayersTakesOnlyWhatContinuesADish():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:bread", 2)
    K.effects()
    assert _place(manager, "minecraft:beef", 2, slot=4)
    assert K.board(data) is None and K.hand(manager)["count"] == 2 and _names(K.effects()) == ["refused"], "有层了：生牛肉不是汉堡的料，不躺下等切"
    assert len(K.layers(data)) == 1


def testTheLayersAreBroadcastToEveryoneAndTheBoardItemIsOnlyDrawnWithoutLayers():
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:bread", 2)
    last = [c for c in fake.calls if c[1] == "OnBlockItems"][-1][2][0]
    assert last["items"]["L0"]["count"] == 2 and not last["items"].get("0"), "有层画层"
    K.do(manager, "a", K.custom("take"))
    last = [c for c in fake.calls if c[1] == "OnBlockItems"][-1][2][0]
    assert not last["items"].get("L0") and not last["items"].get("0"), "拿空了：什么也不画"


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
