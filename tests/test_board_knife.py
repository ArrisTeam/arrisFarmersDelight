# -*- coding: utf-8 -*-
# runner: both
"""砧板上的刀（Shared/Rules/HandsOn/BoardKnife.py）：跟光标、吸附到下一刀的线、点一下算什么、落刀的高低、点下去等服务端回话。

对应 HoD 的 BoardBehavior.moveKnife / chop / onStateChanged 的 pendingChops 记账 / PENDING_WAIT，和 BoardTests 里
anIgnoredChopIsAnswered、anotherCookKeepsTheMarks 这类"服务端不收就要撤回"的断言。
"""
from __future__ import print_function

import math

import fdtest

Knife = fdtest.load("Shared.Rules.HandsOn.BoardKnife")
Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")

TOP = 0.625                    # 食物顶面离板面多高（10 像素 / 16）


def _close(a, b, eps=1.0e-6):
    return abs(a - b) < eps


def _settled(knife, over, cut, steps=120, dt=1.0 / 60.0, index=0, top=TOP):
    pose = None
    for _ in range(steps):
        pose = knife.frame(dt, over, cut, index, top)
    return pose


def testTheKnifeFollowsTheCursorByAnExponentialCatchUp():
    knife = Knife.Knife()
    knife.x, knife.z, knife.y = 0.0, 0.0, TOP + Knife.HOVER
    pose = knife.frame(1.0 / 60.0, (3.0, 0.0), None, -1, TOP)
    assert _close(pose[0], 3.0 * (1.0 - math.exp(-22.0 / 60.0))), "每帧挪 1 - exp(-22 dt) 的距离"
    assert knife.overMark == -1 and knife.shown
    pose = _settled(knife, (3.0, -2.0), None)
    assert _close(pose[0], 3.0, 1e-3) and _close(pose[2], -2.0, 1e-3), "停下来就在光标上"
    assert _close(pose[1], TOP + Knife.HOVER, 1e-3), "悬在食物顶面上方 2.4"


def testNearTheNextMarkTheKnifeSnapsOntoItAndTurnsAlongIt():
    cut = Marks.Cut(0.0, 1.0, 0.3)                      # 过 (0, 1)、斜 0.3 弧度的线
    knife = Knife.Knife()
    pose = _settled(knife, (2.0, 1.0 + math.tan(0.3) * 2.0 + 1.0), cut)     # 光标在线外 1 / cos 的地方：离线 1.0 < 1.4
    assert knife.overMark == 0, "离线 1.4 以内：吸附"
    assert abs(cut.distance(pose[0], pose[2])) < 1e-3, "刀站到线上"
    assert _close(pose[3], 0.3), "刀顺着这一刀的角度"
    far = Knife.Knife()
    _settled(far, (2.0, 1.0 + math.tan(0.3) * 2.0 + 3.0), cut)
    assert far.overMark == -1, "离线 3 像素：不吸附"
    assert abs(cut.distance(far.x, far.z) - 3.0 * math.cos(0.3)) < 0.05, "刀就在光标那里"


def testTheIndexOfTheMarkItIsSnappedToIsWhatIsSent():
    cut = Marks.Cut(0.0, 0.0, 0.0)
    knife = Knife.Knife()
    _settled(knife, (1.0, 0.5), cut, index=2)
    assert knife.overMark == 2
    assert knife.click((1.0, 0.5)) == (Knife.CHOP, 2, knife.z), "点在线上：发第 2 刀，带刀刃的 z"


def testAClickOffTheLineOnlyKnocksAndNothingIsSent():
    knife = Knife.Knife()
    _settled(knife, (0.0, 3.0), Marks.Cut(0.0, 0.0, 0.0))
    assert knife.overMark == -1
    assert knife.click((0.0, 3.0)) == (Knife.KNOCK,)
    assert knife.chopping, "敲也要落一下"


