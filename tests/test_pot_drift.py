# -*- coding: utf-8 -*-
# runner: both
"""PotDrift / PotDriftArrive / PotDriftExtras（厨锅浮料）的测试。数字来自 Hands-On Delight 的 client/PotBehavior.java
（drift 1395-1479、shoulder 1509-1538、tumble 1541-1551、place 1554-1576、到达 207-210 / 741-756 / 850-870、splashIn 786-798）。"""
from __future__ import print_function

import math

import fdtest

D = fdtest.load("Shared.Rules.HandsOn.PotDrift")
A = fdtest.load("Shared.Rules.HandsOn.PotDriftArrive")
X = fdtest.load("Shared.Rules.HandsOn.PotDriftExtras")

SURFACE = 5.77                 # 空锅加一份料后的液面高度，px（PotLiquid 的 5.77）
BASE = SURFACE + 0.25          # 料浮在液面上方 0.25 px（节点高 8，沉在水下 0.25：ITEM_REST 7.75）
TWO_PI = 2.0 * math.pi
DT = 1.0 / 60.0


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def sameAngle(a, b, eps=1.0e-9):
    """两个角度（度）在 360 度里是同一个。"""
    assert abs((a - b + 180.0) % 360.0 - 180.0) <= eps, "%r != %r" % (a, b)


def smooth(x):
    return x * x * (3.0 - 2.0 * x)


def settled(count, slots=6):
    """一圈已经排好的料：places 直接设成各自该在的位置（跳过加进来时互相穿过的那段过渡）。返回 (drift, present)。"""
    drift = D.PotDrift()
    present = [i < count for i in range(slots)]
    for rank in range(count):
        drift.places[rank] = rank * TWO_PI / count
    return drift, present


def run(drift, present, seconds, dt=DT, start=0.0, **spoon):
    """推进 seconds 秒，返回结束时的钟。spoon：step 的 spoonX / spoonZ / grip / swirl / swirlSign / rand。"""
    time = start
    for _ in range(int(round(seconds / dt))):
        time += dt
        drift.step(dt, time, present, SURFACE, **spoon)
    return time


def lcg(seed):
    """确定的伪随机数 rand() -> 0..1。"""
    state = [seed]

    def rand():
        state[0] = (state[0] * 1103515245 + 12345) % 2147483648
        return state[0] / 2147483648.0
    return rand


def testConstantsAreTheJavaOnes():
    assert (D.SLOTS, D.DRIFT_RADIUS, D.ITEM_CLEARANCE, D.ITEM_ROOM, D.ITEM_RADIUS, D.SPOON_RADIUS) == (6, 2.2, 2.1, 2.9, 1.15, 1.05)
    assert (D.PUSH_HALF_LIFE, D.CALM_DRIFT, D.SWIRL_SPEED, D.PLACE_EASE) == (0.35, 0.05, 1.5, 2.5)
    assert (D.TUMBLE_FROM, D.TUMBLE_RATE, D.TUMBLE_TIME, D.TUMBLE_HOP) == (0.3, 0.35, 0.7, 0.7)
    assert (D.ARRIVE_STAGGER, D.ARRIVE_TIME, D.ARRIVE_FROM, D.ARRIVE_ARC, D.ARRIVE_ROLL) == (0.16, 0.4, 9.0, 4.0, 180.0)
    near(D.ITEM_LIFT, 0.25)
    near(D.ITEM_RADIUS * 2.0, 2.3)


def testOneItemSitsOnTheRing():
    drift, present = settled(1)
    drift.step(0.0, 0.0, present, SURFACE)
    near(drift.x[0], 8.0 + 2.2)
    near(drift.z[0], 8.0)
    near(drift.y[0], 6.02)                                       # 5.77 + 0.25 + 0.07 * sin(0)
    sameAngle(drift.yaw[0], 0.0)
    near(drift.pitch[0], 0.0)
    near(drift.roll[0], 3.0)                                     # 3 * cos(0)
    assert drift.visible[0] and drift.scale[0] == 1.0 and not drift.waiting[0]
    for i in range(1, 6):
        assert not drift.visible[i] and drift.scale[i] == 0.0, "没有料的格子不画"


