# -*- coding: utf-8 -*-
# runner: both
"""板上东西的动作（Shared/Rules/HandsOn/BoardMotion.py）：缓动和弧、落下 / 拿走 / 弹回 / 拔出 / 融掉 / 弹出 / 最后一刀飘走各在什么时刻在哪里。

对应 HoD 的 BoardBehavior.land / landFromPlayer / taken / pulledOut / bounced / pop 和 Diegesis 的 Tween。
"""
from __future__ import print_function

import fdtest

Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")


def _close(a, b, eps=1.0e-6):
    return abs(a - b) < eps


def _run(mover, seconds, dt=0.01):
    for _ in range(int(round(seconds / dt))):
        mover.update(dt)


def testInOutCubic():
    assert Motion.inOutCubic(0.0) == 0.0 and Motion.inOutCubic(1.0) == 1.0 and _close(Motion.inOutCubic(0.5), 0.5)
    assert _close(Motion.inOutCubic(0.25), 0.0625) and _close(Motion.inOutCubic(0.75), 0.9375)
    assert Motion.inOutCubic(-1.0) == 0.0 and Motion.inOutCubic(2.0) == 1.0


def testLayersLieAskewByTheirNumberAndNeverTwoTheSame():
    assert Motion.layerTurn(0) == 0.0
    turns = [Motion.layerTurn(layer) for layer in range(9)]
    assert all(abs(turn) <= 15.0 * 1.1 + 1e-9 for turn in turns) and len(set(turns)) >= 7
    assert Motion.layerJitter(1) == Motion.layerJitter(1), "固定的：刷新不会跳"
    assert all(abs(v) <= 3 * 0.12 + 1e-9 for layer in range(9) for v in Motion.layerJitter(layer))
    assert _close(Motion.layerTurn(1), ((7919 % 31) - 15) * 1.1) and Motion.layerJitter(0) == (-0.36, -0.36)


def testTheHeightOfWhatLiesThere():
    assert _close(Motion.itemHeight(1), 0.625) and _close(Motion.itemHeight(2), 0.625 + 0.65), "一叠不止一个：上面那个抬高 0.65"
    assert Motion.itemHeight(5, isBlock=True) == 5.2


def testAMoveEasesAndAHopAddsAnArc():
    mover = Motion.Mover(0.0, 0.0, 0.0)
    mover.move(10.0, 4.0, -2.0, 1.0)
    _run(mover, 0.5)
    assert _close(mover.pos[0], 5.0, 1e-4) and _close(mover.pos[1], 2.0, 1e-4) and _close(mover.pos[2], -1.0, 1e-4), "一半时间走了一半路"
    _run(mover, 0.5)
    assert mover.pos == (10.0, 4.0, -2.0) and not mover.moving
    mover.move(0.0, 4.0, -2.0, 1.0, hop=2.0)
    _run(mover, 0.5)
    assert _close(mover.pos[1], 6.0, 1e-4), "中间多出 hop 高"
    _run(mover, 0.5)
    assert _close(mover.pos[1], 4.0, 1e-9)
    mover.move(1.0, 1.0, 1.0)
    assert mover.pos == (1.0, 1.0, 1.0), "0 秒是跳过去"


def testAfterRunsWhenItsTimeComesAndNotBefore():
    mover = Motion.Mover()
    log = []
    mover.after(0.2, lambda: log.append("late"))
    mover.after(0.1, lambda: log.append("early"))
    _run(mover, 0.09)
    assert log == []
    _run(mover, 0.03)
    assert log == ["early"]
    _run(mover, 0.2)
    assert log == ["early", "late"]


def testAStackLetGoLandsInTwoTenthsSettlesAndStops():
    mover = Motion.Mover(visible=False)
    home = (0.0, 0.0, 0.0)
    Motion.land(mover, home, (3.0, 3.0, 4.0))
    assert mover.visible and mover.pos == (3.0, 3.0, 4.0), "从光标上方出发"
    _run(mover, 0.2)
    assert _close(mover.pos[1], 0.0, 1e-3) and abs(mover.pos[0]) < 1e-3, "0.2 秒落到位"
    _run(mover, 0.01)
    assert mover.pos[1] > 0.0, "再弹一下"
    _run(mover, 0.12)
    assert mover.pos == (0.0, 0.0, 0.0) or all(abs(v) < 1e-9 for v in mover.pos)
    assert not mover.moving


