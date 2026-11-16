# -*- coding: utf-8 -*-
# runner: both
"""PotSpoonMotion / PotSpoonPose（厨锅勺子）的测试。数字来自 Hands-On Delight 的 client/PotBehavior.java
（moveSpoon 1292-1346、stirEffects 1349-1372、pose 1375-1392、点按 466-488）与 cooking_pot.json 的 ladle 节点。"""
from __future__ import print_function

import math

import fdtest

S = fdtest.load("Shared.Rules.HandsOn.PotSpoonMotion")
P = fdtest.load("Shared.Rules.HandsOn.PotSpoonPose")


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def apply(m, v):
    return (m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2])


def inHand(tipX, tipZ):
    """一把已经握在手里、勺尖在 (tipX, tipZ) 的勺子（grip = 1）。"""
    spoon = S.PotSpoonMotion()
    spoon.tipX, spoon.tipZ, spoon.grip = tipX, tipZ, 1.0
    return spoon


def testRestPoseIsTheModelsOwnLean():
    spoon = S.PotSpoonMotion()
    assert (S.REST_LEAN, S.STIR_LEAN, S.SPOON_END, S.SPOON_REACH) == (22.5, 7.0, 3.0, 2.3)
    near(P.restSlope(), math.tan(math.radians(22.5)))
    near(P.restSlope(), 0.41421356237, 1.0e-9)
    near(spoon.axisX, math.sin(math.radians(22.5)))
    near(spoon.axisY, math.cos(math.radians(22.5)))
    near(spoon.axisZ, 0.0)
    assert spoon.rot == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0], "静止时模型不用再转"
    assert spoon.euler() == (0.0, 0.0, 0.0)
    assert spoon.offset() == (0.0, 0.0, 0.0)
    assert spoon.matrix() == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    assert (spoon.tipX, spoon.tipZ, spoon.grip, spoon.swirl, spoon.swirlSign) == (0.0, 0.0, 0.0, 0.0, 1.0)
    near(P.restSlope(-22.5), -0.41421356237, 1.0e-9)            # 酒瓶锅的勺子歪向另一边
    assert S.PotSpoonMotion(restLean=-22.5).axisX < 0.0


def testHandleTopLeansAboutFivePixelsOverAtRest():
    spoon = S.PotSpoonMotion()
    near(12.0 * spoon.leanX, 4.9705627485, 1.0e-6)              # 手柄顶（高 12 px）在 +x 方向偏 ~4.97 px
    near(spoon.throughX, 0.41421356237 * (5.77 - 3.0), 1.0e-9)   # 空锅水面 5.77，勺尖高 3：穿过点
    near(spoon.throughZ, 0.0)


def testPickBoxIsTheSceneColliderAtRestAndFollowsThePose():
    # cooking_pot.json:52-63：[2.6,11.5,-1.5]-[6.6,16,1.5]
    assert S.PICK_LO == (2.6, 11.5, -1.5) and S.PICK_HI == (6.6, 16.0, 1.5)
    spoon = S.PotSpoonMotion()
    assert spoon.pickAabb() == ((2.6, 11.5, -1.5), (6.6, 16.0, 1.5))
    spoon.tipX, spoon.tipZ = 1.0, -1.0
    spoon.step(0.016, 0.0, True, True, aim=(1.0, -1.0))
    lo, hi = spoon.pickAabb()
    matrix = spoon.matrix()
    for corner in ((2.6, 11.5, -1.5), (6.6, 16.0, 1.5), (2.6, 16.0, 1.5), (6.6, 11.5, -1.5)):
        world = [matrix[axis] * corner[0] + matrix[3 + axis] * corner[1] + matrix[6 + axis] * corner[2] + matrix[9 + axis] for axis in range(3)]
        for axis in range(3):
            assert lo[axis] - 1.0e-9 <= world[axis] <= hi[axis] + 1.0e-9, "包围盒要把定向盒的角都装下"