def testItemsShareTheRingEvenly():
    for count in (1, 2, 3, 4, 5):
        drift, present = settled(count)
        drift.step(0.0, 0.0, present, SURFACE)
        for i in range(count):
            near(math.hypot(drift.itemX[i], drift.itemZ[i]), 2.2)
            angle = math.atan2(drift.itemZ[i], drift.itemX[i]) % TWO_PI
            near(angle, i * TWO_PI / count % TWO_PI, 1.0e-9)
        if count > 1:
            side = 2.0 * 2.2 * math.sin(math.pi / count)           # 相邻两件的弦长
            near(math.hypot(drift.itemX[1] - drift.itemX[0], drift.itemZ[1] - drift.itemZ[0]), side)
            assert side >= 2.3 or count > 4, "五件以内本来就不挤"
    near(2.0 * 2.2 * math.sin(math.pi / 2), 4.4)
    near(2.0 * 2.2 * math.sin(math.pi / 3), 3.8105117766, 1.0e-9)


def testPlacesEaseTowardTheirRankAtTwoAndAHalfPerSecond():
    drift = D.PotDrift()
    present = [True, True, False, False, False, False]
    drift.step(0.2, 0.0, present, SURFACE)                       # ease = 0.2 * 2.5 = 0.5
    near(drift.places[0], 0.0)
    near(drift.places[1], 0.5 * math.pi)                          # 离目标 π 走一半
    drift.step(0.4, 0.2, present, SURFACE)                       # ease 到 1 封顶：一步到位
    near(drift.places[1], math.pi)
    drift.step(10.0, 0.6, present, SURFACE)
    near(drift.places[1], math.pi)


def testCalmWaterTurnsOnceInAboutOneHundredTwentySixSeconds():
    near(TWO_PI / D.CALM_DRIFT, 125.6637, 1.0e-4)
    drift, present = settled(1)
    drift.step(0.0, 0.0, present, SURFACE)
    startX, startZ = drift.itemX[0], drift.itemZ[0]
    steps = 1000
    dt = TWO_PI / D.CALM_DRIFT / steps
    time = 0.0
    for _ in range(steps):
        time += dt
        drift.step(dt, time, present, SURFACE)
    near(drift.turned, TWO_PI, 1.0e-9)
    near(drift.itemX[0], startX, 1.0e-9)
    near(drift.itemZ[0], startZ, 1.0e-9)
    near(drift.current, 0.05)


def testStirringSpeedsTheCircleUpBothWays():
    drift, present = settled(1)
    drift.step(1.0, 1.0, present, SURFACE, swirl=1.0)
    near(drift.current, 1.55)
    near(drift.turned, 1.55)
    drift.step(1.0, 2.0, present, SURFACE, swirl=1.0, swirlSign=-1.0)
    near(drift.current, -1.55)
    near(drift.turned, 0.0)
    drift.step(1.0, 3.0, present, SURFACE, swirl=0.5)
    near(drift.current, 0.8)
    drift.step(1.0, 4.0, present, SURFACE)
    near(drift.current, 0.05)


def testYawFollowsTheCircleAndTheItemRocksOnTheClock():
    drift, present = settled(3)
    time = 3.7
    drift.step(0.0, time, present, SURFACE)
    for i in range(3):
        angle = math.atan2(drift.itemZ[i], drift.itemX[i])
        sameAngle(drift.yaw[i], -math.degrees(angle))             # 料朝着前进的方向：-angle
        near(drift.y[i], BASE + 0.07 * math.sin(0.9 * time + 1.3 * i))
        near(drift.pitch[i], 3.0 * math.sin(0.5 * time + i))
        near(drift.roll[i], 3.0 * math.cos(0.4 * time + i))
        assert -180.0 <= drift.yaw[i] < 180.0
    highest, lowest, tilt = -9.0, 9.0, 0.0
    drift, present = settled(1)
    for k in range(4000):
        drift.step(0.0, k * 0.05, present, SURFACE)
        highest, lowest = max(highest, drift.y[0]), min(lowest, drift.y[0])
        tilt = max(tilt, abs(drift.pitch[0]), abs(drift.roll[0]))
    near(highest, BASE + 0.07, 1.0e-4)                             # 起伏 +-0.07 px
    near(lowest, BASE - 0.07, 1.0e-4)
    near(tilt, 3.0, 1.0e-3)                                        # 晃 +-3 度


