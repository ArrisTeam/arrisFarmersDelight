# -*- coding: utf-8 -*-
# runner: both
"""刀以外的工具（Shared/Rules/HandsOn/BoardStroke.py）：落点和全长、各个动作量在每一段接得上、二维姿态、方块上的落点、剪刀的起止。

对应 HoD 的 ToolStroke（pose / raise / ease）和 BoardBehavior.aim / workHeight / startStroke / moveTool。
"""
from __future__ import print_function

import math

import fdtest

Stroke = fdtest.load("Shared.Rules.HandsOn.BoardStroke")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")
Mth = fdtest.load("Shared.Rules.HandsOn.Mth")

KINDS = (Cutting.TOOL_CHOP, Cutting.TOOL_STRIP, Cutting.TOOL_SMASH, Cutting.TOOL_DIG, Cutting.TOOL_PRY, Cutting.TOOL_SNIP)


def _close(a, b, eps=1.0e-9):
    return abs(a - b) < eps


def testEaseIsSmoothstep():
    assert Stroke.ease(0.0) == 0.0 and Stroke.ease(1.0) == 1.0 and _close(Stroke.ease(0.5), 0.5) and _close(Stroke.ease(0.25), 0.15625)
    assert Stroke.ease(-3.0) == 0.0 and Stroke.ease(9.0) == 1.0


def testSwingGoesBackThenDownToTheWorkThenHoldsAndComesUp():
    kind = Cutting.TOOL_CHOP                                  # 落点 0.19、全长 0.42；抬到 0.95 用 0.13 秒，压到 0.24 秒
    assert _close(Stroke.swing(kind, 0.0, 0.3, 0.95, 0.13, 0.24), 0.3), "开头是悬着的角度"
    assert _close(Stroke.swing(kind, 0.13, 0.3, 0.95, 0.13, 0.24), 0.95), "往后抬到最高"
    assert _close(Stroke.swing(kind, 0.19, 0.3, 0.95, 0.13, 0.24), 0.0), "到落点碰上了"
    assert _close(Stroke.swing(kind, 0.22, 0.3, 0.95, 0.13, 0.24), 0.0), "压着"
    assert _close(Stroke.swing(kind, 0.42, 0.3, 0.95, 0.13, 0.24), 0.3), "最后回到悬着"
    mid = Stroke.swing(kind, 0.16, 0.3, 0.95, 0.13, 0.24)
    assert 0.0 < mid < 0.95 and _close(mid, 0.95 * (1.0 - (0.03 / 0.06) ** 2)), "往下是加速的（t 的平方）"


def testEveryMotionIsContinuousWhereItsPartsMeet():
    for kind in KINDS:
        impact, length = Stroke.timesOf(kind)
        for age in (0.06, 0.07, 0.08, 0.1, 0.13, 0.14, 0.22, 0.24, impact, length):
            a = Stroke.motion(kind, age - 1e-9, 5.0, -2.0, 2.0)
            b = Stroke.motion(kind, age + 1e-9, 5.0, -2.0, 2.0)
            for key in ("raise", "lever", "push", "slide", "along", "bite"):
                assert abs(a[key] - b[key]) < 2e-3, (kind, age, key, a[key], b[key])
    assert Stroke.motion(Cutting.TOOL_STRIP, None, 5.0)["slide"] == 1.0
    assert abs(Stroke.motion(Cutting.TOOL_STRIP, 0.27, 5.0)["slide"] + 3.4) < 1e-9, "削皮：从 1 下到 -(顶 - 1.6)，那是它的整个行程"
    assert abs(Stroke.motion(Cutting.TOOL_STRIP, 0.42, 5.0)["slide"] - 1.0) < 1e-9, "再回到 1"


def testTheShovelPushesInLeversAndPullsBack():
    waiting = Stroke.motion(Cutting.TOOL_DIG, None)
    assert waiting["push"] == -1.5 and waiting["lever"] == 0.0, "悬着：退在土堆边上"
    assert _close(Stroke.motion(Cutting.TOOL_DIG, 0.1)["push"], 2.0), "0.1 秒插到底"
    assert _close(Stroke.motion(Cutting.TOOL_DIG, 0.22)["lever"], 0.5), "0.22 秒撬到最大"
    done = Stroke.motion(Cutting.TOOL_DIG, 0.38)
    assert _close(done["push"], -1.5) and _close(done["lever"], 0.0)


def testTheHoeHooksLeversAndLifts():
    assert Stroke.motion(Cutting.TOOL_PRY, None)["raise"] == 0.35
    hooked = Stroke.motion(Cutting.TOOL_PRY, 0.08)
    assert hooked["raise"] == 0.0 and hooked["lever"] == 0.0
    levered = Stroke.motion(Cutting.TOOL_PRY, 0.24)
    assert _close(levered["lever"], 0.45) and all(_close(a, b) for a, b in zip(levered["offset"], (0.0, 0.5, -0.4)))
    assert _close(Stroke.motion(Cutting.TOOL_PRY, 0.40)["raise"], 0.35), "最后回到悬着"


def testTheShearsComeToTheLineSnipThreeTimesAndGoBack():
    kind = Cutting.TOOL_SNIP
    assert Stroke.motion(kind, None, 0.0, -2.0, 2.0)["along"] == 0.0
    assert _close(Stroke.motion(kind, 0.06, 0.0, -2.0, 2.0)["along"], -2.0), "0.06 秒到线头"
    assert _close(Stroke.motion(kind, 0.36 - 1e-9, 0.0, -2.0, 2.0)["along"], 2.0, 1e-6), "三口剪完到线尾"
    assert _close(Stroke.motion(kind, 0.46, 0.0, -2.0, 2.0)["along"], 0.0), "退回"
    assert Stroke.motion(kind, 0.11, 0.0, -2.0, 2.0)["bite"] > 0.0 and Stroke.motion(kind, 0.06, 0.0, -2.0, 2.0)["bite"] == 0.0