def testTargetIsClampedToTheReach():
    spoon = S.PotSpoonMotion()
    spoon.step(0.05, 0.0, True, True, aim=(10.0, 0.0))
    near(spoon.tipX, 2.3 * (1.0 - math.exp(-0.05 * 18.0)))      # 目标夹到 2.3 px，跟手速度 18
    near(spoon.tipZ, 0.0)
    inside = S.PotSpoonMotion()
    inside.step(0.05, 0.0, True, True, aim=(1.0, 1.0))
    near(inside.tipX, 1.0 - 1.0 * math.exp(-0.9))               # 在够得到的范围里不夹
    far = S.PotSpoonMotion()
    for _ in range(300):
        far.step(0.05, 0.0, True, True, aim=(30.0, 40.0))
    near(math.hypot(far.tipX, far.tipZ), 2.3, 1.0e-6)
    near(far.tipX / far.tipZ, 0.75, 1.0e-6)


def testHandWithoutACursorHitGoesToTheMiddle():
    spoon = inHand(2.0, 0.0)
    spoon.step(0.05, 0.0, True, True, aim=None)                 # PB:1298-1309：射线没打到液面，目标是 (0, 0)
    near(spoon.tipX, 2.0 * math.exp(-0.9))


def testFollowsTheSyncedSpoonWhenSomeoneElseStirs():
    spoon = S.PotSpoonMotion()
    spoon.step(0.1, 0.0, False, True, synced=(1.0, 0.0))
    near(spoon.tipX, 2.3 * (1.0 - math.exp(-0.1 * 9.0)))        # 跟同步的速度 9，目标 spoon_x * 2.3
    near(spoon.grip, 0.7)                                       # grip 往 1 走：lerp(min(1, 0.1 * 7), 0, 1)
    spoon.step(0.1, 0.1, False, True, synced=(0.0, -1.0))
    assert spoon.tipZ < 0.0 and spoon.grip > 0.7
    nobody = S.PotSpoonMotion()
    nobody.step(0.1, 0.0, False, True, synced=None)
    near(nobody.tipX, 0.0)


def testSpoonStaysWhereTheHandLeftItForTwoAndAHalfSeconds():
    spoon = S.PotSpoonMotion()
    for _ in range(20):
        spoon.step(0.05, 0.0, True, True, aim=(2.0, 0.0))
    spoon.step(0.05, 1.0, False, True, synced=(-1.0, 0.0))
    held = spoon.tipX
    assert held > 1.5
    assert S.HAND_MEMORY == 2.5
    for _ in range(38):                                         # 松手后 1.9 秒：还是自己的
        spoon.step(0.05, 1.0, False, True, synced=(-1.0, 0.0))
    near(spoon.tipX, held, 1.0e-9)
    for _ in range(40):                                         # 再过 2 秒（共约 3.9 秒）：跟同步的走了
        spoon.step(0.05, 1.0, False, True, synced=(-1.0, 0.0))
    assert spoon.tipX < 0.0


def testGoingHomeSetsOffSoftlyAndEasesBackToRest():
    spoon = inHand(2.0, 0.0)
    spoon.step(0.1, 0.0, False, False)
    near(spoon.homing, 0.1 / 0.6)                               # SPOON_HOME_EASE 0.6 秒
    near(spoon.tipX, 2.0 * math.exp(-0.1 * 1.8 * (0.1 / 0.6)))  # 跟随速度 1.8 * homing
    near(spoon.grip, 1.0 + min(1.0, 0.1 * 2.0 * (0.1 / 0.6)) * (0.0 - 1.0))   # grip 往 0 走 2 * homing
    for _ in range(3):
        spoon.step(0.1, 0.0, False, False)
    near(spoon.homing, 4 * 0.1 / 0.6)
    for _ in range(400):
        spoon.step(0.1, 0.0, False, False)
    near(spoon.homing, 1.0)
    assert abs(spoon.tipX) < 1.0e-6 and spoon.grip < 1.0e-6
    near(spoon.axisX, math.sin(math.radians(22.5)), 1.0e-6)
    spoon.step(0.1, 0.0, True, True, aim=(1.0, 0.0))
    near(spoon.homing, 0.0)                                      # 有人握上了，回位进度清零


