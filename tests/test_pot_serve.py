# -*- coding: utf-8 -*-
# runner: both
"""用容器盛汤和手往汤里倒东西的动作（Shared/Rules/HandsOn/PotServe.py / PotServePour.py / PotServeHands.py / PotServeMath.py）：
数值照 Hands-On Delight 的 PotBehavior（offerBowl 575-618、offerTakeBack 620-666、dipOffered 541-551、goesIn 812-838）和 KitchenMotions（Dip / Pour / Shake / Crack）。

Java：光标在锅中心 +-5 像素以内、手空着、不在勺子上、离上次盛 >= 0.35 秒才悬；悬在汤面上 1.5 像素（方块容器缩 0.45、高 5 像素）；
Dip：DOWN 0.14 秒平方加速浸到面下 0.4 歪 25 度、浸到换成盛满、涟漪 0.45 + 水花 x4、UP 0.26 秒提到面上 3、HOLD 0.08 秒、每秒滴 14 滴、AWAY 0.3 秒 smoothstep 端走缩没；
Pour：桶 0.3 + 0.2 + 0.8 秒、瓶 0.3 + 0.2 + 0.55 秒，再 0.2 秒放正、0.3 秒端走；Shake 0.3 + 0.18 + 0.6 + 0.15 秒、每秒 70 粒、每 0.1 秒一圈涟漪；
Crack 0.3 + 0.06 + 0.1 + 0.14 + 0.1 + 0.2 秒落到汤面、再 0.5 秒沉下去。
"""
from __future__ import print_function

import math

import fdtest

Serve = fdtest.load("Shared.Rules.HandsOn.PotServe")
Pour = fdtest.load("Shared.Rules.HandsOn.PotServePour")
Hands = fdtest.load("Shared.Rules.HandsOn.PotServeHands")
Maths = fdtest.load("Shared.Rules.HandsOn.PotServeMath")
DT = 0.01
SURFACE = 5.0
AT = (8.0, SURFACE + 1.5, 8.0)
AWAY = (8.0, 11.0, 30.0)
BROTH = 0xFF336699


def close(a, b, eps=1e-9):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def run(motion, seconds, dt=DT, **args):
    """推进 seconds 秒；返回 [(时刻, pose(s), events)]。"""
    out = []
    for index in range(int(round(seconds / dt))):
        posed, events = motion.step(dt, **args)
        out.append((round((index + 1) * dt, 6), posed, events))
    return out


def eventsOf(timeline, kind):
    return [(at, e) for at, _p, events in timeline for e in events if e["type"] == kind]


# ---------------------------------------------------------------- 数学

def testEasingAndTippedPoints():
    assert Maths.smooth(0.0) == 0.0 and Maths.smooth(1.0) == 1.0 and Maths.smooth(0.5) == 0.5 and Maths.smooth(-3) == 0.0 and Maths.smooth(9) == 1.0
    assert Maths.out(0.0) == 0.0 and Maths.out(1.0) == 1.0 and Maths.out(0.5) == 0.75 and Maths.out(2) == 1.0, "开头快收尾慢：1 - (1 - t) 的平方"
    assert close(Maths.tipped(0.0, 1.0, 1.0, 0.0, 0.0), (0.0, math.cos(math.radians(16)), math.sin(math.radians(16)))), "只往后仰 LEAN = 16 度"
    assert close(Maths.tipped(0.0, 1.0, 1.0, 0.0, 90.0), (math.sin(math.radians(16)), math.cos(math.radians(16)), 0.0), 1e-9), "再绕竖轴转 90 度"
    assert close(Maths.tipped(1.0, 0.0, 1.0, 90.0, 0.0), (0.0, math.cos(math.radians(16)), math.sin(math.radians(16))), 1e-9), "绕 z 转 90 度：x 变成 y"
    assert close(Maths.tipped(0.5, 0.25, 4.0, 0.0, 0.0)[:1], (2.0,)) and Maths.LEAN == 16.0
    assert close(Maths.rotateY((1.0, 0.0, 0.0), 90.0), (0.0, 0.0, -1.0), 1e-9), "JOML 的 rotateY：x 转到 -z"


# ---------------------------------------------------------------- 悬着的容器