def testLayersFromTheBookFlyInFromThePlayer():
    mover = Motion.Mover()
    Motion.landFromPlayer(mover, (0.0, 1.3, 0.0), (0.0, -14.0))
    assert mover.pos == (0.0, 1.3 + Motion.DROP_HEIGHT, -14.0)
    _run(mover, Motion.PLAYER_LAND_TIME)
    assert all(abs(a - b) < 1e-3 for a, b in zip(mover.pos, (0.0, 1.3, 0.0)))


def testWhatIsTakenLiftsMeltsAndVanishes():
    mover = Motion.Mover()
    Motion.lift(mover, (1.0, 2.0, 3.0))
    _run(mover, 0.1)
    assert _close(mover.pos[1], 2.0 + 2.5, 1e-4) and mover.visible and mover.scale == 1.0
    _run(mover, 0.22)                                       # 0.1 秒到点后下一步才起（步长 0.01 的累加差一点点），再走 0.2 秒
    assert _close(mover.pos[1], 2.0 + 2.5 + 1.0, 1e-4) and mover.scale == 0.0
    _run(mover, 0.02)
    assert not mover.visible, "0.1 + 0.2 秒后不见"


def testWhatTheBoardRefusesComesDownAndBouncesBackToTheHand():
    mover = Motion.Mover()
    hand = (4.0, 6.0, -3.0)
    Motion.bounce(mover, 1.0, hand)
    assert mover.pos == hand
    _run(mover, Motion.BOUNCE_DOWN)
    assert all(abs(a - b) < 1e-9 for a, b in zip(mover.pos, (1.2, 1.0, -0.9))), "落到板顶（离手的水平位置 0.3 倍处）"
    _run(mover, Motion.BOUNCE_UP + 0.001)
    assert all(abs(a - b) < 1e-3 for a, b in zip(mover.pos, hand)) and not mover.visible


def testAToolStuckInTheBoardIsPulledOut():
    mover = Motion.Mover()
    Motion.pullOut(mover, (8.0, Motion.CARVED_Y, 8.0))
    _run(mover, Motion.PULL_TIME)
    assert _close(mover.pos[1], Motion.CARVED_Y + 5.0, 1e-4)
    _run(mover, Motion.AWAY_TIME + 0.01)
    assert not mover.visible and mover.scale == 0.0 and _close(Motion.CARVED_Y, 0.23 * 16.0 - 1.01)


def testLayersMeltIntoTheDishAndTheDishPopsUp():
    layer = Motion.Mover(1.0, 1.95, -1.0)
    Motion.melt(layer, (1.0, 1.95, -1.0))
    _run(layer, Motion.MELT_TIME)
    assert _close(layer.scale, 0.1, 1e-6) and _close(layer.pos[0], 0.4) and _close(layer.pos[1], 1.95 * 0.08) and _close(layer.pos[2], -0.4)
    dish = Motion.Mover()
    Motion.popUp(dish, (0.0, 0.0, 0.0))
    assert dish.scale == 0.3
    _run(dish, 0.175)
    assert dish.pos[1] > 1.0, "弹起来 1.6 像素的弧"
    _run(dish, 0.18)
    assert dish.scale == 1.0 and all(abs(v) < 1e-9 for v in dish.pos)


def testTheLastCutLiftsTheCutFoodAwayAndShrinksIt():
    mover = Motion.Mover()
    Motion.floatAway(mover, (0.0, 0.0, 0.0))
    _run(mover, 0.25)
    assert _close(mover.pos[1], 2.5, 1e-4) and mover.scale == 0.0
    _run(mover, 0.01)
    assert not mover.visible


def testTheStrippedLogRisesThreePixelsAndShrinksAwayInThreeTenthsOfASecond():
    mover = Motion.Mover()
    Motion.stripAway(mover, (0.0, 0.0, 0.0))
    assert mover.visible and mover.scale == 1.0 and mover.pos == (0.0, 0.0, 0.0)
    _run(mover, 0.15)
    assert 1.0 < mover.pos[1] < 2.0 and 0.2 < mover.scale < 0.8, "走到一半"
    _run(mover, 0.15)
    assert _close(mover.pos[1], 3.0, 1e-4) and mover.scale == 0.0 and Motion.STRIP_RISE == 3.0 and Motion.STRIP_TIME == 0.3
    _run(mover, 0.01)
    assert not mover.visible
    tall = Motion.Mover()
    Motion.stripAway(tall, (0.0, 0.5, 0.0), 2.6)
    _run(tall, 0.3)
    assert _close(tall.pos[1], 0.5 + 3.0 + 2.6, 1e-4), "立着的东西绕底边缩：底边多升一个中心的高，缩到点时就在升了 3 像素的中心上"