def testLeanInHandGrowsWithTheDistanceFromTheMiddle():
    # PB:1377-1380：握在手里手柄每升 1 px 偏 tip * tan(7 度) / 2.3，最远处 7 度
    spoon = inHand(2.3, 0.0)
    spoon.step(1.0e-9, 0.0, True, True, aim=(2.3, 0.0))
    near(spoon.leanX, math.tan(math.radians(7.0)), 1.0e-6)
    near(math.degrees(math.atan2(math.hypot(spoon.axisX, spoon.axisZ), spoon.axisY)), 7.0, 1.0e-4)
    half = P.leanSlopes(1.15, 0.0, 1.0)
    near(half[0], math.tan(math.radians(7.0)) / 2.0)
    near(half[1], 0.0)
    near(P.leanSlopes(0.0, 2.3, 1.0)[1], math.tan(math.radians(7.0)))
    mixed = P.leanSlopes(2.3, 0.0, 0.5)                          # 按 grip 从静止混向握着
    near(mixed[0], P.restSlope() + 0.5 * (math.tan(math.radians(7.0)) - P.restSlope()))
    assert P.leanSlopes(2.3, 0.0, 0.0) == (P.restSlope(), 0.0)


def testRotationTakesTheRestAxisToTheLeanAxis():
    # PB:1382：rotationTo(restAxis, leanAxis)，最短弧
    restNorm = math.sqrt(P.restSlope() ** 2 + 1.0)
    rest = (P.restSlope() / restNorm, 1.0 / restNorm, 0.0)
    for tip in ((0.0, 0.0), (2.0, 0.5), (-1.5, 1.2), (0.3, -2.2), (-2.3, 0.0)):
        spoon = inHand(tip[0], tip[1])
        spoon.step(1.0e-9, 0.0, True, True, aim=tip)
        turned = apply(spoon.rot, rest)
        near(turned[0], spoon.axisX, 1.0e-9)
        near(turned[1], spoon.axisY, 1.0e-9)
        near(turned[2], spoon.axisZ, 1.0e-9)
        near(spoon.axisX ** 2 + spoon.axisY ** 2 + spoon.axisZ ** 2, 1.0, 1.0e-12)
        m = spoon.rot                                            # 正交、行列式 1
        near(m[0] * m[0] + m[1] * m[1] + m[2] * m[2], 1.0, 1.0e-12)
        det = (m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6]))
        near(det, 1.0, 1.0e-12)


def testShortestArcFallbackForOppositeVectors():
    m = P.alignMatrix([0.0] * 9, 0.0, 1.0, 0.0, 0.0, -1.0, 0.0)
    assert apply(m, (0.0, 1.0, 0.0)) == (0.0, -1.0, 0.0) or max(abs(a - b) for a, b in zip(apply(m, (0.0, 1.0, 0.0)), (0.0, -1.0, 0.0))) < 1.0e-9
    same = P.alignMatrix([0.0] * 9, 0.3, 0.8, 0.0, 0.3, 0.8, 0.0)
    for got, want in zip(same, [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]):
        near(got, want)


def testEulerAnglesRebuildTheRotationInYxzOrder():
    # JOML getEulerAnglesYXZ：R = Ry(y) * Rx(x) * Rz(z)；节点的 rotateTo(x, y, z) 吃的就是它
    for tip in ((2.0, 0.5), (-1.5, 1.2), (0.3, -2.2)):
        spoon = inHand(tip[0], tip[1])
        spoon.step(1.0e-9, 0.0, True, True, aim=tip)
        x, y, z = [math.radians(a) for a in spoon.euler()]
        cy, sy, cx, sx, cz, sz = math.cos(y), math.sin(y), math.cos(x), math.sin(x), math.cos(z), math.sin(z)
        rebuilt = [cy * cz + sy * sx * sz, -cy * sz + sy * sx * cz, sy * cx,
                   cx * sz, cx * cz, -sx,
                   -sy * cz + cy * sx * sz, sy * sz + cy * sx * cz, cy * cx]
        for got, want in zip(spoon.rot, rebuilt):
            near(got, want, 1.0e-9)