def testNoClickOffTheItemOrWhileTheKnifeIsStillComingDown():
    knife = Knife.Knife()
    _settled(knife, (0.0, 0.0), Marks.Cut(0.0, 0.0, 0.0))
    assert knife.click(None) is None, "光标不在食物上：什么也不是"
    assert knife.click((0.0, 0.0))[0] == Knife.CHOP
    assert knife.click((0.0, 0.0)) is None, "这一刀还没落完，不能再点"
    knife.frame(0.3, (0.0, 0.0), Marks.Cut(0.0, 0.0, 0.0), 0, TOP)
    assert not knife.chopping
    assert knife.click((0.0, 0.0)) is not None, "落完了又能点"


def testTheKnifeGoesDownFiveHundredthsAndUpFourteenHundredths():
    knife = Knife.Knife()
    cut = Marks.Cut(0.0, 0.0, 0.0)
    _settled(knife, (0.0, 0.0), cut)
    hover = knife.y
    knife.click((0.0, 0.0))
    pose = knife.frame(0.025, (0.0, 0.0), cut, 0, TOP)
    assert _close(pose[1], hover + (TOP - hover) * 0.5, 1e-6), "0.025 秒：下去一半"
    pose = knife.frame(0.025, (0.0, 0.0), cut, 0, TOP)
    assert _close(pose[1], TOP, 1e-6), "0.05 秒：刀刃到食物顶面"
    pose = knife.frame(0.07, (0.0, 0.0), cut, 0, TOP)
    assert _close(pose[1], TOP + (hover - TOP) * 0.5, 1e-6), "起来的一半"
    pose = knife.frame(0.08, (0.0, 0.0), cut, 0, TOP)
    assert _close(pose[1], hover, 1e-6) and not knife.chopping, "0.19 秒落完"


def testNoKnifeToOfferMeansNothingIsDrawn():
    knife = Knife.Knife()
    assert knife.frame(0.016, (1.0, 1.0), Marks.Cut(0.0, 0.0, 0.0), 0, TOP, haveTool=False) is None
    assert not knife.shown and _close(knife.y, TOP + Knife.HOVER + Knife.REST_HEIGHT), "停在高处等着"
    assert knife.frame(0.016, None, None, -1, TOP) is None, "光标不在食物上也不画"


def testAChopInTheAirIsDrawnToTheEndEvenIfTheCursorLeaves():
    knife = Knife.Knife()
    cut = Marks.Cut(0.0, 0.0, 0.0)
    _settled(knife, (0.0, 0.0), cut)
    knife.click((0.0, 0.0))
    assert knife.frame(0.01, None, cut, 0, TOP) is not None, "落刀中光标挪开：照样画完"
    knife.frame(0.3, None, cut, 0, TOP)
    assert knife.frame(0.01, None, cut, 0, TOP) is None


def testPendingChopsAreDrawnAtOnceAndAnsweredOneByOne():
    pending = Knife.Pending()
    assert pending.next(0, 2) == 0 and pending.made(0, 2) == 0
    pending.add(5.0)
    assert pending.next(0, 2) == 1 and pending.made(0, 2) == 1, "点下去马上画成切开，下一刀已经是第 1 刀"
    pending.add(5.1)
    assert pending.next(0, 2) == -1 and pending.made(0, 2) == 2
    pending.state(1)
    assert pending.count == 1, "服务端说切了一刀：回了一刀"
    pending.state(2)
    assert pending.count == 0, "全回了"


def testABoardChangeOrAMarkCountGoingBackCancelsThem():
    pending = Knife.Pending()
    pending.state(1)
    pending.add(0.0)
    pending.state(1, boardChanged=True)
    assert pending.count == 0, "板上换了东西（别人放了层、漏斗取走）：作废"
    pending.state(2)
    pending.add(0.0)
    pending.state(0)
    assert pending.count == 0, "刀数倒退（重布刀口）：作废"
    pending.state(0)
    pending.add(0.0)
    pending.state(0)
    assert pending.count == 1, "没变：还在等"


def testARefusedChopOrASilentServerTakesTheCutBack():
    pending = Knife.Pending()
    pending.add(2.0)
    assert pending.refused() and pending.count == 0
    assert not pending.refused()
    pending.add(2.0)
    assert not pending.expire(2.9) and pending.count == 1, "1 秒之内还等"
    assert pending.expire(3.1) and pending.count == 0, "超过 1 秒没回话：撤回"
    assert not pending.expire(9.0)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