def testRestingSpoonLeavesAGapOnItsOwnSide():
    for count, opposite in ((1, math.pi), (2, math.pi / 2.0)):
        drift, present = settled(count)
        drift.step(0.0, 0.0, present, SURFACE, spoonX=1.0, spoonZ=1.0, grip=0.0)
        near(drift.circleStart, math.pi / 4.0 + math.pi / count)
        first = math.atan2(drift.itemZ[0], drift.itemX[0])
        near(abs((first - math.pi / 4.0 + math.pi) % TWO_PI - math.pi), opposite)   # 勺子和第一件之间留的角度
    drift, present = settled(3)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.2, spoonZ=0.0, grip=0.0)
    near(drift.circleStart, math.pi / 3.0)                        # 缺口里勺子在正中：两边各 π / 件数


def testNoGapWhileTheSpoonIsInHandOrNearTheMiddle():
    drift, present = settled(2)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=1.0, spoonZ=0.0, grip=0.05)       # grip 到 0.05 就算握着
    assert drift.circleStart is None
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.09, spoonZ=0.0, grip=0.0)       # 离心 0.1 px 以内：当它在中间
    assert drift.circleStart is None
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.11, spoonZ=0.0, grip=0.049)
    assert drift.circleStart is not None
    held = drift.circleStart
    drift.step(1.0, 0.0, present, SURFACE, spoonX=0.0, spoonZ=2.0, grip=0.5)        # 一握上手，缺口就不再跟着动
    assert drift.circleStart == held


def testGapFollowsTheSpoonByTheShortWayRound():
    drift, present = settled(1)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=math.cos(3.0), spoonZ=math.sin(3.0), grip=0.0)
    near(drift.circleStart, 3.0 + math.pi)
    before = drift.circleStart
    drift.step(0.04, 0.04, present, SURFACE, spoonX=math.cos(-3.0), spoonZ=math.sin(-3.0), grip=0.0)
    wanted = -3.0 + math.pi
    short = ((wanted - before + math.pi) % TWO_PI) - math.pi      # 3.0 -> -3.0 只差 0.283 弧度，不是 6
    near(short, 2.0 * math.pi - 6.0)
    near(drift.circleStart, before + short * 0.1, 1.0e-9)         # dt 0.04 * 2.5 = 0.1


def testItemsStayTwoPointOnePixelsAwayFromTheSpoon():
    drift, present = settled(1)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.5, spoonZ=0.0, grip=1.0)
    near(drift.itemX[0], 0.5 + 2.1)                               # 从勺子往外推到 2.1 px
    near(drift.itemZ[0], 0.0)
    near(drift.pushX[0], 0.4)                                     # 推开的量记下来，之后慢慢回原路
    near(drift.x[0], 8.0 + 2.6)
    wall, present = settled(1)
    wall.step(0.0, 0.0, present, SURFACE, spoonX=2.0, spoonZ=0.0, grip=1.0)
    near(wall.itemX[0], 2.9)                                      # 勺子贴着圈：墙比勺子硬，进了 2.1 也出不去