def testNodeOffsetKeepsTheTipAtTheSpoonEnd():
    # PB:1384-1385：moveTo(tip - R * (0, 3, 0))：模型里 (0, 3, 0) 那点转完正好落在 (tipX, 3, tipZ)
    for tip in ((0.0, 0.0), (2.0, 0.5), (-1.5, 1.2)):
        spoon = inHand(tip[0], tip[1])
        spoon.step(1.0e-9, 0.0, True, True, aim=tip)
        pivot = spoon.matrix()
        placed = [pivot[axis] * 0.0 + pivot[3 + axis] * 3.0 + pivot[6 + axis] * 0.0 + pivot[9 + axis] for axis in range(3)]
        near(placed[0], spoon.tipX, 1.0e-9)
        near(placed[1], 3.0, 1.0e-9)
        near(placed[2], spoon.tipZ, 1.0e-9)


def testThroughPointAndTheTurnOfTheScene():
    spoon = inHand(1.0, 0.5)
    spoon.step(1.0e-9, 0.0, True, True, aim=(1.0, 0.5), surfaceY=7.0)
    height = 7.0 - 3.0
    near(spoon.throughX, spoon.tipX + spoon.leanX * height, 1.0e-9)
    near(spoon.throughZ, spoon.tipZ + spoon.leanZ * height, 1.0e-9)
    x, z = spoon.throughX, spoon.throughZ
    turned = inHand(1.0, 0.5)
    turned.step(1.0e-9, 0.0, True, True, aim=(1.0, 0.5), surfaceY=7.0, turn=90.0)
    near(turned.throughX, z, 1.0e-9)                             # JOML rotationY(90 度)：(x, z) -> (z, -x)
    near(turned.throughZ, -x, 1.0e-9)
    for angle in (0.0, 37.0, 90.0, 180.0, -123.0):
        sx, sz = P.toScene(1.3, -0.7, angle)
        lx, lz = P.toLocal(sx, sz, angle)
        near(lx, 1.3, 1.0e-12)
        near(lz, -0.7, 1.0e-12)
    assert P.toScene(1.0, 2.0, 0.0) == (1.0, 2.0)
    near(P.toScene(1.0, 2.0, 180.0)[0], -1.0, 1.0e-12)
    near(P.toScene(1.0, 2.0, 180.0)[1], -2.0, 1.0e-12)


def testSwirlRisesTowardTheSpeedAndDecaysByHalfEveryNinetyMilliseconds():
    # PB:1338-1344：目标 min(1, moved / dt / 7)，只往上涨（速度 2.5/s），每帧乘 0.5^(dt / 0.9)
    assert (S.SWIRL_SPEED, S.SWIRL_RISE, S.SWIRL_HALF_LIFE) == (7.0, 2.5, 0.9)
    decay = inHand(0.0, 0.0)
    decay.swirl = 1.0
    for _ in range(9):
        decay.step(0.1, 0.0, False, True, synced=None)
    near(decay.swirl, 0.5, 1.0e-9)                               # 0.9 秒一半
    spoon = inHand(2.0, 0.0)
    spoon.step(0.1, 0.0, True, True, aim=(2.0 * math.cos(1.0), 2.0 * math.sin(1.0)))
    wanted = min(1.0, spoon.moved / 0.1 / 7.0)
    near(spoon.swirl, wanted * 0.25 * 0.5 ** (0.1 / 0.9), 1.0e-12)   # lerp(min(1, 0.1 * 2.5), 0, wanted) 再衰减
    faster = inHand(0.0, 0.0)
    faster.swirl = 0.9
    faster.step(0.1, 0.0, True, True, aim=(0.0, 0.0))
    near(faster.swirl, 0.9 * 0.5 ** (0.1 / 0.9), 1.0e-12)        # 目标比现在低：不降，只衰减