def testTheLayersHopInPlaceWhenTheyAddUpToADish():
    mover = Motion.Mover(0.1, 1.3, -0.2)
    Motion.settle(mover, (0.1, 1.3, -0.2))
    _run(mover, Motion.SETTLE_TIME / 2.0)
    assert _close(mover.pos[1], 1.3 + Motion.SETTLE_HOP, 0.02), "弧的最高点：SETTLE_HOP 0.25"
    _run(mover, Motion.SETTLE_TIME / 2.0 + 0.01)
    assert all(_close(a, b, 1e-6) for a, b in zip(mover.pos, (0.1, 1.3, -0.2))), "落回原位"
    assert Motion.SETTLE_TIME == 0.12 and Motion.SETTLE_HOP == 0.25


def testAShovelfulShrinksABlockByFourteenPercentAndNothingElseDoes():
    assert Motion.wornScale(True, 0) == 1.0 and _close(Motion.wornScale(True, 1), 0.86) and _close(Motion.wornScale(True, 3), 0.58)
    assert Motion.wornScale(False, 5) == 1.0, "斧、镐不缩（它们是换裂纹，这里不画）"
    assert Motion.wornScale(True, -2) == 1.0, "坏数据不放大"


def testAShakeIsRandomInEveryDirectionAndDiesAwayLinearly():
    ones, zeros = (lambda: 1.0), (lambda: 0.5)
    assert Motion.shakeOffset(0.25, 0.12, 0.12, ones) == (0.25, 0.25, 0.25), "刚抖时：±幅度"
    assert all(_close(v, 0.125) for v in Motion.shakeOffset(0.25, 0.12, 0.06, ones)), "过了一半：幅度减半"
    assert Motion.shakeOffset(0.25, 0.12, 0.06, zeros) == (0.0, 0.0, 0.0), "随机数在中间：没有偏移"
    assert Motion.shakeOffset(0.25, 0.12, 0.0, ones) == (0.0, 0.0, 0.0), "抖完了回到原位"
    assert Motion.shakeOffset(0.25, 0.12, 0.12, lambda: 0.0) == (-0.25, -0.25, -0.25)
    assert Motion.SHAKE_PIXELS == 0.25 and Motion.SHAKE_SECONDS == 0.12


def testARotationEasesEachAngleFromWhereItIsAndStartsFromNothingTurned():
    """Diegesis NodeInstance.rotateTo：三个角各自从现在的值缓动到目标（inOutCubic）；没转过的东西（rotation 是 None，画的人按默认朝向摆）从 (0, 0, 0) 起。"""
    mover = Motion.Mover()
    assert mover.rotation is None and not mover.moving
    mover.rotateTo(40.0, 90.0, -20.0, 1.0)
    assert mover.rotation == (0.0, 0.0, 0.0) and mover.moving and mover.busy
    _run(mover, 0.5)
    assert all(_close(a, b, 1e-4) for a, b in zip(mover.rotation, (20.0, 45.0, -10.0))), "一半时间走了一半"
    _run(mover, 0.5)
    assert mover.rotation == (40.0, 90.0, -20.0) and not mover.moving
    mover.rotateTo(0.0, 0.0, 0.0, 1.0)
    _run(mover, 0.25)
    assert all(_close(a, b, 1e-4) for a, b in zip(mover.rotation, (40.0 * (1 - 0.0625), 90.0 * (1 - 0.0625), -20.0 * (1 - 0.0625)))), "从现在的值（不是从头）走，慢起"
    mover.rotateTo(1.0, 2.0, 3.0)
    assert mover.rotation == (1.0, 2.0, 3.0) and not mover.moving, "0 秒是转过去"
    mover.unturn()
    assert mover.rotation is None and not mover.moving, "回到没转过"


def testARotationInTheMiddleOfAMoveRunsBesideItAndEitherKeepsTheMoverBusy():
    mover = Motion.Mover()
    mover.move(1.0, 0.0, 0.0, 0.1)
    mover.rotateTo(0.0, 30.0, 0.0, 0.3)
    _run(mover, 0.1)
    assert mover.pos == (1.0, 0.0, 0.0) and mover.moving, "位置走完了，转角还在走"
    _run(mover, 0.25)
    assert mover.rotation == (0.0, 30.0, 0.0) and not mover.moving


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