def testPushesDieAwayWithAHalfLifeOfAThirdOfASecond():
    drift, present = settled(1)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.5, spoonZ=0.0, grip=1.0)
    near(drift.pushX[0], 0.4)
    drift.step(0.35, 0.35, present, SURFACE, spoonX=-9.0, spoonZ=0.0, grip=1.0)     # 勺子走远了
    near(drift.pushX[0], 0.2)
    near(drift.pushZ[0], 0.0)
    drift.step(0.35, 0.7, present, SURFACE, spoonX=-9.0, spoonZ=0.0, grip=1.0)
    near(drift.pushX[0], 0.1)
    drift.step(0.7, 1.4, present, SURFACE, spoonX=-9.0, spoonZ=0.0, grip=1.0)
    near(drift.pushX[0], 0.025)


def testNothingLeavesTheBox():
    rand = lcg(7)
    drift = D.PotDrift()
    present = [True] * 6
    time = 0.0
    for _ in range(600):
        time += DT
        drift.step(DT, time, present, SURFACE, spoonX=rand() * 7.0 - 3.5, spoonZ=rand() * 7.0 - 3.5,
                   grip=rand(), swirl=rand(), swirlSign=1.0 if rand() < 0.5 else -1.0, rand=rand)
        for i in range(6):
            assert abs(drift.itemX[i]) <= 2.9 + 1.0e-9 and abs(drift.itemZ[i]) <= 2.9 + 1.0e-9


def testSixItemsPushEachOtherApart():
    drift, present = settled(6)
    run(drift, present, 10.0)
    smallest = min(math.hypot(drift.itemX[i] - drift.itemX[j], drift.itemZ[i] - drift.itemZ[j]) for i in range(6) for j in range(i + 1, 6))
    assert 2.25 <= smallest <= 2.31, smallest                    # 圈上本来 2.2 一个挨一个，推开到两件的半径之和 2.3
    for i in range(6):
        assert abs(drift.itemX[i]) <= 2.9 + 1.0e-9 and abs(drift.itemZ[i]) <= 2.9 + 1.0e-9
    ring, present = settled(5)
    run(ring, present, 5.0)
    for i in range(5):
        near(math.hypot(ring.itemX[i], ring.itemZ[i]), 2.2, 1.0e-6)     # 五件弦长 2.586，用不着推


def testTumbleNeedsAStrongSwirl():
    calls = []

    def rand():
        calls.append(1)
        return 0.0
    drift, present = settled(1)
    drift.step(0.1, 0.1, present, SURFACE, swirl=0.3, rand=rand)       # 刚好 0.3：不翻
    assert calls == [] and drift.tumbling[0] == 0.0
    drift.step(0.1, 0.2, present, SURFACE, swirl=0.31, rand=None)      # 没有随机数：不翻
    assert drift.tumbling[0] == 0.0
    drift.step(0.1, 0.3, present, SURFACE, swirl=0.31, rand=rand)
    assert len(calls) == 1 and drift.tumbling[0] == 0.001
    chance = D.PotDrift()
    chance.places[0] = 0.0
    present = [True] + [False] * 5
    chance.step(0.1, 0.0, present, SURFACE, swirl=1.0, rand=lambda: 0.0349)     # dt * 0.35 * swirl = 0.035
    assert chance.tumbling[0] > 0.0
    miss = D.PotDrift()
    miss.step(0.1, 0.0, present, SURFACE, swirl=1.0, rand=lambda: 0.0351)
    assert miss.tumbling[0] == 0.0


def testTumbleTakesSevenTenthsOfASecondWithAHop():
    drift, present = settled(1)
    drift.step(0.35, 0.35, present, SURFACE, swirl=1.0, rand=lambda: 0.0)
    near(drift.tumbling[0], 0.001)
    drift.step(0.35, 0.7, present, SURFACE, swirl=1.0, rand=lambda: 0.0)      # 翻到 0.501
    near(drift.tumbling[0], 0.501)
    bob = 0.07 * math.sin(0.9 * 0.7)
    near(drift.y[0], BASE + bob + 0.7 * math.sin(0.501 * math.pi))            # 最高跳 0.7 px
    near(drift.pitch[0], 3.0 * math.sin(0.5 * 0.7) + 360.0 * smooth(0.501))   # 空翻 360 度，缓入缓出
    near(drift.roll[0], 3.0 * math.cos(0.4 * 0.7))
    drift.step(0.35, 1.05, present, SURFACE, swirl=1.0, rand=lambda: 0.0)     # 0.7 秒到了，这一帧不再翻
    assert drift.tumbling[0] == 0.0
    near(drift.pitch[0], 3.0 * math.sin(0.5 * 1.05))
    drift.step(0.35, 1.4, present, SURFACE, swirl=1.0, rand=lambda: 0.0)      # 下一帧还可以再翻
    assert drift.tumbling[0] == 0.001