def offer(**kw):
    args = dict(cursor=(8.0, 8.0), surface=SURFACE, now=10.0, scoopedAt=0.0)
    args.update(kw)
    return Serve.offerOf(**args)


def testAContainerHangsOverTheSoupAtTheCursor():
    shown = offer(cursor=(9.5, 6.25))
    assert shown["pos"] == (9.5, SURFACE + 1.5, 6.25), "悬在汤面上 1.5 像素，光标的位置"
    assert shown["scale"] == 1.0 and abs(shown["size"] - 8.0 * 0.3) < 1e-12 and shown["tint"] == 0x8CFFFFFF and shown["block"] is False
    block = offer(cursor=(9.5, 6.25), block=True)
    assert block["pos"] == (9.5, SURFACE + 5.0, 6.25) and block["scale"] == 0.45 and abs(block["size"] - 8.0 * 0.3 * 0.45) < 1e-12, "方块容器缩 0.45、悬高 5"


def testTheOfferNeedsAnEmptyHandOverThePotAndAWhileSinceTheLastScoop():
    assert offer() is not None
    assert offer(busy=True) is None, "上一份还在端走"
    assert offer(focused=False) is None and offer(spoon=True) is None and offer(carrying=True) is None and offer(hasContainer=False) is None
    assert offer(cursor=None) is None, "光标没落在汤面那个平面上"
    assert offer(now=0.34, scoopedAt=0.0) is None and offer(now=0.35, scoopedAt=0.0) is not None and offer(now=0.36) is not None, "盛过之后 0.35 秒内不悬新的"
    assert offer(cursor=(12.9, 8.0)) is not None and offer(cursor=(13.0, 8.0)) is None, "离锅中心 x 要小于 5 像素"
    assert offer(cursor=(8.0, 3.1)) is not None and offer(cursor=(8.0, 3.0)) is None and offer(cursor=(8.0, 13.0)) is None
    assert Serve.OFFER_AWAY == 0.35 and Serve.POT_HALF == 5.0 and Serve.OFFER_LIFT == 1.5 and Serve.OFFERED == 0x8CFFFFFF


def testWhatWentInWithoutFloatingCanBeTakenBackOut():
    enabled, shown = Serve.takeBackOf((9.0, 7.0), SURFACE, 10.0, 0.0, hovered=True)
    assert enabled and shown["pos"] == (9.0, SURFACE + 1.5, 7.0) and shown["scale"] == 0.6 and abs(shown["size"] - 8.0 * 0.3 * 0.6) < 1e-12
    assert Serve.takeBackOf((9.0, 7.0), SURFACE, 10.0, 0.0, hovered=False) == (True, None), "光标不在汤面上：汤面照样接点击，但不悬东西"
    for blocked in (dict(focused=False), dict(spoon=True), dict(offered=True), dict(hasSunk=False), dict(carrying=True), dict(busy=True)):
        assert Serve.takeBackOf((9.0, 7.0), SURFACE, 10.0, 0.0, hovered=True, **blocked) == (False, None), blocked
    assert Serve.takeBackOf((9.0, 7.0), SURFACE, 0.2, 0.0, hovered=True) == (False, None), "盛过 0.35 秒内不接"
    assert Serve.takeBackOf(None, SURFACE, 10.0, 0.0, hovered=True) == (True, None)


# ---------------------------------------------------------------- 浸下去、提上来、端走

def testTheDipGoesDownQuadraticallyTippingTwentyFiveDegrees():
    dip = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH)
    posed, events = dip.step(0.07, SURFACE)
    k = 0.5
    assert abs(posed["pos"][1] - (AT[1] + k * k * ((SURFACE - 0.4) - AT[1]))) < 1e-9, "y = lerp(k * k, 悬着的高度, 面下 0.4)"
    assert posed["pos"][0] == 8.0 and posed["pos"][2] == 8.0 and abs(posed["rot"][0] - 12.5) < 1e-9, "歪 25 * k 度"
    assert not events and not posed["filled"] and posed["visible"] and posed["scale"] == 1.0


