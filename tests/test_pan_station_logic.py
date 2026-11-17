# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点的服务端逻辑（Compat/Diegesis/PanLogic.py + Server/HandFrying.py + Server/PanLook.py + Server/Helpers/PanContents.py），
真的前置包 Manager 配假引擎：照 HoD 的 SkilletLogic / SkilletTests——放（光标栈点锅：左键整叠、右键一个、最多一批、同一种、煎得了的、没泡水）、
托盘里 Shift 点、全拿出来、颠锅（间隔 0.4 秒）、开站时主手的食物整叠放进去、手放的两面分开煎、一面时间随批量和火焰附加、存档、广播。"""
from __future__ import print_function

import panfake as P

fake, HandFrying, PanLook = P.fake, P.HandFrying, P.PanLook
BEEF, PORK, COOKED, EGG, STICK = P.BEEF, P.PORK, P.COOKED, P.EGG, P.STICK


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def carry(manager, playerId, slot, name, count):
    """把背包里一叠东西拿到光标栈上。"""
    P.hold(playerId, slot, name, count)
    assert P.do(manager, playerId, P.click(P.inv(slot)))


def testPlacingTheStackOnTheCursorLaysTheWholeStackIn():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    assert P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 5) and manager.sessions["a"].hand is None, "整叠进锅"
    hand = HandFrying.peek(0, P.PAN)
    assert hand.frying.byHand and hand.cook == "a", "放进来的从此两面分开煎（SkilletCooking.place 的 byHand）"
    assert len(P.events("placed")) == 1 and P.events("placed")[0][1]["pos"] == list(P.PAN), "附近的人都听到放进锅的声音"
    assert data["panFrying"] == {"byHand": True, "down": 0.0, "up": 0.0, "batch": 0}, "存进方块实体，重启接着煎"


def testPlacingOneAtATimeAndMoreOfTheSameKeepsAdding():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    assert P.do(manager, "a", P.custom("place", one=True))
    assert P.inPan() == (BEEF, 1) and manager.sessions["a"].hand["count"] == 4
    assert P.do(manager, "a", P.custom("place", one=True))
    assert P.inPan() == (BEEF, 2)
    assert P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 5) and manager.sessions["a"].hand is None, "同一种接着叠：1 + 1 + 剩下的 3"


def testAtMostABatchOfSixteenGoesIn():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 20)
    assert P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 16) and manager.sessions["a"].hand["count"] == 4, "放满一批，余下的留在手上"
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 16) and manager.sessions["a"].hand["count"] == 4, "满了再放不动"
    assert len(P.events("refused")) == 1, "被拒：那一件落到锅心又弹开，大家都看得见（EFFECT_REFUSED）"


def testEggsStackToSixteenButAnEggStackOfSixteenIsOneBatch():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, EGG, 16)
    assert P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (EGG, 16)


def testOnlyWhatTheCampfireCooksGoesInAndOnlyOneKindAtATime():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 30, STICK, 3)
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() is None and manager.sessions["a"].hand["count"] == 3, "木棍不是食物"
    assert P.events("refused")[-1][1]["stack"] == {"newItemName": STICK, "newAuxValue": 0, "count": 1}
    assert P.do(manager, "a", P.click(P.inv(30)))                    # 放回
    carry(manager, "a", 31, COOKED, 2)
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() is None and manager.sessions["a"].hand["count"] == 2, "煎好的不再煎"
    assert P.do(manager, "a", P.click(P.inv(31)))
    carry(manager, "a", 32, BEEF, 2)
    assert P.do(manager, "a", P.custom("place"))
    carry(manager, "a", 33, PORK, 2)
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 2) and manager.sessions["a"].hand["newItemName"] == PORK, "一种一种来，不换（也不和手上的对调）"


def testAPanSoakedInWaterTakesNothing():
    manager, _ = P.setup()
    P.opened(manager)
    fake.liquid[(0, P.PAN)] = {"name": "minecraft:water"}
    carry(manager, "a", 35, BEEF, 5)
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() is None and manager.sessions["a"].hand["count"] == 5
    fake.liquid.clear()
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 5)


def testShiftClickOnTheTrayLaysTheWholeStackIn():
    manager, _ = P.setup()
    P.opened(manager)
    P.hold("a", 12, "minecraft:chicken", 7)
    assert P.do(manager, "a", P.click(P.inv(12), kind="QUICK_MOVE"))
    assert P.inPan() == ("minecraft:chicken", 7) and fake.world.players["a"]["inv"][12] is None, "Shift 点：JE 的 onInventoryShiftClick"
    assert HandFrying.peek(0, P.PAN).frying.byHand


def testPlacingFromAnInventorySlotLaysThatStackIn():
    """JE 的 onInventoryShiftClick 发 place {"from": 背包格号}：那一格的一叠（最多一批）直接放进锅，不经光标栈。"""
    manager, _ = P.setup()
    P.opened(manager)
    P.hold("a", 12, "minecraft:chicken", 20)
    assert P.do(manager, "a", P.custom("place", **{"from": 12}))
    assert P.inPan() == ("minecraft:chicken", 16) and fake.world.players["a"]["inv"][12]["count"] == 4, "放满一批，余下的留在那一格"
    assert manager.sessions["a"].hand is None, "没经过光标栈"
    assert HandFrying.peek(0, P.PAN).frying.byHand and len(P.events("placed")) == 1
    assert P.do(manager, "a", P.custom("place", **{"from": 12}))
    assert P.inPan() == ("minecraft:chicken", 16) and fake.world.players["a"]["inv"][12]["count"] == 4 and len(P.events("refused")) == 1, "满了：弹回"
    P.hold("a", 13, "minecraft:chicken", 3)
    assert P.do(manager, "a", P.custom("place", one=True, **{"from": 13}))
    assert P.inPan() == ("minecraft:chicken", 16) and fake.world.players["a"]["inv"][13]["count"] == 3


def testPlacingFromASlotThePanWillNotTakeIsRefusedAndABadSlotDoesNothing():
    manager, _ = P.setup()
    P.opened(manager)
    P.hold("a", 12, STICK, 3)
    assert P.do(manager, "a", P.custom("place", **{"from": 12}))
    assert P.inPan() is None and fake.world.players["a"]["inv"][12]["count"] == 3, "木棍不是食物：留在那一格"
    assert P.events("refused")[-1][1]["stack"] == {"newItemName": STICK, "newAuxValue": 0, "count": 1}, "弹开的那一件大家都看得见"
    refused = len(P.events("refused"))
    for bad in (-1, 36, 99, True, "12", 1.5, None):
        assert P.do(manager, "a", P.custom("place", **{"from": bad}))
    assert P.inPan() is None and len(P.events("refused")) == refused, "格号不对（越界、负数、布尔、字符串、小数）：什么也不做"
    assert P.do(manager, "a", P.custom("place", **{"from": 20})) and P.inPan() is None and len(P.events("refused")) == refused, "空格：什么也不做"


def testTheLibraryCannotTakeTheFoodOut():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    P.do(manager, "a", P.custom("place"))
    assert not P.do(manager, "a", P.click(P.pan())), "空手点锅里的东西：库不让拿（要走 take，它会重置两面进度）"
    assert not P.do(manager, "a", P.click(P.pan(), kind="QUICK_MOVE"))
    carry(manager, "a", 34, BEEF, 2)
    assert not P.do(manager, "a", P.click(P.pan())), "光标栈上拿着同一种东西点锅也不行：库的 PICKUP 对非空槽先问 mayTake"
    assert P.do(manager, "a", P.click(P.inv(34), kind="PICKUP_ALL")) in (True, False)
    assert P.inPan() == (BEEF, 5), "双击聚拢不会把锅里的东西收走"


def testTakeBringsEverythingBackToTheInventoryAndStartsOver():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    P.do(manager, "a", P.custom("place"))
    hand = HandFrying.peek(0, P.PAN)
    hand.frying.down, hand.frying.up, hand.frying.batch = 0.5, 0.25, 5
    assert P.do(manager, "a", P.custom("take"))
    assert P.inPan() is None and fake.count("a", BEEF) == 5, "全进背包"
    assert not hand.frying.byHand and (hand.frying.down, hand.frying.up, hand.frying.batch) == (0.0, 0.0, 0), "空锅重新开始"
    assert data["panFrying"] is None and data["cookTimer"] == 7.0
    taken = P.events("taken")
    assert len(taken) == 1 and taken[0][1]["stack"]["newItemName"] == BEEF and taken[0][1]["stack"]["count"] == 5


def testTakeWithAFullInventoryDropsAtTheFeet():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    P.do(manager, "a", P.custom("place"))
    for slot in range(36):
        P.hold("a", slot, "minecraft:stone", 64)
    assert P.do(manager, "a", P.custom("take"))
    assert P.inPan() is None and fake.count("a", BEEF) == 0
    assert [(item["newItemName"], item["count"]) for _, _, item in manager.world.dropped] == [(BEEF, 5)], "放不下的掉在脚下"


def testTakeMergesIntoStacksThatAreThere():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 5)
    P.do(manager, "a", P.custom("place"))
    P.hold("a", 3, BEEF, 60)
    assert P.do(manager, "a", P.custom("take"))
    inv = fake.world.players["a"]["inv"]
    assert inv[3]["count"] == 64 and fake.count("a", BEEF) == 65, "先并入同种没满的栈，再放进空格"


def testTakeWithAnEmptyPanDoesNothing():
    manager, _ = P.setup()
    P.opened(manager)
    assert P.do(manager, "a", P.custom("take")) and P.events("taken") == []


def testATossSwapsTheSidesAndEverybodySeesIt():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    hand = HandFrying.peek(0, P.PAN)
    hand.frying.down, hand.frying.up = 1.0, 0.0
    fake.world.time += 1.0
    assert P.do(manager, "a", P.custom("toss", strength=0.7))
    assert (hand.frying.down, hand.frying.up) == (0.0, 1.0) and hand.tosses == 1
    tossed = P.events("tossed")
    assert len(tossed) == 1 and near(tossed[0][1]["strength"], 0.7), "颠锅谁都看得见（HoD 的 EFFECT_TOSSED）"
    assert data["panFrying"]["up"] == 1.0, "颠完马上存"


def testATossWhileTheLastOneIsStillInTheAirIsNotTaken():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    fake.world.time += 1.0
    P.do(manager, "a", P.custom("toss", strength=0.5))
    fake.world.time += 0.2
    assert P.do(manager, "a", P.custom("toss", strength=0.5))
    assert len(P.events("tossed")) == 1 and len(P.events("untossed")) == 1, "上一颠还在空中：食物照原样躺着（EFFECT_UNTOSSED）"
    fake.world.time += 0.3
    P.do(manager, "a", P.custom("toss", strength=0.5))
    assert len(P.events("tossed")) == 2, "0.4 秒之后可以再颠"


def testNothingToTossOrDoneFoodDoesNotToss():
    manager, _ = P.setup()
    P.opened(manager)
    fake.world.time += 1.0
    P.do(manager, "a", P.custom("toss", strength=0.5))
    assert P.events("tossed") == [] and P.events("untossed") == [], "空锅什么都不发生"
    fake.blockEntities[(0, P.PAN)]["cookingDict"] = {"newItemName": COOKED, "newAuxValue": 0, "count": 2}
    P.do(manager, "a", P.custom("toss", strength=0.5))
    assert P.events("tossed") == [] and len(P.events("untossed")) == 1, "煎好的不能颠（SkilletCooking.turn 要营火配方）"


def testAStrengthFromTheNetworkIsClamped():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    fake.world.time += 1.0
    P.do(manager, "a", P.custom("toss", strength=99.0))
    assert P.events("tossed")[0][1]["strength"] == 1.0
    fake.world.time += 1.0
    P.do(manager, "a", P.custom("toss", strength="hard"))
    assert P.events("tossed")[1][1]["strength"] == 0.5, "不是数就当 0.5"


def testOpeningWithFoodInTheMainHandPutsTheWholeStackIn():
    manager, _ = P.setup()
    P.hold("a", 0, BEEF, 6)
    fake.world.players["a"]["selected"] = 0
    P.opened(manager)
    assert P.inPan() == (BEEF, 6) and fake.world.players["a"]["inv"][0] is None, "右键放料不比不开站点慢"
    assert HandFrying.peek(0, P.PAN).frying.byHand and len(P.events("placed")) == 1


def testComingOverFromANeighbouringStationLeavesTheMainHandAlone():
    """JE 的 SkilletBehavior.onOpen:197-204 先看 view.openedByUse()：从砧板按 A / D 走到煎锅，主手里的生肉不是给这口锅的，不自己进锅。"""
    manager, _ = P.setup()
    P.hold("a", 0, BEEF, 6)
    fake.world.players["a"]["selected"] = 0
    assert manager.open("a", list(P.PAN), False)
    assert P.inPan() is None and fake.world.players["a"]["inv"][0]["count"] == 6 and P.events("placed") == []
    assert manager.stations[(0, P.PAN)].openedByUse("a") is False


def testOpeningWithTooMuchFoodOnlyFillsABatch():
    manager, _ = P.setup()
    P.hold("a", 0, BEEF, 20)
    P.opened(manager)
    assert P.inPan() == (BEEF, 16) and fake.world.players["a"]["inv"][0]["count"] == 4


def testOpeningWithOtherFoodOrAToolLeavesTheHandAlone():
    manager, _ = P.setup()
    fake.blockEntities[(0, P.PAN)]["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 2}
    P.hold("a", 0, PORK, 3)
    P.opened(manager)
    assert P.inPan() == (BEEF, 2) and fake.world.players["a"]["inv"][0]["count"] == 3, "锅里是别的：留在手里不拒绝"
    manager.close("a")
    P.hold("a", 0, STICK, 3)
    P.opened(manager)
    assert fake.world.players["a"]["inv"][0]["count"] == 3


def testOpeningAtAFullPanOrAWetOneLeavesTheHandAlone():
    manager, _ = P.setup()
    fake.blockEntities[(0, P.PAN)]["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 16}
    P.hold("a", 0, BEEF, 3)
    P.opened(manager)
    assert fake.world.players["a"]["inv"][0]["count"] == 3 and P.inPan() == (BEEF, 16)
    manager.close("a")
    fake.blockEntities[(0, P.PAN)]["cookingDict"] = None
    fake.liquid[(0, P.PAN)] = {"name": "minecraft:water"}
    P.opened(manager)
    assert fake.world.players["a"]["inv"][0]["count"] == 3 and P.inPan() is None


def testFoodPlacedAtTheStationFriesOneSideThenWaitsAndTheOtherSideAfterATossFinishes():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    side = P.Rules.sideSeconds(2)
    P.run(manager, side + 0.5)
    hand = HandFrying.peek(0, P.PAN)
    assert hand.frying.down >= 1.0 and hand.frying.up == 0.0 and hand.frying.waits(), "贴锅那面熟了，等着翻"
    P.run(manager, 1.0)
    assert P.inPan() == (BEEF, 2), "没翻，什么都不再发生"
    P.do(manager, "a", P.custom("toss", strength=0.5))
    assert hand.frying.up >= 1.0
    P.run(manager, side + 0.5)
    assert P.inPan() == (COOKED, 2), "两面都熟：一整批成了熟的，留在锅里等人取"
    fried = P.events("fried")
    assert len(fried) == 1 and fried[0][1]["in_pan"] is True and fried[0][1]["stack"]["newItemName"] == COOKED


def testFireAspectOnThePlacedSkilletFriesFaster():
    manager, data = P.setup(fireAspect=2)
    assert PanLook.fireAspectOf(data) == 2 and PanLook.fireAspectOf(None) == 0
    beef = {"newItemName": BEEF, "count": 1}
    assert near(PanLook.rateOf(beef, _frying(), True, 0), 0.5) and near(PanLook.rateOf(beef, _frying(), True, 2), 1.0), "一件一面 2 秒 / 火焰附加 II 1 秒"
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    assert near(P.looks()[-1]["rate"], 1.0), "站点广播的速度按方块里那件煎锅的火焰附加算"
    P.run(manager, 1.25)
    assert HandFrying.peek(0, P.PAN).frying.down >= 1.0, "II 级：1 秒一面"


def _frying():
    frying = P.HandFrying.Frying.Frying()
    frying.layByHand()
    frying.resize(1)
    return frying


def testASavedPanKeepsFryingAfterARestart():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    P.run(manager, 1.0)
    saved = data["panFrying"]
    assert saved["byHand"] and 0.2 < saved["down"] < 0.5 and saved["batch"] == 2
    HandFrying._hands.clear()
    reloaded = HandFrying.handOf(0, P.PAN, data)
    assert reloaded.frying.byHand and near(reloaded.frying.down, saved["down"]) and reloaded.frying.batch == 2, "读回来接着煎"


def testFarmersDelightsOwnRightClickAfterARestartDropsTheOldSave():
    manager, data = P.setup()
    data["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 2}
    data["panFrying"] = {"byHand": True, "down": 0.5, "up": 0.0, "batch": 2}
    HandFrying.byFarmersDelight(0, P.PAN, data)                 # 重启后还没人读过存档，玩家用 FD 原样的右键把牛肉取走再放别的
    assert data["panFrying"] is None, "存档作废：这锅归 FD 了"
    data["cookingDict"] = {"newItemName": PORK, "newAuxValue": 0, "count": 1}
    hand = HandFrying.handOf(0, P.PAN, data)
    assert not hand.frying.byHand and hand.frying.down == 0.0, "之后读不回旧的进度"


def testAnEmptiedPanForgetsItsProgress():
    manager, data = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    hand = HandFrying.peek(0, P.PAN)
    data["cookingDict"] = None                       # 被水冲走、被漏斗吸走
    P.step()
    assert not hand.frying.byHand and data["panFrying"] is None


def testTheLookIsBroadcastWhenSomethingChangesAndEveryKeyframeWhileFrying():
    manager, _ = P.setup()
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    first = P.looks()[-1]
    assert first["item"] == {"newItemName": BEEF, "newAuxValue": 0, "count": 2} and first["byHand"] and first["heated"]
    assert near(first["rate"], 1.0 / 2.85, 1e-4), "两块牛肉一面 57 刻 = 2.85 秒"
    assert first["both"] is False and first["pos"] == list(P.PAN)
    P.step(0.25, now=fake.world.time + 0.1)           # 第一步：批量定下来了（0 -> 2），算一次变化
    sent = len(P.looks())
    P.step(0.25, now=fake.world.time + 0.3)
    assert len(P.looks()) == sent, "没变、没到一秒：不重发"
    P.step(0.25, now=fake.world.time + 1.5)
    assert len(P.looks()) == sent + 1, "熟度在走：每秒补一次关键帧"


def testTheBroadcastGoesOnlyToPlayersWithin32Blocks():
    manager, _ = P.setup()
    fake.addPlayer("far", (10.5, 64.0, 80.5))
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    players = P.events("placed")[0][2]
    assert "a" in players and "b" in players and "far" not in players


def testAPlayerWhoWalksIntoRangeGetsTheCurrentLookOnceAndNobodyElseDoes():
    """JE 的状态在方块实体里，走近就对；广播只发给"发的那一刻在 32 格内的人"，走进来的人要补一份，不然等翻 / 煎好留在锅里这类不再变的状态永远是旧的。"""
    manager, _ = P.setup(heated=False)
    fake.addPlayer("far", (10.5, 64.0, 80.5))
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    P.step(0.25, now=fake.world.time + 1.0)
    for payload, players in P._grouped():
        assert "far" not in players, "还在 32 格外：什么也收不到"
    before = len(P.looks())
    fake.world.players["far"]["pos"] = (10.5, 64.0, 20.5)           # 走进来了
    P.step(0.25, now=fake.world.time + 2.0)
    arrivals = [(payload, players) for payload, players in P._grouped() if "far" in players]
    assert len(arrivals) == 1 and arrivals[0][1] == ["far"], "只单发给他一份，a 和 b 不重复收"
    assert arrivals[0][0]["item"] == {"newItemName": BEEF, "newAuxValue": 0, "count": 2} and arrivals[0][0]["byHand"], "是锅现在的样子"
    assert len(P.looks()) == before + 1
    P.step(0.25, now=fake.world.time + 3.0)
    assert len(P.looks()) == before + 1, "他已经有了：没变就不再发"


def testAPlayerWhoLeavesAndComesBackGetsAnotherCopy():
    manager, _ = P.setup(heated=False)
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    P.step(0.25, now=fake.world.time + 1.0)
    fake.world.players["b"]["pos"] = (10.5, 64.0, 90.5)             # b 走远了
    P.step(0.25, now=fake.world.time + 2.0)
    P.do(manager, "a", P.custom("take"))                              # 锅里的东西被取走（b 没收到）
    fake.world.players["b"]["pos"] = (12.5, 64.0, 10.5)             # b 回来
    mark = len(fake.calls)
    P.step(0.25, now=fake.world.time + 3.0)
    got = [m for m in fake.calls[mark:] if m[0] == "b" and m[1] == PanLook.ENDPOINT]
    assert len(got) == 1 and got[0][2][0]["item"] == {}, "回来的人补到的是现在的样子：锅里空了"


def testTheBroadcastIsOffWithoutThePrerequisite():
    manager, _ = P.setup()
    PanLook.enable(False)
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 1)
    P.do(manager, "a", P.custom("place"))
    assert P.inPan() == (BEEF, 1) and not [m for m in fake.calls if m[1] == PanLook.ENDPOINT]


def testAnEggFriesThroughSoBothSidesAdvanceTogetherAndTheRateIsHalf():
    frying = P.HandFrying.Frying.Frying()
    frying.layByHand()
    frying.resize(1)
    rate = PanLook.rateOf({"newItemName": EGG, "count": 1}, frying, True, 0)
    assert near(rate, 0.25), "蛋：一面 2 秒，从下往上煎透要两面的时间，每秒 0.5 / 2"


def testNoRateWhileColdWaitingOrDone():
    frying = _frying()
    beef = {"newItemName": BEEF, "count": 1}
    assert PanLook.rateOf(beef, frying, False, 0) == 0.0, "没火不走"
    frying.down = 1.0
    assert PanLook.rateOf(beef, frying, True, 0) == 0.0, "贴锅面熟了等翻面：不走"
    assert PanLook.rateOf({"newItemName": COOKED, "count": 1}, frying, True, 0) == 0.0
    assert PanLook.rateOf(None, frying, True, 0) == 0.0
    plainPan = P.HandFrying.Frying.Frying()
    assert PanLook.rateOf(beef, plainPan, True, 0) == 0.0, "FD 原样煎的没有两面进度"


def testTheSecondPlayerSeesTheSameSlotAndNothingDuplicates():
    manager, _ = P.setup()
    P.opened(manager, "a")
    P.opened(manager, "b")
    carry(manager, "a", 35, BEEF, 3)
    P.do(manager, "a", P.custom("place"))
    manager.tick(0.05)
    assert P.inPan() == (BEEF, 3)
    updates = [s for s in fake.world.sent if s[0] == "b" and s[1] == P.Protocol.EP_STATE]
    assert updates, "另一位使用者的状态镜像跟着变（pan 槽组绑在方块上）"


def testTheInGameSelfTestRunsCleanAgainstTheFakeEngine():
    """Server/Debug/McdkPanStationTest 是给游戏里的 execute_code 用的；这里用同一套假引擎把它整条跑一遍，至少代码本身没有拼写错误、
    每一步的预期和离线的行为一致（真引擎里的方块实体、背包、广播还要进游戏跑）。"""
    manager, _ = P.setup()
    P.exposeManager(manager)
    fake.world.players["a"]["pos"] = (10.5, 64.0, 8.5)
    selftest = P.potfake.load("Server.Debug.McdkPanStationTest")
    selftest.time = P.potfake.Clock(fake.world)
    result = selftest.mcdk_test_pan_station()
    assert result["ok"], result
    assert result["checks"]["library_cannot_take"] and result["checks"]["tossed_once"] and result["checks"]["taken"] and result["checks"]["save_shape"]


def testTheSelfTestSkipsWithoutThePrerequisite():
    manager, _ = P.setup()
    import sys
    engine = sys.modules[P.potfake.PACKAGE + ".Server.Helpers.Engine"]
    engine.serverApi.ImportModule = lambda name: None
    selftest = P.potfake.load("Server.Debug.McdkPanStationTest")
    assert selftest.mcdk_test_pan_station() == {"case": "pan_station", "ok": True, "skipped": "diegesis not installed or no player"}


def testALookTheClientNeverGotIsSentAgainEveryRefreshSecondsEvenWhenNothingChanges():
    """广播发出去就不管有没有收到（客户端脚本还没就绪、区块还没加载好时整份丢掉），等翻面 / 煎好留在锅里 / 没热源这些状态又不再变：
    原来丢了就永远补不上。现在样子没变时每隔 REFRESH_SECONDS 秒再单发一份（熟度在走时本来就每秒补一次关键帧，这里用没热源的锅）。"""
    manager, _ = P.setup(heated=False)
    P.opened(manager)
    carry(manager, "a", 35, BEEF, 2)
    P.do(manager, "a", P.custom("place"))
    base = fake.world.time
    P.step(0.25, now=base + 1.0)
    del fake.calls[:]                                               # 客户端没收到：服务端不知道
    P.step(0.25, now=base + 3.0)
    assert P.looks() == [], "还没到 5 秒"
    P.step(0.25, now=base + 7.0)
    again = [(payload, players) for payload, players in P._grouped() if not payload.get("event")]
    assert len(again) == 1 and sorted(again[0][1]) == ["a", "b"], "隔了 5 秒又发了一份"
    assert again[0][0]["item"] == {"newItemName": BEEF, "newAuxValue": 0, "count": 2} and again[0][0]["byHand"], "是锅现在的样子"
    del fake.calls[:]
    P.step(0.25, now=base + 13.0)
    assert P.looks() == [], "补过一次：下一份要隔 10 秒（间隔逐次加倍）"
    P.step(0.25, now=base + 17.5)
    assert len(P.looks()) == 1, "隔够 10 秒：第二份"


def testOpeningTheStationSendsTheOpenerTheCurrentLookAtOnce():
    """开站的人的客户端可能先前丢了锅的样子：开站那一刻单发给他一份，别人不重复收。"""
    manager, data = P.setup(heated=False, refresh=None)
    data["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 2}
    P.step(0.25)                                                    # a 和 b 都已经收到了
    del fake.calls[:]
    P.opened(manager)
    groups = [(payload, players) for payload, players in P._grouped() if not payload.get("event")]
    assert len(groups) == 1 and groups[0][1] == ["a"] and groups[0][0]["item"]["newItemName"] == BEEF, "只单发给开站的人"


def testNothingIsResentOnOpenWithoutThePrerequisiteSwitch():
    manager, data = P.setup(heated=False)
    P.PanLook.enable(False)
    P.opened(manager)
    P.step(0.25, now=fake.world.time + 20.0)
    assert not [call for call in fake.calls if call[1] == P.PanLook.ENDPOINT]


if __name__ == "__main__":
    raise SystemExit(P.dgtest.run(globals()))