def testWaitingOnlyOneItemAtATimeLandsAtOnce():
    drift = D.PotDrift()
    drift.arrive([2])
    assert drift.events == [(D.EVENT_LANDED, 2)]
    assert not drift.arrivals.arriving[2], "只放进一件：直接落水，不飞"
    del drift.events[:]
    drift.arrive([4], sinking=[True])
    assert drift.events == [(D.EVENT_POUR, 4)], "会沉的东西（倒的液体、蛋）发的是倒"


def testSeveralItemsFlyInOneAfterAnother():
    drift = D.PotDrift()
    present = [True, True, True, False, False, False]
    drift.arrive([0, 1, 2], starts=[(-4.0, 5.0), None, (3.0, 3.0)])
    assert drift.events == []
    assert drift.arrivals.age[0] == 0.0
    near(drift.arrivals.age[1], -0.16)
    near(drift.arrivals.age[2], -0.32)
    drift.step(0.0, 0.0, present, SURFACE)
    assert [drift.waiting[i] for i in range(3)] == [False, True, True]
    for i in (1, 2):                                             # 等着的：Java 里已经画在圈上
        near(drift.x[i], 8.0 + drift.itemX[i])
        near(drift.y[i], BASE + 0.07 * math.sin(1.3 * i))
    drift.step(0.2, 0.2, present, SURFACE)                       # 第一件飞到一半：t = 0.5，缓动 0.5
    x, z = drift.itemX[0], drift.itemZ[0]
    near(drift.x[0], 8.0 + (x - 4.0) / 2.0)
    near(drift.z[0], 8.0 + (z + 5.0) / 2.0)
    bob = 0.07 * math.sin(0.9 * 0.2)
    near(drift.y[0], BASE + bob + 4.5 + 4.0)                     # lerp(0.5, y + 9, y) + 4 * sin(pi / 2)
    near(drift.pitch[0], 3.0 * math.sin(0.5 * 0.2) + 90.0)       # 额外翻 (1 - 0.5) * 180 度
    assert not drift.waiting[1]
    assert drift.events == []
    order = []
    for k in range(3):
        drift.step(0.2, 0.4 + 0.2 * k, present, SURFACE)
        order.extend(drift.events)
        del drift.events[:]
    assert order == [(D.EVENT_LANDED, 0), (D.EVENT_LANDED, 1), (D.EVENT_LANDED, 2)], order
    drift.step(0.0, 1.0, present, SURFACE)
    near(drift.x[0], 8.0 + drift.itemX[0])                       # 落下以后就在圈上
    near(drift.y[0], BASE + 0.07 * math.sin(0.9 * 1.0))
    assert not drift.arrivals.arriving[0]


def testAnItemTakenOutMidFlightNeverSplashes():
    drift = D.PotDrift()
    present = [True, True, False, False, False, False]
    drift.arrive([0, 1])
    drift.step(0.1, 0.1, present, SURFACE)
    present[1] = False                                           # 第二格被取空了
    for k in range(6):
        drift.step(0.1, 0.2 + 0.1 * k, present, SURFACE)
    assert drift.events == [(D.EVENT_LANDED, 0)]
    assert not drift.arrivals.arriving[1] and not drift.visible[1]
    again = D.PotDrift()
    again.arrive([0, 1])
    again.clear(1)
    again.arrive([3, 4])
    again.reset()
    assert again.events == [] and not any(again.arrivals.arriving)


