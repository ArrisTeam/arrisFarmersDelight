# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点的服务端逻辑（Compat/Diegesis/PotLogic.py + PotScoop.py + BookFill.py + Server/PotServe.py，前置包的 Manager 是真的）：
放料、摆料、盛出、取回、照书放料、右键盛菜、经验。引擎是 potfake.py 里的假的；烹饪与外观广播见 test_pot_cooking_server.py。"""
from __future__ import print_function

import dgtest
import potkit as K
from potkit import BOWL, POT, SAUCE, TOMATO, fake

Protocol = K.Protocol
HandCooking = K.HandCooking


def testOpeningBindsTheSlotsAndSendsTheStateTheDataAndTheControls():
    manager, data = K.setup()
    fake.setContainer(POT, 0, TOMATO, 3)
    fake.setContainer(POT, 7, "arris:dumplings", 4)
    payload = K.opened(manager)
    state = payload["state"]
    assert state["slots"]["ingredients"]["0"]["count"] == 3 and state["slots"]["ingredients"]["1"] == {}
    assert state["slots"]["served"]["0"]["newItemName"] == "arris:dumplings", "产出格是容器的 7 号格"
    assert sorted(state["controls"]) == ["heated", "progress", "spoon_x", "spoon_z", "stars", "stirring"]
    assert payload["hand"] is None and payload["yaw"] == 0
    shared = state["data"]
    assert sorted(shared) == ["batch", "bonus", "cook_left", "dish", "grade", "here", "made", "made_all", "meal", "mode", "open_stars", "sunk",
                              "vessel", "vessel_name"], sorted(shared)
    assert shared["here"] is True and shared["made"] == 0 and shared["open_stars"] == 1 and shared["sunk"] == []
    assert shared["dish"] == {} and shared["meal"] == {} and shared["vessel"] == {}


def testAStackIsCarriedToThePotAndTheFoodIsLaidOutForTheDishItMakes():
    manager, data = K.setup()
    fake.give("a", 3, TOMATO, 16)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.click(K.slot(0)))
    assert K.shape(K.cells())[:2] == [(TOMATO, 16), None], "16 个番茄先整堆躺在 0 号格"
    assert fake.world.players["a"]["inv"][3] is None
    fake.world.take()
    manager.tick(0.05)
    assert K.shape(K.cells())[:3] == [(TOMATO, 8), (TOMATO, 8), None], "下一刻按番茄酱的写法摆成两格"
    states = fake.world.take("a", Protocol.EP_STATE)
    assert states and states[-1][2]["state"]["data"]["dish"]["newItemName"] == SAUCE, "数据里是它做的那道菜"
    assert HandCooking.handOf(0, POT).clock._handFed is True, "站点里放的料算手放的"


def testADishContainerDoesNotGoInButEverythingElseDoes():
    manager, data = K.setup()
    fake.give("a", 0, BOWL, 3)
    fake.give("a", 1, "minecraft:dirt", 2)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(0)))
    assert not K.do(manager, "a", K.click(K.slot(0))), "碗是盛菜的，不下锅"
    assert manager.sessions["a"].hand["count"] == 3 and K.cells()[0] == {}
    assert K.do(manager, "a", K.click(K.inv(0), kind="PUT_AWAY"))
    assert K.do(manager, "a", K.click(K.inv(1))) and K.do(manager, "a", K.click(K.slot(2)))
    assert K.shape(K.cells())[2] == ("minecraft:dirt", 2), "凑不成菜的东西也收，原样躺着"
    manager.tick(0.05)
    assert K.shape(K.cells())[2] == ("minecraft:dirt", 2)


def testShiftClickMovesTheWholeStackIntoTheFirstSlotsAndRightClickPutsOne():
    manager, data = K.setup()
    fake.give("a", 4, "arris:onion", 20)
    fake.give("a", 5, "arris:onion", 5)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(4), kind="QUICK_MOVE"))
    assert K.shape(K.cells())[0] == ("arris:onion", 20)
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert K.do(manager, "a", K.click(K.slot(0), button=1)), "右键放一个"
    assert K.shape(K.cells())[0] == ("arris:onion", 21) and manager.sessions["a"].hand["count"] == 4


def testAWholeStackThrownInComesBackTheWayAContainerGivesIt():
    """一下子丢进 64 个：按菜摆成两格各 32；点一格 = 那一格整叠到手上，双击（PICKUP_ALL）= 两格都收到手上，再点背包的格子放回；
    Shift 点 = 那一格直接进背包（Diegesis 的 FocusInput.clickItem，和原版容器一样）。"""
    manager, data = K.setup()
    fake.give("a", 3, TOMATO, 64)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3))) and K.do(manager, "a", K.click(K.slot(0)))
    manager.tick(0.05)
    assert K.shape(K.cells())[:3] == [(TOMATO, 32), (TOMATO, 32), None]
    assert K.do(manager, "a", K.click(K.slot(0)))
    assert manager.sessions["a"].hand["count"] == 32 and K.shape(K.cells())[:2] == [None, (TOMATO, 32)]
    assert K.do(manager, "a", K.click(K.slot(0), kind="PICKUP_ALL"))
    assert manager.sessions["a"].hand["count"] == 64 and K.shape(K.cells())[:2] == [None, None], "双击：两格都收到手上"
    assert K.do(manager, "a", K.click(K.inv(3)))
    assert manager.sessions["a"].hand is None and fake.world.players["a"]["inv"][3]["count"] == 64, "点背包的格子放回去"
    assert K.do(manager, "a", K.click(K.inv(3))) and K.do(manager, "a", K.click(K.slot(0)))
    manager.tick(0.05)
    assert K.do(manager, "a", K.click(K.slot(0), kind="QUICK_MOVE")) and K.do(manager, "a", K.click(K.slot(1), kind="QUICK_MOVE"))
    assert K.shape(K.cells())[:2] == [None, None] and manager.sessions["a"].hand is None
    assert sum(stack["count"] for stack in fake.world.players["a"]["inv"] if stack) == 64, "Shift 点：各自直接进背包"


def testTheServedSlotIsTakeOnlyAndTakingFromItCountsAsServed():
    manager, data = K.setup()
    fake.setContainer(POT, 7, "arris:dumplings", 6)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.slot(0, "served")))
    assert manager.sessions["a"].hand["count"] == 6 and fake.container(POT, 7) is None, "整堆拿到手上"
    assert HandCooking.madeOf("a", "arris:dumplings") == 6, "从产出格取走算盛出，记做过几份"
    assert not K.do(manager, "a", K.click(K.slot(0, "served"))), "只能取，放不回去"


def testScoopingWithTheBowlsInHandTakesOneServingAPieceAndTheLastBowlHoldsTheDish():
    manager, data = K.setup()
    K.setMeal(SAUCE, 3, data)
    K.PotContainer.addUsed(data, SAUCE, 4)
    fake.give("a", 5, BOWL, 3)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(5)))
    fake.world.take()
    assert K.do(manager, "a", K.custom("scoop"))
    assert manager.sessions["a"].hand["count"] == 2 and K.preview()["count"] == 2, "一个动作一份"
    assert fake.count("a", SAUCE) == 1, "菜进背包（碗在手上，背包里有空格）"
    assert HandCooking.madeOf("a", SAUCE) == 1
    assert len(K.orbs()) == 1 and K.orbs()[0] in (1, 2), "经验在第一份时一并给（4 份 x 0.35 = 1.4）：%r" % K.orbs()
    assert K.effects() == [("scooped", {"count": 1})]
    assert K.do(manager, "a", K.custom("scoop", all=True))
    assert K.preview() == {} and fake.count("a", SAUCE) == 2
    assert manager.sessions["a"].hand["newItemName"] == SAUCE, "最后一个碗用完，盛出来的菜顶替手里的东西"
    assert HandCooking.madeOf("a", SAUCE) == 3 and len(K.orbs()) == 1, "以后的盛出不再给经验"


def testScoopingFromTheInventoryUsesTheSelectedSlotFirstAndNeedsAnEmptyHand():
    manager, data = K.setup()
    K.setMeal(SAUCE, 4, data)
    fake.give("a", 2, BOWL, 3)
    fake.give("a", 7, BOWL, 5)
    K.opened(manager)
    fake.world.players["a"]["selected"] = 7
    assert K.do(manager, "a", K.custom("scoop", from_inventory=True))
    assert fake.world.players["a"]["inv"][7]["count"] == 4 and fake.world.players["a"]["inv"][2]["count"] == 3
    assert K.do(manager, "a", K.custom("scoop", from_inventory=True, all=True))
    assert K.preview() == {} and fake.world.players["a"]["inv"][7]["count"] == 1, "选中那格的碗先用：4 份盛完了，用了 4 个"
    assert fake.world.players["a"]["inv"][2]["count"] == 3, "别的格子的碗没动"
    assert fake.count("a", SAUCE) == 4 and HandCooking.madeOf("a", SAUCE) == 4
    K.setMeal(SAUCE, 2, data)
    assert K.do(manager, "a", K.click(K.inv(2)))
    assert K.do(manager, "a", K.custom("scoop", from_inventory=True)) and K.preview()["count"] == 2, "手里拿着东西时不从背包盛"


def testAServingDoesNotGoIntoAContainerThatIsNotItsOwn():
    manager, data = K.setup()
    K.setMeal(SAUCE, 2, data)
    fake.give("a", 0, "minecraft:glass_bottle", 2)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(0)))
    K.do(manager, "a", K.custom("scoop", all=True))
    assert K.preview()["count"] == 2 and manager.sessions["a"].hand["count"] == 2, "番茄酱盛在碗里，不是瓶子里"
    K.setMeal("arris:dumplings", 2, data)
    K.do(manager, "a", K.custom("scoop"))
    assert K.preview()["count"] == 2, "饺子不要容器：由产出格取"


def testTakeBackReturnsTheLastSunkSlotWholeOneAtATime():
    manager, data = K.setup()
    for index, (name, count) in enumerate([("minecraft:milk_bucket", 1), ("minecraft:carrot", 2), ("minecraft:egg", 3),
                                           ("minecraft:sugar", 5)]):
        fake.setContainer(POT, index, name, count)
    payload = K.opened(manager)
    assert payload["state"]["data"]["sunk"] == [0, 2, 3], "牛奶、蛋、糖沉着，胡萝卜浮着"
    assert K.do(manager, "a", K.custom("take_back"))
    assert fake.count("a", "minecraft:sugar") == 5 and fake.container(POT, 3) is None, "最后放进去的先回来"
    assert fake.container(POT, 2)["count"] == 3
    assert K.do(manager, "a", K.custom("take_back"))
    assert fake.count("a", "minecraft:egg") == 3
    assert K.do(manager, "a", K.custom("take_back"))
    assert fake.count("a", "minecraft:milk_bucket") == 1, "奶连桶一起回来"
    K.do(manager, "a", K.custom("take_back"))
    assert fake.container(POT, 1)["count"] == 2 and fake.count("a", "minecraft:carrot") == 0, "浮着的料不走这条路"
    manager.tick(0.05)
    assert fake.world.take("a", Protocol.EP_STATE)[-1][2]["state"]["data"]["sunk"] == []


def testTakeBackSplitsABigStackAndDropsWhatDoesNotFit():
    manager, data = K.setup()
    fake.setContainer(POT, 0, "minecraft:egg", 40)
    for index in range(36):
        fake.give("a", index, "arris:wheat", 64)
    fake.world.players["a"]["inv"][20] = None
    fake.world.players["a"]["inv"][21] = None
    K.opened(manager)
    assert K.do(manager, "a", K.custom("take_back"))
    assert fake.count("a", "minecraft:egg") == 32, "背包里只剩两个空格，一堆蛋最多 16 个"
    assert sum(item["count"] for dim, pos, item in fake.world.dropped) == 8, fake.world.dropped


def testTheBookPutsWholeSetsFromTheInventoryAndLaysThemOut():
    manager, data = K.setup()
    fake.give("a", 9, TOMATO, 20)
    fake.give("a", 10, TOMATO, 20)
    K.opened(manager)
    assert K.do(manager, "a", K.custom("bookFill", key=K.sauceIndex(), sets=16))
    assert K.shape(K.cells())[:3] == [(TOMATO, 16), (TOMATO, 16), None], "32 个番茄放成两格"
    assert fake.count("a", TOMATO) == 8
    assert HandCooking.handOf(0, POT).clock._handFed is True
    assert manager.stations[(0, POT)].logic.wanted == K.sauceIndex(), "书里点的这道成了锅的选择"
    assert K.do(manager, "a", K.custom("bookFill", key=K.sauceIndex(), sets=1))
    assert fake.count("a", TOMATO) == 6 and sum(c["count"] for c in K.cells() if c) == 34
    assert K.shape(K.cells())[:2] == [(TOMATO, 17), (TOMATO, 17)]


def testTheBookTakesOnlyWholeSetsAndNothingWhenThePotHoldsFoodTheDishDoesNotUse():
    manager, data = K.setup()
    fake.give("a", 9, TOMATO, 7)
    K.opened(manager)
    assert K.do(manager, "a", K.custom("bookFill", key=K.sauceIndex(), sets=16))
    assert fake.count("a", TOMATO) == 1 and sum(c["count"] for c in K.cells() if c) == 6, "7 个只够 3 份：放 6 个，剩 1 个"
    manager, data = K.setup()
    fake.give("a", 9, TOMATO, 7)
    fake.setContainer(POT, 0, "arris:onion", 2)
    K.opened(manager)
    K.do(manager, "a", K.custom("bookFill", key=K.sauceIndex(), sets=16))
    assert fake.count("a", TOMATO) == 7 and K.shape(K.cells())[0] == ("arris:onion", 2), "锅里有番茄酱用不上的洋葱：书什么也不放"
    manager, data = K.setup(creative=True)
    fake.give("a", 9, TOMATO, 8)
    K.opened(manager)
    K.do(manager, "a", K.custom("bookFill", key=K.sauceIndex(), sets=16))
    assert fake.count("a", TOMATO) == 0, "创造模式也照扣（HoD 的 fill 不分）"


def testARightClickWithTheContainerServesOneAndRefusesTheStation():
    manager, data = K.setup()
    K.setMeal(SAUCE, 2, data)
    K.PotContainer.addUsed(data, SAUCE, 2)
    fake.give("a", 0, BOWL, 2)
    assert not manager.open("a", list(POT))
    assert fake.world.take("a", Protocol.EP_DENIED)[0][2]["reason"] == "refused" and not manager.sessions and not manager.stations
    assert fake.count("a", BOWL) == 1 and fake.count("a", SAUCE) == 1 and K.preview()["count"] == 1
    assert HandCooking.madeOf("a", SAUCE) == 1 and K.orbs() == [], "右键盛不给经验（FD 也不给）"
    assert [c for c in fake.calls if c[1] == "OnPlaySound"], "有盛菜的声音"
    assert not manager.open("a", list(POT)) and fake.count("a", SAUCE) == 1, "按住右键：冷却里不重复盛，也不开站点"
    for delay, fn, args in list(fake.timers):
        fn(*args)
    assert not manager.open("a", list(POT)) and fake.count("a", SAUCE) == 2 and K.preview() == {}
    for delay, fn, args in list(fake.timers):
        fn(*args)
    assert manager.open("a", list(POT)), "没有菜了：照常开站点"


def testTheStationOpensWhenTheHandHoldsSomethingThatIsNotItsContainer():
    manager, data = K.setup()
    K.setMeal(SAUCE, 2, data)
    fake.give("a", 0, "minecraft:glass_bottle", 2)
    assert manager.open("a", list(POT)) and fake.count("a", SAUCE) == 0
    manager.close("a")
    fake.world.players["a"]["inv"][0] = None
    assert manager.open("a", list(POT)), "空手也开"


def testWhatTheDishDoesNotHoldGoesBackToTheCookOnTheNextTick():
    manager, data = K.setup()
    fake.give("a", 0, TOMATO, 64)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(0)))
    assert K.do(manager, "a", K.click(K.slot(0)))
    fake.container(POT, 0)["count"] = 64
    fake.setContainer(POT, 1, TOMATO, 64)
    fake.setContainer(POT, 2, TOMATO, 10)
    manager.tick(0.05)
    laid = [c["count"] for c in K.cells() if c]
    assert laid == [64, 64] and fake.count("a", TOMATO) == 10, "番茄酱只占两格：多的 10 个退给厨师：%r" % laid


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