def testTheDipFillsRingsAndSplashesTheMomentItIsUnder():
    dip = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH)
    dip.step(0.13, SURFACE)
    posed, events = dip.step(0.01, SURFACE)
    assert [e["type"] for e in events] == ["ripple", "splash", "filled"]
    assert events[0] == {"type": "ripple", "x": 8.0, "z": 8.0, "strength": 0.45}
    assert events[1] == {"type": "splash", "count": 4, "pos": (8.0, SURFACE, 8.0), "rise": (0.0, 6.0, 0.0), "spread": 0.6, "color": BROTH}
    assert posed["filled"] and posed["pos"][1] < SURFACE - 0.39 + 0.05, "浸到面下 0.4 像素的位置"
    sound = {"type": "sound", "name": "scoop", "volume": 0.45, "pitch": 1.1, "at": "broth"}
    other = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH, sound=sound)
    assert sound in other.step(0.14, SURFACE)[1], "取回沉下去的东西用 scoopBack 的声音，浸到的那一刻放"
    assert sound not in other.step(0.01, SURFACE)[1], "只放一次"


def testTheDipLiftsToThreePixelsOverTheSurfaceHoldsAndLeavesAfterTheTimeline():
    dip = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH)
    timeline = run(dip, 0.9, surface=SURFACE)
    byAt = dict((at, posed) for at, posed, _e in timeline)
    assert abs(byAt[0.15]["rot"][0] - 25.0 * (1.0 - Maths.out(0.01 / 0.26))) < 1e-6, "提的时候歪的角度从 25 度回正"
    top = byAt[0.41]
    assert abs(top["pos"][1] - (SURFACE + 3.0)) < 1e-6 and abs(top["rot"][0]) < 1e-6, "提到面上 3 像素、正过来"
    assert abs(byAt[0.47]["pos"][1] - (SURFACE + 3.0)) < 1e-6, "停 HOLD 0.08 秒：还在顶上"
    assert dip.done and not byAt[0.9]["visible"] and byAt[0.9]["scale"] == 1.0 and byAt[0.9]["rot"] == (0.0, 0.0, 0.0), "走完：隐藏、归位"
    ended = [at for at, posed, _e in timeline if not posed["visible"]]
    assert 0.78 <= ended[0] <= 0.80, "0.14 + 0.26 + 0.08 + 0.3 = 0.78 秒走完"
    posed, events = dip.step(DT, SURFACE)
    assert not posed["visible"] and events == [], "走完之后什么都不发"


def testTheDipCarriesTheContainerAwayShrinkingToTheCooksPoint():
    dip = Serve.Dip(AT, AWAY, 0.45, 1.08, BROTH)
    timeline = run(dip, 0.9, surface=SURFACE)
    byAt = dict((at, posed) for at, posed, _e in timeline)
    middle = byAt[0.63]
    assert abs(middle["scale"] - 0.45 * 0.5) < 0.01, "smoothstep 走到一半（端走开始后 0.15 秒）缩一半：scale * (1 - k)"
    assert close(middle["pos"], Maths.mix((8.0, SURFACE + 3.0, 8.0), AWAY, 0.5), 0.15), "朝给的点走：(at.x, 顶, at.z) 到 away"
    assert byAt[0.77]["scale"] < 0.05 and byAt[0.77]["visible"]


def testTheDipDripsFourteenDropsASecondWhileItLifts():
    dip = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH)
    timeline = run(dip, 0.9, surface=SURFACE)
    lifting = [e for at, e in eventsOf(timeline, "drip") if at <= 0.14 + 0.26 + 0.08 + 0.011]
    assert sum(e["count"] for e in lifting) == 4, "0.34 秒 * 14 = 4.76：滴了 4 滴"
    assert lifting[0]["rise"] == (0.0, -2.0, 0.0) and lifting[0]["spread"] == 0.6 and lifting[0]["color"] == BROTH
    assert lifting[0]["pos"][0] == 8.0 and lifting[0]["pos"][2] == 8.0
    assert SURFACE - 0.4 - 0.72 - 1e-9 <= lifting[0]["pos"][1] <= SURFACE + 3.0 - 0.72 + 1e-9, "从容器底下滴：比容器低 size * 0.3 = 0.72"
    late = [at for at, _e in eventsOf(timeline, "drip") if at > 0.48 + 0.3 * 0.45]
    assert late == [], "端走的前 40% 还在滴，之后不滴了"