def testSinkersPourWhenTheirTurnComes():
    drift = D.PotDrift()
    present = [True, False, False, False, False, False]          # 第二件会沉：不浮着，present 为假
    drift.arrive([0, 1], starts=[None, (3.0, -2.0)], sinking=[False, True])
    near(drift.arrivals.age[1], -0.16)
    drift.step(0.1, 0.1, present, SURFACE)
    assert drift.events == []
    drift.step(0.1, 0.2, present, SURFACE)                       # -0.16 + 0.2：轮到它了
    assert drift.events == [(D.EVENT_POUR, 1)]
    assert not drift.arrivals.arriving[1]
    assert (drift.arrivals.startX[1], drift.arrivals.startZ[1]) == (3.0, -2.0), "手从哪出发：事件之后还在"
    del drift.events[:]
    drift.step(0.2, 0.4, present, SURFACE)
    assert drift.events == [(D.EVENT_LANDED, 0)]


def testAnotherOfTheSameSinkerGetsItsOwnHandAndNeverGetsLost():
    # PotBehavior.java:757-763（more / again）、1428-1431：手闲着马上再来一只，忙着就排队，走完再来；手忙着时又放了几回就来几只
    drift = D.PotDrift()
    drift.more(0, False)
    assert drift.events == [(D.EVENT_POUR, 0)], "手闲着：马上再来一只"
    del drift.events[:]
    drift.more(0, True)
    drift.more(0, True)
    assert drift.events == [] and drift.arrivals.again[0] == 2, "手忙着：排着，不丢"
    drift.handDone(0)
    assert drift.events == [(D.EVENT_POUR, 0)] and drift.arrivals.again[0] == 1
    del drift.events[:]
    drift.handDone(0)
    assert drift.events == [(D.EVENT_POUR, 0)] and drift.arrivals.again[0] == 0
    del drift.events[:]
    drift.handDone(0)
    assert drift.events == [], "排的队走完了：手走完就是走完了"


def testAStackThatIsStillWaitingForItsTurnQueuesToo():
    drift = D.PotDrift()
    drift.arrive([0, 1], starts=[None, None], sinking=[True, True])
    assert drift.arrivals.waiting(1)
    del drift.events[:]
    drift.more(1, False)
    assert drift.events == [] and drift.arrivals.again[1] == 1, "还在等轮到自己：当手忙着"
    drift.clear(1)
    assert drift.arrivals.again[1] == 0, "格子空了：排着队的也不来了（PotBehavior.java:734）"
    drift.handDone(1)
    assert drift.events == []


def testFlightCurveIsThePrintedOne():
    arrivals = A.Arrivals(6)
    events = []
    arrivals.begin([0, 1], events, starts=[(4.0, -2.0), None])
    out = [0.0] * 4
    arrivals.blend(0, 1.0, 5.0, 2.0, out)                        # 刚出手：在起点，高 9 px，翻了 180 度
    assert out == [4.0, 14.0, -2.0, 180.0]
    arrivals.age[0] = 0.2
    arrivals.blend(0, 1.0, 5.0, 2.0, out)
    assert out == [2.5, 13.5, 0.0, 90.0]
    arrivals.age[0] = 0.4
    arrivals.blend(0, 1.0, 5.0, 2.0, out)
    near(out[0], 1.0)
    near(out[1], 5.0)
    near(out[2], 2.0)
    near(out[3], 0.0)
    arrivals.blend(1, 1.0, 5.0, 2.0, out)                        # 没给起点：从锅心正上方落下
    near(arrivals.startX[1], 0.0)
    near(arrivals.startZ[1], 0.0)


def testLandingEffects():
    assert A.landingEffects(0, False) == (0.5, 5, 0.5, 0.92, 0.0, 0.8)
    assert A.landingEffects(0, True) == (0.5, 5, 0.5, 0.92, 0.16, 0.8)
    near(A.landingEffects(3, True)[3], 1.01)                      # 音调 0.92 + 0.03 * 格子序号