def testSwirlSignFollowsWhichWayTheHandGoesRound():
    # PB:1328, 1335-1337：叉积 tipX * stepZ - tipZ * stepX 的符号，每秒 1.5 倍地追
    clockwise = inHand(2.0, 0.0)
    clockwise.step(0.1, 0.0, True, True, aim=(2.0 * math.cos(-0.5), 2.0 * math.sin(-0.5)))
    near(clockwise.swirlSign, 1.0 + 0.15 * (-1.0 - 1.0))
    counter = inHand(2.0, 0.0)
    counter.swirlSign = -1.0
    counter.step(0.1, 0.0, True, True, aim=(2.0 * math.cos(0.5), 2.0 * math.sin(0.5)))
    near(counter.swirlSign, -1.0 + 0.15 * 2.0)
    still = inHand(2.0, 0.0)
    still.step(0.1, 0.0, True, True, aim=(2.0, 0.0))
    near(still.swirlSign, 1.0)                                   # 没挪（moved <= 0.02）：转向不变
    outOfSoup = S.PotSpoonMotion()
    outOfSoup.tipX, outOfSoup.grip = 2.0, 0.2
    outOfSoup.step(0.05, 0.0, False, True, synced=(0.0, -1.0))   # grip 才 0.48 <= 0.5：还没进汤，转向、水波、涡流都不起
    assert outOfSoup.swirlSign == 1.0 and outOfSoup.swirl == 0.0 and not outOfSoup.ripple and not outOfSoup.furrow
    outOfSoup.step(0.05, 0.05, False, True, synced=(0.0, -1.0))  # 进汤了（grip 0.72）：顺时针，转向开始往 -1 走
    assert outOfSoup.swirlSign < 1.0 and outOfSoup.furrow
    resting = S.PotSpoonMotion()
    resting.step(0.1, 0.0, False, False)                         # 靠着：grip <= 0.5，什么都不起
    assert not resting.ripple and not resting.furrow and resting.swirl == 0.0


def circle(spoon, frames, dt, radius=2.0, speed=6.0, start=0.0, clock=0.0, hand=True):
    """握着勺子画圆：每帧一个 (ripple, furrow, send)。"""
    seen = []
    angle = start
    for i in range(frames):
        angle += speed * dt
        spoon.step(dt, clock + (i + 1) * dt, hand, True, aim=(radius * math.cos(angle), radius * math.sin(angle)))
        seen.append((spoon.ripple, spoon.furrow, spoon.send))
    return seen


def testRippleEveryNinetyMillisecondsWhileMoving():
    # PB:1353-1358：moved > 0.01 且距上次 >= 0.09 秒
    assert (S.RIPPLE_INTERVAL, S.RIPPLE_STRENGTH, S.RIPPLE_MOVED, S.FURROW_MOVED) == (0.09, 0.17, 0.01, 0.005)
    spoon = inHand(2.0, 0.0)
    seen = circle(spoon, 7, 0.03)
    assert [flags[0] for flags in seen] == [True, False, False, True, False, False, True], seen
    assert all(flags[1] for flags in seen), "每帧都在拖尾迹"
    spoon.step(0.03, 1.0, True, True, aim=(spoon.tipX, spoon.tipZ))
    assert not spoon.ripple and not spoon.furrow, "不动就没有水波和尾迹"
    near(math.hypot(spoon.rippleX, spoon.rippleZ), math.hypot(spoon.tipX, spoon.tipZ), 0.5)