def testTheDipFollowsTheSurfaceWhenTheSoupIsLadledLower():
    dip = Serve.Dip(AT, AWAY, 1.0, 2.4, BROTH)
    dip.step(0.14, SURFACE)
    posed, _events = dip.step(0.26, SURFACE - 2.0)
    assert abs(posed["pos"][1] - (SURFACE - 2.0 + 3.0)) < 1e-9, "提到的是此刻的液面 + 3"
    assert Serve.awayFallback(AT, SURFACE) == (8.0, SURFACE + 8.0, 8.0)


# ---------------------------------------------------------------- 倒液体

def testPouringTimesAndTheLipLandsOnTheTarget():
    assert Pour.Pour.pouredBy(True) == 0.3 + 0.2 + 0.8 and Pour.Pour.pouredBy(False) == 0.3 + 0.2 + 0.55
    assert (Pour.ARRIVE, Pour.TIP, Pour.BUCKET_FLOW, Pour.BOTTLE_FLOW, Pour.BACK, Pour.AWAY) == (0.3, 0.2, 0.8, 0.55, 0.2, 0.3)
    assert (Pour.COCK, Pour.EMPTYING, Pour.OVER, Pour.THROW, Pour.FROM_SCALE, Pour.HAND_SIZE) == (-12.0, 14.0, 3.2, 1.3, 0.5, 2.9)
    onto = (7.4, 0.0, 8.8)
    for bucket, side, yaw in ((True, -1.0, 0.0), (False, -1.0, 0.0), (True, 1.0, 180.0), (False, 1.0, 90.0)):
        pour = Pour.Pour(bucket, (8.0, 12.0, 30.0), onto, SURFACE, 2.9, side, yaw)
        lip = Maths.tipped(side * Maths.LIP_X, Maths.LIP_Y, 2.9, side * (105.0 if bucket else 125.0), yaw)
        away = Maths.rotateY((-side * 1.3, 0.0, 0.0), yaw)
        assert close((pour.middle[0] + lip[0] + away[0], pour.middle[1] + lip[1], pour.middle[2] + lip[2] + away[2]), (7.4, SURFACE + 3.2, 8.8)), (bucket, side, yaw)
        assert abs(pour.duration - (Pour.Pour.pouredBy(bucket) + 0.5)) < 1e-12


def testTheHandComesInAnArcCockedBackAndGrowingFromHalfSize():
    pour = Pour.Pour(True, (8.0, 12.0, 30.0), (7.4, 0.0, 8.8), SURFACE)
    posed, events = pour.step(0.15)
    k = 0.5
    mid = Maths.mix((8.0, 12.0, 30.0), pour.middle, k)
    assert close(posed["pos"], (mid[0], mid[1] + 2.0, mid[2])), "弧顶高 2 像素"
    assert abs(posed["rot"][2] - (-1.0 * -12.0 * k)) < 1e-9 and posed["rot"][0] == 16.0 and posed["item"] == "full", "往倾倒的反方向仰 12 * k 度"
    assert abs(posed["scale"] - 2.9 / 8.0 * 0.75) < 1e-9, "先小后大：lerp(k, 0.5, 1)"
    assert not events