def testFacingTurnsTheCircleTheOtherWay():
    drift = D.PotDrift()
    drift.setFacing(0.0)
    assert drift.turned == 0.0, "第一次只是记下朝向"
    drift.setFacing(90.0)
    near(drift.turned, -math.pi / 2.0)
    drift.setFacing(90.0)
    near(drift.turned, -math.pi / 2.0)
    drift.setFacing(60.0)
    near(drift.turned, -math.pi / 2.0 + math.pi / 6.0)


def testWakeFollowsHowFastTheItemMoves():
    drift, present = settled(1)
    wakes = []
    time = 0.0
    for _ in range(4):
        time += DT
        drift.step(DT, time, present, SURFACE, swirl=1.0)
        wakes.append(drift.wake[0])
    assert wakes[0] == 0.0, "刚浮上来的第一帧没有上一帧可比"
    near(wakes[1], 0.7, 1.0e-9)                                   # 2.2 * 1.55 = 3.41 px/s：满
    calm, present = settled(1)
    run(calm, present, 1.0)
    assert calm.wake[0] == 0.0, "静水不留尾迹"
    slow, present = settled(1)
    run(slow, present, 0.5, swirl=(0.6 - 0.05) / 1.5)             # 转速 0.6 rad/s -> 1.32 px/s
    near(slow.wake[0], 0.7 * (1.32 - 0.4) / 1.6, 1.0e-3)
    flying = D.PotDrift()
    flying.arrive([0, 1])
    present = [True, True, False, False, False, False]
    for k in range(3):
        flying.step(0.05, 0.05 * k, present, SURFACE, swirl=1.0)
    assert flying.wake[0] == 0.0 and flying.wake[1] == 0.0, "飞入中的料不留尾迹"


def testExtras():
    assert [X.flatJitter(i) for i in range(6)] == [(i * 7919 % 25 - 12) * 0.7 for i in range(6)]
    near(X.flatJitter(0), -8.4)
    near(X.flatJitter(1), 4.9)
    near(X.flatJitter(4), -7.7)
    assert X.servedAt(6.02) == (8.0, 6.02 + 0.25, 8.0)
    drift, present = settled(2)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=1.0, spoonZ=-1.0, grip=1.0)
    out = X.obstacleList(drift, present)
    assert len(out) == 3 + 2 * 3
    assert out[:3] == [9.0, 7.0, 1.05]                            # 先是勺子（半径 1.05）
    near(out[3], 8.0 + drift.itemX[0])
    near(out[4], 8.0 + drift.itemZ[0])
    assert out[5] == 1.15                                         # 再是每件整料（半径 1.15）
    same = X.obstacleList(drift, present, out)
    assert same is out and len(out) == 9


def testSameScriptSameResultAndNoNaNOnAZeroFrame():
    runs = []
    for _ in range(2):
        rand = lcg(11)
        drift = D.PotDrift()
        present = [True, True, True, True, False, False]
        drift.arrive([0, 1, 2, 3], starts=[(-5.0, 2.0), (4.0, 4.0), None, (0.0, -6.0)])
        time = 0.0
        for k in range(300):
            time += DT
            drift.step(DT, time, present, SURFACE, spoonX=2.0 * math.cos(k * 0.05), spoonZ=2.0 * math.sin(k * 0.05),
                       grip=1.0, swirl=0.8, swirlSign=1.0, rand=rand)
        runs.append((list(drift.x), list(drift.y), list(drift.z), list(drift.yaw), list(drift.pitch), list(drift.events)))
    assert runs[0] == runs[1]
    drift, present = settled(3)
    drift.step(0.0, 0.0, present, SURFACE, spoonX=0.0, spoonZ=0.0, grip=0.0, swirl=0.0)
    for value in drift.x + drift.y + drift.z + drift.yaw + drift.pitch + drift.roll + drift.wake:
        assert value == value, "没有 NaN"
    empty = D.PotDrift()
    empty.step(DT, 0.0, [False] * 6, SURFACE, spoonX=1.0, spoonZ=0.0, grip=0.0)
    assert not any(empty.visible)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