def testFurrowStartsAtThePreviousFramesThroughPoint():
    spoon = inHand(2.0, 0.0)
    spoon.step(0.03, 0.0, True, True, aim=(2.0, 1.0), surfaceY=6.0)
    before = (spoon.throughX, spoon.throughZ)
    spoon.step(0.03, 0.03, True, True, aim=(2.0, 1.5), surfaceY=6.0)
    assert spoon.furrow and (spoon.furrowX, spoon.furrowZ) == before, "stirEffects 在 pose 之前，用的是上一帧的穿过点"


def testSendCadenceAndPayload():
    # PB:1359-1370：握着时每 0.12 秒、至少挪了 0.2 px 才上报；载荷 = 勺尖 / 2.3 与站点的钟
    assert (S.SEND_INTERVAL, S.SEND_TRAVEL) == (0.12, 0.2)
    spoon = inHand(2.0, 0.0)
    seen = []
    last = None
    for i in range(14):
        circle_one = circle(spoon, 1, 0.03, clock=10.0 + i * 0.03, start=0.2 * i)
        seen.append(circle_one[0][2])
        if spoon.send:
            last = (i, spoon.sendX, spoon.sendZ, spoon.sendAt, spoon.tipX, spoon.tipZ)
    sends = [i for i, flag in enumerate(seen) if flag]
    assert len(sends) >= 3 and sends[0] <= 1, "第一次最迟第二帧：挪够 0.2 px 就报"
    assert all(b - a == 4 for a, b in zip(sends, sends[1:])), "之后每 0.12 秒（0.03 * 4）一次：%r" % (sends,)
    near(last[1], last[4] / 2.3)
    near(last[2], last[5] / 2.3)
    near(last[3], 10.0 + last[0] * 0.03 + 0.03)
    slow = inHand(2.0, 0.0)
    flags = circle(slow, 40, 0.03, radius=2.0, speed=0.6)        # 慢慢蹭（0.036 px 一帧）：不是 0.12 秒到了就报，要 0.2 px 攒够
    sends = [i for i, f in enumerate(flags) if f[2]]
    assert sends[:3] == [6, 12, 18], sends
    watcher = inHand(2.0, 0.0)
    assert not any(f[2] for f in circle(watcher, 20, 0.03, hand=False)), "不是本人握着：不上报"


def testGestureClickKeepsTheSpoonUntilTheNextClick():
    # PB:466-488：按下 -> 抬起 < 0.3 秒 = 点，勺子留在手里；下一次按下放下，随后的抬起不算
    gesture = S.SpoonGesture()
    assert S.SPOON_CLICK == 0.3
    assert gesture.down(1.0) is True and gesture.stroking
    assert gesture.up(1.2) is True and gesture.heldByClick and gesture.stroking
    assert gesture.up(1.5) is False and gesture.stroking, "留在手里时的抬起不改变什么"
    assert gesture.down(2.0) is False and not gesture.stroking and not gesture.heldByClick
    assert gesture.up(2.1) is False and not gesture.stroking
    assert gesture.down(3.0) is True


def testGestureDragEndsOnRelease():
    gesture = S.SpoonGesture()
    gesture.down(5.0)
    assert gesture.up(5.5) is False and not gesture.stroking and not gesture.heldByClick
    edge = S.SpoonGesture()
    edge.down(0.0)
    assert edge.up(0.3) is False, "正好 0.3 秒不算点（Java 是 < 0.3）"
    quick = S.SpoonGesture()
    quick.down(0.0)
    assert quick.up(0.29) is True
    quick.reset()
    assert not quick.stroking and not quick.heldByClick
    never = S.SpoonGesture()
    assert never.up(1.0) is False


def testZeroFrameIsHarmless():
    spoon = inHand(1.0, 1.0)
    spoon.step(0.0, 0.0, True, True, aim=(2.0, 0.0))
    assert spoon.tipX == 1.0 and spoon.tipZ == 1.0
    assert not (spoon.ripple or spoon.send)
    for value in (spoon.axisX, spoon.axisY, spoon.axisZ, spoon.throughX, spoon.throughZ, spoon.swirl):
        assert value == value, "没有 NaN"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