def testABucketPoursForEightTenthsOfASecondInAThickStreamThatThins():
    pour = Pour.Pour(True, (8.0, 12.0, 30.0), (7.4, 0.0, 8.8), SURFACE, color=0xFFFFFFFF, key="pour_1")
    timeline = run(pour, 1.9)
    sound = eventsOf(timeline, "sound")
    assert len(sound) == 1 and sound[0][1]["name"] == "bucket_empty" and sound[0][1]["volume"] == 0.45 and 0.5 <= sound[0][0] <= 0.52
    flow = eventsOf(timeline, "flow")
    assert len(flow) == 1 and flow[0][0] == sound[0][0], "流出来那一刻汤开始染色"
    streams = [e for _at, e in eventsOf(timeline, "stream")]
    assert 78 <= len(streams) <= 81, "0.8 秒每帧一条"
    assert streams[0]["strength"] < 0.15 and max(e["strength"] for e in streams) == 1.0, "粗细先涨到 1.0（桶）"
    assert abs(streams[-1]["strength"] - 0.25) < 0.03, "收尾细到 1 - 0.75 = 0.25"
    assert all(e["key"] == "pour_1" and e["liquid"] == "broth" and e["to"][1] == SURFACE for e in streams)
    drops = eventsOf(timeline, "droplets")
    assert len(drops) == 1 and drops[0][1]["count"] == 2 and drops[0][1]["rise"] == (0.0, -6.0, 0.0) and 1.29 <= drops[0][0] <= 1.31
    items = [(at, posed["item"]) for at, posed, _e in timeline if posed["visible"]]
    assert [item for at, item in items if at < 1.29] == ["full"] * len([1 for at, _i in items if at < 1.29]) and items[-1][1] == "empty", "倒空之后拿着空容器"
    assert pour.done and not timeline[-1][1]["visible"]
    ended = [at for at, posed, _e in timeline if not posed["visible"]][0]
    assert 1.8 <= ended <= 1.82, "1.0 + 0.8 = 1.8 秒"


def testABottlePoursFasterAndThinner():
    pour = Pour.Pour(False, (8.0, 12.0, 30.0), (7.4, 0.0, 8.8), SURFACE)
    timeline = run(pour, 1.6)
    assert eventsOf(timeline, "sound")[0][1]["name"] == "bottle_empty"
    streams = [e for _at, e in eventsOf(timeline, "stream")]
    assert 53 <= len(streams) <= 56 and abs(max(e["strength"] for e in streams) - 0.45) < 1e-9, "0.55 秒，粗细 0.45"
    angles = [posed["rot"][2] for at, posed, _e in timeline if 0.5 < at < 1.04]
    assert all(abs(angle - (-125.0)) < 14.0 + 2.5 for angle in angles), "倾到 125 度，越倒越倾 14 度，手抖 2 度"
    assert pour.done and 1.55 <= [at for at, posed, _e in timeline if not posed["visible"]][0] <= 1.57


def testTheEmptyContainerSettlesUprightAndGoesBackSmaller():
    pour = Pour.Pour(False, (8.0, 12.0, 30.0), (7.4, 0.0, 8.8), SURFACE)
    timeline = run(pour, 1.6)
    byAt = dict((at, posed) for at, posed, _e in timeline)
    settled = byAt[1.05 + 0.2]
    assert abs(settled["rot"][2]) < 1.0 and abs(settled["pos"][1] - (pour.middle[1] + 1.0)) < 0.05, "放正，同时提 1 像素"
    leaving = byAt[1.25 + 0.15]
    assert abs(leaving["scale"] - 2.9 / 8.0 * 0.5) < 0.02, "端走：缩一半时 k = 0.5"
    assert close(leaving["pos"], Maths.mix((pour.middle[0], pour.middle[1] + 1.0, pour.middle[2]), (8.0, 15.0, 30.0), 0.5), 0.2)


# ---------------------------------------------------------------- 抖粉末

def testShakeGoesOverAndShakesGrainsDown():
    onto = (7.4, 0.0, 8.8)
    shake = Hands.Shake((8.0, 12.0, 30.0), onto, SURFACE, 0xFFFFFFFF, lambda: 0.5)
    mouth = Maths.tipped(0.0, Maths.LIP_Y, Hands.HAND_SIZE * 0.8, -140.0, 0.0)
    assert close((shake.middle[0] + mouth[0], shake.middle[1] + mouth[1], shake.middle[2] + mouth[2]), (7.4, SURFACE + 3.5, 8.8))
    assert Hands.Shake.doneBy() == 0.3 + 0.18 + 0.6 + 0.15
    first = shake.step(0.0)[0]
    assert abs(first["scale"] - 2.9 * 0.8 / 8.0 * 0.5) < 1e-9, "从手里端来，半大"
    timeline = run(shake, 1.3)
    sand = eventsOf(timeline, "sound")
    assert len(sand) == 1 and sand[0][1]["name"] == "brush_sand" and sand[0][1]["volume"] == 0.25 and sand[0][1]["pitch"] == 1.4 and 0.48 <= sand[0][0] <= 0.5
    grains = eventsOf(timeline, "grains")
    total = sum(e["count"] for _at, e in grains)
    assert 28 <= total <= 30, "每秒 70 粒，越抖越少：70 * (0.6 - 0.18) = 29.4"
    assert all(e["rise"] == (0.0, -3.0, 0.0) and e["spread"] == 0.35 and e["color"] == 0xFFFFFFFF for _at, e in grains)
    rings = eventsOf(timeline, "ripple")
    assert 6 <= len(rings) <= 7 and all(e["strength"] == 0.05 for _at, e in rings), "每 0.1 秒一圈小涟漪"
    assert shake.done and 1.23 <= [at for at, posed, _e in timeline if not posed["visible"]][0] <= 1.25