def testAChopRunSendsItsBlowAtTheImpactOnce():
    run = Stroke.Run(Cutting.TOOL_CHOP, 0)
    assert run.step(0.1) == [] and run.step(0.08) == []
    assert run.step(0.02) == ["impact"], "0.19 秒"
    assert run.step(0.1) == [] and run.step(0.2) == ["done"], "0.42 秒完"
    assert run.sent


def testAShearsRunIsHeardTwiceBeforeTheCut():
    run = Stroke.Run(Cutting.TOOL_SNIP, 0)
    heard = []
    for _ in range(50):
        heard += run.step(0.01)
    assert heard.count("snip") == 2 and heard.count("impact") == 1 and heard[-1] == "done", heard
    assert heard.index("snip") < heard.index("impact")


def testTheWorkingPointLandsOnTheTargetWhenTheHeadIsDown():
    for kind, age in ((Cutting.TOOL_CHOP, 0.19), (Cutting.TOOL_SMASH, 0.19), (Cutting.TOOL_PRY, 0.08)):
        posed = Stroke.pose(kind, age, (1.5, 3.0))
        assert _close(posed["point"][0], 1.5, 1e-6) and _close(posed["point"][1], 3.0, 1e-6), (kind, posed)
    waiting = Stroke.pose(Cutting.TOOL_CHOP, None, (1.5, 3.0))
    assert waiting["point"][1] > 3.0, "悬着时头抬着"


def testEveryPoseIsFiniteAtEveryAge():
    for kind in KINDS:
        impact, length = Stroke.timesOf(kind)
        for age in (None, 0.0, 0.05, impact, length * 0.9, length):
            posed = Stroke.pose(kind, age, (0.0, 3.0), 4.0, -1.0, 1.0)
            assert all(abs(v) < 1e3 for v in posed["point"] + posed["center"]) and Mth.isFinite(posed["roll"]), (kind, age, posed)


def testTheRollTurnsTheIconSoItsHeadPointsAtTheWork():
    posed = Stroke.pose(Cutting.TOOL_CHOP, 0.19, (0.0, 3.0))
    assert _close(posed["roll"] % 360.0, 207.0, 0.5), "斧头：握柄在右上、头朝下要顺时针转 207 度（刀尖朝下是 135 度）"
    first = Stroke.pose(Cutting.TOOL_CHOP, 0.0, (0.0, 3.0))
    assert first["roll"] != posed["roll"], "抬起来时姿态变了"
    assert _close(Stroke.reachOf(Cutting.TOOL_CHOP), math.hypot(4.0, 10.0) * 0.45)


def testTheLeverDropsTheHandleAndRaiseLiftsTheHead():
    plain = Stroke.pose(Cutting.TOOL_DIG, 0.1, (0.0, 3.0))
    levered = Stroke.pose(Cutting.TOOL_DIG, 0.22, (0.0, 3.0))
    assert levered["roll"] != plain["roll"]
    swung = Stroke.pose(Cutting.TOOL_SMASH, 0.14, (0.0, 3.0))
    assert swung["point"][1] > 3.0 + 1.0, "往后抬到最高：头比落点高出一截"


def testWhereToolsLandOnABlockAndHowHighTheyWork():
    assert _close(Stroke.workHeight(Cutting.TOOL_DIG, 5.2), 4.0) and _close(Stroke.workHeight(Cutting.TOOL_STRIP, 5.2), 4.9)
    assert _close(Stroke.workHeight(Cutting.TOOL_PRY, 5.2), 5.1) and Stroke.workHeight(Cutting.TOOL_CHOP, 5.2) == 5.2
    reach = Marks.BLOCK_SIZE / 2.0 - Stroke.BLOCK_MARGIN
    assert _close(reach, 1.4)
    assert Stroke.aimOnBlock(Cutting.TOOL_CHOP, 9.0, -9.0) == (reach, -reach), "夹在方块里"
    assert Stroke.aimOnBlock(Cutting.TOOL_STRIP, 0.5, 1.0) == (0.5, -2.75), "削皮贴着近侧"
    assert Stroke.aimOnBlock(Cutting.TOOL_DIG, 0.5, 1.0) == (0.5, -2.9), "铲也是"


def testTheHandleIsTurnedHalfRoundToTheCooksSide():
    assert Stroke.towardsCook(0.3) == 0.3 and _close(Stroke.towardsCook(2.5), 2.5 + math.pi)


def testShearsAreSnippedFromOneEndOfTheLineToTheOther():
    cut = Marks.Cut(0.0, 0.0, 0.0)
    start, end = Stroke.snipRange(0.0, 0.0, 0.0, cut, (-3.0, 3.0))
    assert _close(start, -2.6) and _close(end, 2.6), "两头各留 0.4"
    start, end = Stroke.snipRange(1.0, 0.0, 0.0, cut, (-3.0, 3.0))
    assert _close(start, -4.0 + 0.4) and _close(end, 2.0 - 0.4), "剪刀不在线中间：范围相对它现在在哪"
    start, end = Stroke.snipRange(0.0, 0.0, math.pi, cut, (-3.0, 3.0))
    assert _close(start, -2.6) and _close(end, 2.6), "握柄转了半圈：尖朝另一头，范围翻过来"


def testWhichKindsAreStrokes():
    assert not Stroke.isStroke(Cutting.TOOL_CUT) and all(Stroke.isStroke(kind) for kind in KINDS)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
