# -*- coding: utf-8 -*-
# runner: both
"""一口煎锅在客户端的样子（Shared/Rules/HandsOn/PanShow.py 和它用的 PanLand / PanToss / PanHeat / PanOil / PanEffects）：
断言照 Hands-On Delight 的 SkilletBehavior——食物怎么落进来、一批一起来、颠锅时的时间线（0.07 秒一拽、0.032 秒起各块飞、0.262 秒换面）、
等着翻面时的油噗和锅柄描边、煎着时滋滋声随熟度变响、熟了一鼓一鼓、取走时抬起缩没、蛋在锅沿敲开。随机数固定成 0.5。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.PanStation")
Show = fdtest.load("Shared.Rules.HandsOn.PanShow")
Layout = fdtest.load("Shared.Rules.HandsOn.PanLayout")
Land = fdtest.load("Shared.Rules.HandsOn.PanLand")
Toss = fdtest.load("Shared.Rules.HandsOn.PanToss")
BEEF, COOKED, EGG, FRIED = "minecraft:beef", "minecraft:cooked_beef", "minecraft:egg", "arris:fried_egg"
DT = 1.0 / 120.0


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def item(name, count):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def make(heated=True, offset=(0.0, 0.0), focused=False):
    calls = []

    def fromPlayer(height, index, count):
        calls.append((height, index, count))
        return offset(index) if callable(offset) else offset

    show = Show.PanShow(Rules, lambda: 0.5, fromPlayer)
    show.focused = focused
    show.calls, show.wasHeated = calls, heated
    return show


def apply(show, name, count, down=0.0, up=0.0, byHand=True, heated=None):
    show.apply(item(name, count) if name else None, byHand, show.wasHeated if heated is None else heated, down, up)


def run(show, seconds, dt=DT):
    events = []
    for _ in range(int(round(seconds / dt))):
        show.frame(dt)
        events += show.drain()
    return events


def kinds(events, **match):
    return [e for e in events if all(e.get(key) == value for key, value in match.items())]


def testTheFirstStateIsDrawnWithoutLandingAnything():
    show = make()
    apply(show, BEEF, 2)
    piece = show.nodes["piece_0"]
    assert piece.visible and piece.item["newItemName"] == BEEF and piece.item["count"] == 1 and near(piece.size, 7.5)
    assert piece.pos == (2.6, 1.01, 0.4), "node 在锅里 (0, 1.01, 0)，加上摆的位置"
    assert near(piece.rot[1], Layout.yaw(0, False))
    assert show.nodes["piece_1"].visible and not show.nodes["piece_2"].visible and not show.nodes["under_0"].visible
    assert not show.landings.landing(0, False) and show.drain() == [], "刚看到这口锅：东西本来就在，不落、不出声"


def testBatchOfSixteenDrawsEightPiecesWithFourUnderTheTopOnes():
    show = make()
    apply(show, BEEF, 16)
    assert [show.nodes["piece_%d" % i].visible for i in range(4)] == [True] * 4
    assert [show.nodes["under_%d" % i].visible for i in range(4)] == [True] * 4
    assert near(show.nodes["piece_0"].pos[1], 1.01 + 0.6), "垫了东西，上面的抬 0.6"
    assert near(show.nodes["under_0"].pos[1], 1.01) and near(show.nodes["piece_0"].size, 6.5)


def testNewFoodDropsInWhileWhatWasThereStays():
    show = make()
    apply(show, BEEF, 1)
    apply(show, BEEF, 2)
    first, second = show.nodes["piece_0"], show.nodes["piece_1"]
    assert show.landings.landing(1, False) and not show.landings.landing(0, False)
    assert second.visible and near(second.pos[1], 1.01 + Land.LAND_FROM), "从 4 像素高处下来"
    run(show, 0.1)
    start, end = Land.LAND_FROM, 0.0
    assert near(second.pos[1], 1.01 + start + (end - start) * 0.5 + 0.8, 1e-3), "过半时：直线一半 + 跳 0.8"
    run(show, 0.15)
    assert not show.landings.landing(1, False)
    assert near(second.pos[0], -2.6) and near(second.pos[2], -0.4) and near(second.pos[1], 1.01)
    assert near(first.pos[0], 2.6, 1e-3), "原来那块挪到两块的新位置（滑 0.16 秒）"


def testFoodFallingIntoAHotPanHitsTheFatAndAColdOneDoesNot():
    hot = make(heated=True)
    apply(hot, BEEF, 1)
    apply(hot, BEEF, 2)
    events = run(hot, 0.4)
    assert len(kinds(events, type="particle", style="oil_pop")) >= 12, "12 个油泡（再加上锅一直在冒的）"
    assert len(kinds(events, type="particle", style="fat")) >= 6
    steam = kinds(events, type="particle", style="steam", count=3)
    assert steam and steam[0]["color"] == 0x50FFFFFF
    cold = make(heated=False)
    apply(cold, BEEF, 1)
    apply(cold, BEEF, 2)
    assert kinds(run(cold, 0.4), type="particle", style="oil_pop") == []


def testSeveralPiecesComeFromThePlayerOneAfterTheOther():
    show = make(offset=lambda index: (float(index), -float(index)))
    apply(show, BEEF, 1)
    apply(show, BEEF, 4)
    assert show.calls == [(4.0, 0, 3), (4.0, 1, 3), (4.0, 2, 3)], "几块一起来：问玩家屏幕底边的起点"
    assert show.landings.landing(1, False) and not show.nodes["piece_2"].visible and not show.nodes["piece_3"].visible
    assert near(show.nodes["piece_1"].pos[0], Layout.place(1, 4)[0] + 0.0), "第一块从自己那一点（偏移 0）起"
    run(show, 0.15)
    assert show.nodes["piece_2"].visible and show.landings.landing(2, False), "晚 0.14 秒"
    assert near(show.nodes["piece_2"].pos[0], Layout.place(2, 4)[0] + 1.0, 2.0), "从偏移 (1, -1) 的地方起飞"
    run(show, 0.6)
    assert all(not show.landings.landing(i, False) for i in range(4))
    assert near(show.landings.time[1], Land.PLAYER_LAND_TIME) and near(show.landings.hop[1], 2.0)


def testATossShakesThePanThenFlipsEachPiece():
    show = make()
    apply(show, BEEF, 2, down=1.0, up=0.0)
    assert show.toss(1.0) is True
    assert show.takeActions() == [("toss", {"strength": 1.0})]
    pan = show.nodes["pan"]
    events = run(show, 0.07)
    assert near(pan.rot[0], 11.0, 0.5) and near(pan.pos[1], 1.2, 0.1) and near(pan.pos[2] - 8.0, 0.9, 0.1), "0.07 秒转 11 度、抬 1.2、拽 0.9"
    assert kinds(events, type="sound", name="lantern_step") == [{"type": "sound", "name": "lantern_step", "volume": 0.35, "pitch": 1.0}]
    events += run(show, 0.2)
    assert near(pan.rot[0], 0.0, 0.2) and near(pan.pos[1], 0.0, 0.1), "0.2 秒落回原位"
    assert show.tossing() is True


def testAPieceTurnsOverInTheAirAndTheOtherSideShowsAtTheEdgeOnMoment():
    show = make()
    apply(show, BEEF, 2, down=1.0, up=0.0)
    piece = show.nodes["piece_0"]
    assert piece.item["newItemName"] == BEEF
    show.toss(1.0)
    run(show, 0.2)
    assert piece.item["newItemName"] == BEEF and piece.rot[0] > 20.0, "还在翻上去，生的那面"
    run(show, 0.1)
    assert piece.item["newItemName"] == COOKED, "约 0.262 秒（0.042 + 飞行的一半 0.22，按帧取整）转到边朝镜头：换成熟的那面"
    assert piece.rot[0] < 0.0, "之后从 -90 度转回 0"
    run(show, 0.3)
    assert near(piece.pos[1], 1.01, 0.01) and near(piece.rot[0], 0.0, 0.5), "落回原位"
    assert near(show.shownUp, 1.0)


def testTossHeightGrowsWithStrength():
    soft, hard = make(), make()
    for show, strength in ((soft, 0.0), (hard, 1.0)):
        apply(show, BEEF, 1, down=1.0)
        show.toss(strength)
        run(show, 0.1)
    top = {}
    for name, show in (("soft", soft), ("hard", hard)):
        best = 0.0
        for _ in range(int(0.5 / DT)):
            show.frame(DT)
            best = max(best, show.nodes["piece_0"].pos[1])
        top[name] = best
    assert top["hard"] > top["soft"] + 3.0, top      # 4.5 对 10.5 像素的抬高，随机 0.85 + 0.3 * 0.5 = 1


def testFoodComesDownWithASizzleAndSpatter():
    show = make()
    apply(show, BEEF, 1, down=1.0)
    show.toss(0.0)
    events = run(show, 0.6)
    drop = kinds(events, type="sound", name="add_food")
    assert len(drop) == 1 and near(drop[0]["volume"], 0.55) and near(drop[0]["pitch"], 0.95 + 0.5 * 0.15)
    assert len(kinds(events, type="particle", style="fat")) >= 10 and len(kinds(events, type="particle", style="oil_pop")) >= 8


def testTheLastTossMustLandBeforeTheNext():
    show = make()
    apply(show, BEEF, 1, down=1.0)
    assert show.toss(0.5) is True
    run(show, 0.3)
    assert show.toss(0.5) is False, "0.42 秒内不再颠"
    run(show, 0.15)
    assert show.toss(0.5) is True
    assert len(show.takeActions()) == 2
    empty = make()
    assert empty.toss(0.5) is False and empty.takeActions() == [], "锅里没东西不颠"


def testAServerTossIsShownToEverybodyButTheCooksOwnIsNotPlayedTwice():
    watcher = make(focused=False)
    apply(watcher, BEEF, 1, down=1.0)
    watcher.effect("tossed", {"strength": 0.5})
    assert watcher.tossing() and watcher.takeActions() == [], "旁人：照服务端的话演，不再发动作"
    cook = make(focused=True)
    apply(cook, BEEF, 1, down=1.0)
    cook.toss(0.5)
    run(cook, 0.2)
    at = cook.tossedAt
    cook.effect("tossed", {"strength": 0.5})
    assert cook.tossedAt == at, "本人刚颠过：服务端回来的这一条不再演第二遍"
    run(cook, 0.6)
    cook.effect("tossed", {"strength": 0.5})
    assert cook.tossedAt > at, "过了 0.6 秒的是别的颠"


def testARefusedTossTurnsTheLookBack():
    show = make()
    apply(show, BEEF, 1, down=1.0, up=0.0)
    show.toss(0.5)
    run(show, 0.4)
    assert show.nodes["piece_0"].item["newItemName"] == COOKED
    show.effect("untossed", {})
    assert show.nodes["piece_0"].item["newItemName"] == BEEF, "服务端没认这一颠：食物照原来的样子躺着"


def testTheServerWordOverridesWhatTheCookPredicted():
    show = make()
    apply(show, BEEF, 1, down=1.0, up=0.0)
    show.toss(0.5)
    run(show, 0.4)
    apply(show, BEEF, 1, down=0.0, up=1.0)           # 服务端：颠过了，新朝上的那面是熟的
    assert show.tossedUp is None and show.nodes["piece_0"].item["newItemName"] == COOKED


def testWhenTheSideOnThePanIsDoneThePanPopsAndTheHandleStaysOutlined():
    show = make(focused=True)
    apply(show, BEEF, 2, down=1.0, up=0.0)
    events = run(show, 0.2)
    pops = kinds(events, type="sound", name="lava_pop")
    assert [(e["volume"], e["pitch"]) for e in pops[:2]] == [(0.4, 1.3), (0.35, 1.55)], "噗两声（隔 0.09 秒）"
    assert len(kinds(events, type="particle", style="fat")) >= 8, "一把油星"
    assert show.waitOutline and show.handleOutlined(False), "本人在锅边、食物等着翻：锅柄描边"
    assert show.handleOutlined(True)
    show.focused = False
    assert not show.handleOutlined(False) and show.handleOutlined(True), "旁人只在光标放上去时描"


def testWhileItWaitsTheSmokeAndTheSharpSizzleGoOn():
    show = make()
    apply(show, BEEF, 2, down=1.0, up=0.0)
    events = run(show, 3.0)
    assert len(kinds(events, type="particle", style="pan_smoke")) >= 10, "每秒 6 * 0.75 = 4.5 缕"
    sizzle = kinds(events, type="sound", name="sizzle")
    assert sizzle and near(sizzle[0]["volume"], 0.3) and near(sizzle[0]["pitch"], 1.15 + 0.5 * 0.1)
    assert kinds(events, type="particle", style="steam", color=0x40FFFFFF) == [], "等翻面时不淌水汽"


def testSizzleGrowsLouderAndHigherAsTheSideBrowns():
    low, high = make(), make()
    apply(low, BEEF, 1, down=0.0)
    apply(high, BEEF, 1, down=0.9)
    a, b = kinds(run(low, 0.1), type="sound", name="sizzle")[0], kinds(run(high, 0.1), type="sound", name="sizzle")[0]
    assert near(a["volume"], 0.12) and near(b["volume"], 0.12 + 0.28 * 0.9)
    assert b["pitch"] > a["pitch"] and near(b["pitch"], 0.85 + 0.3 * 0.9 + 0.025)
    assert len(kinds(run(low, 3.0), type="sound", name="sizzle")) == 3, "一秒一回（越熟越密）"
    assert kinds(run(low, 3.0), type="sound", name="lava_pop") == [], "还在煎：不噗"


def testAColdPanSaysNothingAndAnEmptyHotOneShimmersMore():
    cold = make(heated=False)
    apply(cold, BEEF, 2, down=1.0)
    assert run(cold, 3.0) == []
    empty, full = make(), make()
    apply(empty, None, 0)
    apply(full, BEEF, 1, down=0.0)
    emptyHeat = len(kinds(run(empty, 5.0), type="particle", style="heat"))
    fullHeat = len(kinds(run(full, 5.0), type="particle", style="heat"))
    assert emptyHeat in (11, 12) and fullHeat in (5, 6), (emptyHeat, fullHeat)


def testNoSeethingWhileTheFoodIsInTheAir():
    show = make()
    apply(show, BEEF, 4, down=0.0)
    show.toss(0.5)
    during = kinds(run(show, 0.45), type="particle", style="oil_pop")
    assert len(during) <= 9, "在空中时不冒油泡（只有落地那 8 个）"


def testDoneFoodGlowsInStepAndGivesNoSound():
    show = make()
    apply(show, COOKED, 2)
    assert show.isShownDone()
    events = run(show, 1.3)
    scales = []
    for _ in range(int(1.3 / DT)):
        show.frame(DT)
        scales.append(show.nodes["piece_0"].scale)
        events += show.drain()
    assert max(scales) < 1.0501 and max(scales) > 1.04 and min(scales) < 1.003, "一鼓一鼓：1 + 0.05 * (0.5 - 0.5 cos)"
    assert kinds(events, type="sound") == [], "熟了不出声（噗是翻我）"
    glints = kinds(events, type="particle", style="glint")
    assert glints and all(e["count"] == 1 and e["color"] == 0xFFFFE9A0 for e in glints) and len(glints) % 2 == 0, "每鼓到最大闪两颗"
    assert kinds(events, type="particle", style="pan_smoke") == [] and kinds(events, type="particle", style="fat") == []


def testTheGlowEndsWhenTheFoodIsTaken():
    show = make()
    apply(show, COOKED, 1)
    run(show, 0.7)
    assert show.nodes["piece_0"].scale > 1.0
    apply(show, BEEF, 1)
    run(show, 0.05)
    assert near(show.nodes["piece_0"].scale, 1.0)


def testOilRunsOutWhileFryingAndDriesOffAfterwards():
    show = make()
    apply(show, BEEF, 2, down=0.0)
    run(show, 1.25)
    assert near(show.oil.amount, 0.5, 0.01)
    puddles = show.oil.puddles()
    assert len(puddles) == 2 and puddles[0]["x"] == 2.6 and puddles[1]["turn"] == 1
    run(show, 2.0)
    assert show.oil.amount == 1.0
    apply(show, None, 0)
    run(show, 0.75)
    assert near(show.oil.amount, 0.5, 0.01), "空了：1.5 秒收干"
    run(show, 1.0)
    assert show.oil.amount == 0.0 and show.oil.puddles() == []


def testTakingTheFoodLiftsEveryPieceAndMeltsItAway():
    show = make()
    apply(show, BEEF, 2)
    show.effect("taken", {"stack": item(BEEF, 2)})
    assert [show.nodes["lift_%d" % i].visible for i in range(4)] == [True, True, False, False], "每块一个替身"
    assert not show.nodes["piece_0"].visible and show.shownPieces == 0, "真的那几块马上藏起来"
    events = kinds(run(show, 0.05), type="sound", name="item_pickup")
    assert events == [{"type": "sound", "name": "item_pickup", "volume": 0.3, "pitch": 1.5}]
    run(show, 0.15)
    lifted = show.nodes["lift_0"]
    assert 0.0 < lifted.scale < 1.0 and lifted.pos[1] > 1.01, "抬起来一边缩小"
    run(show, 0.15)
    assert not show.nodes["lift_0"].visible and not show.nodes["lift_1"].visible, "0.3 秒后缩没、藏起来"
    assert show.nodes["lift_0"].scale == 0.0


def testFriedFoodThatLeavesTheCookIsThrownOutOverTheSide():
    show = make()
    apply(show, BEEF, 1)
    show.effect("fried", {"stack": item(COOKED, 1), "to_cook": False})
    run(show, 0.31)
    assert show.nodes["lift_0"].pos[0] >= Land.AWAY_Z - 0.1, "抛向锅右边（+12 像素）"


def testBatchDoneInThePanGivesPuffAndCrackleAndKeepsTheFood():
    show = make()
    apply(show, COOKED, 2)
    show.effect("fried", {"stack": item(COOKED, 2), "in_pan": True})
    events = show.drain()
    assert kinds(events, type="particle", style="steam", count=4) and kinds(events, type="particle", style="glint", count=4)
    assert kinds(events, type="sound", name="add_food") == [{"type": "sound", "name": "add_food", "volume": 0.4, "pitch": 0.75}]
    assert show.nodes["piece_0"].visible, "留在锅里等人取"
    crackle = kinds(run(show, 0.4), type="sound", name="campfire_crackle")
    assert len(crackle) == 1 and crackle[0]["volume"] == 0.6, "0.35 秒后噼啪一声"


def testPlacingAndRefusingSoundsFollowThePan():
    hot, cold = make(heated=True), make(heated=False)
    apply(hot, None, 0)
    apply(cold, None, 0)
    hot.effect("placed", {})
    cold.effect("placed", {})
    names = lambda show: [(e["name"], e["volume"]) for e in show.drain()]
    assert names(hot) == [("add_food", 0.8), ("lantern_place", 0.5)] and names(cold) == [("lantern_place", 0.5)]
    hot.effect("refused", {"stack": item(BEEF, 3)})
    ghost = hot.nodes["lift_0"]
    assert ghost.visible and ghost.item["newItemName"] == BEEF and near(ghost.pos[1], 1.01 + Land.LAND_FROM + 2.0)
    assert names(hot) == [("lantern_hit", 0.4)]
    run(hot, 0.4)
    assert not ghost.visible, "落到锅心又弹开，0.31 秒后藏起来"


def testClickingTheFoodTossesTakesOrDoesNothing():
    show = make()
    show.clickFood(0)
    assert show.takeActions() == []
    apply(show, BEEF, 1, down=0.0)
    show.clickFood(0)
    assert show.takeActions() == [("toss", {"strength": 0.4})]
    run(show, 0.5)
    show.clickFood(1)
    assert show.takeActions() == [("take", {})], "右键：把生的、半熟的也拿回来，重来"
    done = make()
    apply(done, COOKED, 1)
    done.clickFood(0)
    assert done.takeActions() == [("take", {})], "熟了：左键也是拿出来"


def testHoldingTheHandleLiftsThePanAndAFlickTosses():
    show = make(focused=True)
    apply(show, BEEF, 2, down=1.0)
    show.strokeStart(0.0)
    run(show, 0.1)
    pan = show.nodes["pan"]
    assert near(pan.pos[1], 0.5, 0.02) and near(pan.pos[2], 8.3, 0.02), "抓着锅柄：锅拎起来 (0, 0.5, 0.3)"
    show.frame(DT)
    show.strokeMove(0.0)
    show.frame(DT)
    show.strokeMove(1.0)                                    # 一帧 1 像素 = 120 像素每秒
    assert show.takeActions() == [("toss", {"strength": 1.0})]
    show.strokeEnd()
    run(show, 0.4)
    assert near(pan.pos[1], 0.0, 0.1), "颠过之后锅自己落回，松手不再补"


def testReleasingWithoutATossSetsThePanDown():
    show = make(focused=True)
    apply(show, BEEF, 1)
    show.strokeStart(0.0)
    run(show, 0.5)
    show.strokeEnd()
    run(show, 0.2)
    assert near(show.nodes["pan"].pos[1], 0.0, 0.01) and show.takeActions() == []
    show.strokeStart(0.0)
    run(show, 0.1)
    show.close()
    run(show, 0.2)
    assert near(show.nodes["pan"].pos[1], 0.0, 0.01), "走开时锅放回原位"


def testEggsAreCrackedOnTheRimAndTheInsideDropsIn():
    show = make(heated=True)
    apply(show, EGG, 1)
    assert show.nodes["piece_0"].item["newItemName"] == FRIED, "蛋从不连壳躺着：画煎蛋"
    apply(show, EGG, 2)
    egg, inside, piece = show.nodes["hand_1"], show.nodes["spill_1"], show.nodes["piece_1"]
    assert show.cracking[1] is not None and not piece.visible and show.waitingIn[1], "新来的蛋先不露出那一块，一只手拿着敲"
    assert egg.item["newItemName"] == EGG and egg.item["count"] == 1 and inside.item["newItemName"] == FRIED
    events = run(show, 0.7)
    assert egg.visible and kinds(events, type="sound", name="egg_crack"), "磕在锅沿：脆响"
    assert kinds(events, type="particle", style="dust"), "蛋壳碎屑"
    events += run(show, 0.5)
    assert not egg.visible and not inside.visible and show.cracking[1] is None
    assert piece.visible and not show.waitingIn[1], "蛋液落稳了才露出那一块"
    assert near(piece.pos[0], -2.6) and near(piece.pos[2], -0.4)
    assert kinds(events, type="particle", style="oil_pop"), "落进热锅：油泡"


def testEggRimAndStartFollowTheCursorOnlyForTheCook():
    show = make(focused=True)
    show.cursorOn = lambda height: (9.0, height, 5.0)
    apply(show, EGG, 1)
    apply(show, EGG, 2)
    assert near(show.cracking[1].crack.start[0], 9.0) and near(show.cracking[1].crack.start[1], Layout.FLOOR + Land.CRACK_FROM)
    other = make(focused=False)
    other.cursorOn = lambda height: (9.0, height, 5.0)
    apply(other, EGG, 1)
    apply(other, EGG, 2)
    at = Layout.place(1, 2)
    assert near(other.cracking[1].crack.start[0], 8.0 + at[0]) and near(other.cracking[1].crack.start[1], Layout.FLOOR + Land.CRACK_FROM + 2.0)
    assert near(other.cracking[1].crack.rim[0], 8.0 + Land.RIM_OUT) and near(other.cracking[1].crack.rim[2], 8.0 + at[1] * 0.5)


def testStateArrivingBeforeTheTakenEffectStillShowsEveryPiece():
    show = make()
    apply(show, BEEF, 3)
    apply(show, None, 0)                       # 状态先到：锅空了
    show.effect("taken", {"stack": item(BEEF, 3)})
    assert [show.nodes["lift_%d" % i].visible for i in range(3)] == [True, True, True], "按走的那叠数块数，不是按已经画空的锅"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