def testTheShakeRipplesLandNearTheMouth():
    draws = [0.0, 1.0] * 20
    shake = Hands.Shake((8.0, 12.0, 30.0), (7.4, 0.0, 8.8), SURFACE, 0xFFFFFFFF, lambda: draws.pop(0))
    timeline = run(shake, 1.3)
    at, first = eventsOf(timeline, "ripple")[0]
    # 抖的第一步就落一圈（计时器从 0 开始）：在瓶口 +-0.5 像素以内，x 用第一个随机数、z 用第二个：0.0 -> -0.5，1.0 -> +0.5
    k = (at - (0.3 + 0.18)) / 0.6
    mouth = Maths.add(Maths.tipped(0.0, Maths.LIP_Y, Hands.HAND_SIZE * 0.8 * (1.0 - 0.45 * k), -140.0, 0.0), shake.middle)
    assert abs(first["x"] - (mouth[0] - 0.5)) < 1e-4 and abs(first["z"] - (mouth[2] + 0.5)) < 1e-4 and first["strength"] == 0.05


# ---------------------------------------------------------------- 打鸡蛋

def testACrackedEggIsKnockedOpenedAndLandsInTheSoup():
    crack = Hands.Crack((8.0, 12.0, 30.0), (3.0, 10.0, 8.8), (6.0, 0.0, 8.8), SURFACE)
    assert abs(Hands.Crack.landsBy() - 0.9) < 1e-12
    timeline = run(crack, 1.5)
    dusts = eventsOf(timeline, "dust")
    assert [e["count"] for _at, e in dusts] == [5, 4] and 0.36 <= dusts[0][0] <= 0.37 and 0.6 <= dusts[1][0] <= 0.61, "磕下去那一刻碎屑 x5，壳裂开碎屑 x4"
    assert dusts[0][1]["color"] == 0xFFEAD9B8 and dusts[0][1]["pos"] == (3.0, 10.0, 8.8), "碎屑在蛋最低点磕到的地方"
    assert dusts[1][1]["pos"] == (6.0, SURFACE + 2.5, 8.8)
    sounds = eventsOf(timeline, "sound")
    assert [(e["name"], e["volume"], e["pitch"]) for _at, e in sounds] == [("egg_crack", 0.35, 1.5), ("plop", 0.35, 1.25)], "磕的脆响、蛋液落下的噗"
    assert 0.9 <= sounds[1][0] <= 0.91
    shakes = eventsOf(timeline, "shake")
    assert [(e["node"], e["amount"], e["seconds"]) for _at, e in shakes] == [("egg", 0.15, 0.12), ("inside", 0.12, 0.15)]
    ripple = eventsOf(timeline, "ripple")
    assert len(ripple) == 1 and ripple[0][1] == {"type": "ripple", "x": 6.0, "z": 8.8, "strength": 0.35}
    splash = eventsOf(timeline, "splash")[0][1]
    assert splash["count"] == 3 and splash["color"] == 0xFFF4F0E4 and splash["pos"] == (6.0, SURFACE, 8.8) and splash["rise"] == (0.0, 6.0, 0.0)
    assert crack.done and 1.4 <= [at for at, posed, _e in timeline if not posed["inside"]["visible"] and at > 0.9][0] <= 1.42, "0.9 + 0.5 沉完"


def testTheEggDisappearsAndItsInsideFallsFasterAndFaster():
    crack = Hands.Crack((8.0, 12.0, 30.0), (3.0, 10.0, 8.8), (6.0, 0.0, 8.8), SURFACE)
    byAt = dict((at, posed) for at, posed, _e in run(crack, 1.5))
    assert byAt[0.5]["egg"]["visible"] and not byAt[0.5]["inside"]["visible"], "0.5 秒：蛋还在，蛋液还没出来"
    assert byAt[0.65]["egg"]["visible"] and byAt[0.65]["inside"]["visible"] and byAt[0.65]["egg"]["scale"] < 2.4 / 8.0, "0.6 到 0.7 秒壳缩没、蛋液出现"
    assert not byAt[0.75]["egg"]["visible"], "0.7 秒之后蛋没了"
    over = SURFACE + 2.5
    fall = byAt[0.8]["inside"]["pos"][1]
    assert abs(fall - (over - 0.3 + (SURFACE - (over - 0.3)) * 0.25)) < 0.05, "越落越快：k = 0.5 时只落了四分之一"
    assert byAt[0.8]["inside"]["scale"] > 0.7 and abs(byAt[0.95]["inside"]["pos"][1] - (SURFACE - 1.2 * Maths.smooth(0.05 / 0.5))) < 0.05
    assert byAt[1.2]["inside"]["scale"] < 0.6, "沉的时候缩没"
    assert byAt[0.5]["egg"]["pos"][1] > 9.0 and byAt[0.5]["egg"]["rot"][0] == 16.0


def testAnEggThatDoesNotSinkLeavesWhenItLands():
    crack = Hands.Crack((8.0, 12.0, 30.0), (3.0, 10.0, 8.8), (6.0, 0.0, 8.8), SURFACE, sinks=False)
    timeline = run(crack, 1.2)
    assert crack.done and not [at for at, posed, _e in timeline if at > 0.95 and posed["inside"]["visible"]], "不沉：落到面上就交给调用方"
    assert eventsOf(timeline, "ripple")


# ---------------------------------------------------------------- 选手的动作

def testTheHandMotionFollowsWhatWentIn():
    start = (8.0, 12.0, 30.0)
    egg = Hands.goesIn("cracked", 1, start, SURFACE, 10.0, lambda: 0.5)
    assert isinstance(egg, Hands.Crack) and egg.rim == (3.0, 10.0 + 2.4 * 0.42, 8.8) and egg.over == (6.0, SURFACE + 2.5, 8.8), "右沿磕开：8 - 5、锅沿高度，蛋液落在 8 - 2"
    for index, z in ((0, 7.4), (1, 8.8), (2, 10.2), (3, 7.4)):
        assert abs(Hands.goesIn("cracked", index, start, SURFACE, 10.0, lambda: 0.5).over[2] - z) < 1e-9, "同时倒进去的沿 z 错开 1.4 * (槽位 % 3 - 1)"
    milk = Hands.goesIn("poured", 2, start, SURFACE, 10.0, lambda: 0.5, bucket=True, color=0xFFFFFFFF)
    assert isinstance(milk, Pour.Pour) and milk.bucket and milk.key == "pour_2" and milk.size == 2.9 and milk.side == -1.0
    bottle = Hands.goesIn("poured", 0, start, SURFACE, 10.0, lambda: 0.5, key="mine")
    assert not bottle.bucket and bottle.key == "mine"
    sugar = Hands.goesIn("dissolves", 0, start, SURFACE, 10.0, lambda: 0.5, color=0xFFEEDDCC)
    assert isinstance(sugar, Hands.Shake) and abs(sugar.size - 2.9 * 0.8) < 1e-12 and sugar.color == 0xFFEEDDCC


def testWhatDissolvedSendsUpItsLastBubbles():
    events = Hands.wentIn("dissolves", 0xE0AABBCC)
    assert events[0] == {"type": "bubbles", "count": 6, "rise": (0.0, 3.5, 0.0), "color": 0xE0AABBCC}
    assert events[1]["name"] == "plop" and events[1]["volume"] == 0.25 and events[1]["pitch"] == 1.35
    assert Hands.wentIn("poured", 0) == [] and Hands.wentIn("cracked", 0) == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
