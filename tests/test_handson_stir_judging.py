# -*- coding: utf-8 -*-
# runner: both
"""StirSkill 评分细则测试：手速带、宽度、稳定性、方向、涨落速度、笔画窗口。

这些数值不在 Hands-On Delight 的 GameTest 里（那里只测"搅好 3 星、抖动/打转/没煮 0 星"），
按 StirSkill.java 的公式手算：稳速、宽圈时质量 = 手速分 * 宽度分，星数收敛到 3 * 质量 / 0.8（封顶 3）。
采样间隔 0.05 秒（一刻），一段笔画 5 个采样（0.25 秒）评一次分。
"""
from __future__ import print_function

import math

import fdtest

Stir = fdtest.load("Shared.Rules.HandsOn.StirSkill")


DT = 0.05


def stir(schedule, radius=0.9):
    """按 [(秒数, 角速度 rad/s), ...] 依次转圈，每 DT 秒一个采样。返回 (评分器, 最后一个采样的时刻)。"""
    skill, angle, index = Stir.StirSkill(), 0.0, 0
    for seconds, speed in schedule:
        for _ in range(int(round(seconds / DT))):
            skill.move(index * DT, math.cos(angle) * radius, math.sin(angle) * radius, True, 3)
            angle += speed * DT
            index += 1
    return skill, (index - 1) * DT


def steadyStars(speed, radius=0.9, seconds=12.0):
    skill, last = stir([(seconds, speed)], radius)
    return skill.stars(last)


def testThePaceBandsOfTheHand():
    # 1.2 rad/s 以下 0，爬到 3.0 满分；13 以内满分，再降到 22 为 0
    assert steadyStars(1.2) < 1e-6 and steadyStars(22.0) < 1e-6, "带边上浮点误差会给出 1e-16 量级的星，不是整 0"
    assert steadyStars(1.0) == 0.0 and steadyStars(25.0) == 0.0
    assert abs(steadyStars(2.4) - 2.5) < 0.02, "pacing (2.4-1.2)/1.8 = 0.667 -> 3 * 0.667 / 0.8 = 2.5"
    assert abs(steadyStars(3.0) - 3.0) < 0.02 and abs(steadyStars(13.0) - 3.0) < 0.02
    assert abs(steadyStars(18.0) - 3 * (22.0 - 18.0) / 9.0 / 0.8) < 0.02, "pacing (22-18)/9 = 0.444 -> 1.67"


def testANarrowRoundIsWorthLessThanAWideOne():
    # 宽度分：勺尖离中心 0.3 以内为 0，0.7 以上满分，中间线性
    assert steadyStars(6.0, radius=0.25) == 0.0
    assert abs(steadyStars(6.0, radius=0.5) - 3 * 0.5 / 0.8) < 0.02, "宽度分 (0.5-0.3)/0.4 = 0.5 -> 1.875"
    assert abs(steadyStars(6.0, radius=0.7) - 3.0) < 0.02 and abs(steadyStars(6.0, radius=1.0) - 3.0) < 0.02


def testTheFirstWindowIsJudgedAfterAQuarterSecond():
    skill, _ = stir([(0.25, 6.0)])
    assert skill.stars(0.2) == 0.0, "0.2 秒时一段笔画还没攒够"
    skill, last = stir([(0.3, 6.0)])
    assert abs(last - 0.25) < 1e-9
    assert abs(skill.stars(last) - Stir.RISE * 0.25) < 1e-9, "第一段评分涨 RISE * 0.25 秒 = 0.1875 颗"


def testStarsFallWhenTheStirringTurnsBad():
    # 好好搅 6 秒拿满 3 星，然后手速飙到 30 rad/s（质量 0）：继续搅着，星星每秒掉 FALL = 0.5 颗
    skill, last = stir([(6.0, 6.0), (2.0, 30.0)])
    assert 1.9 <= skill.stars(last) <= 2.2, skill.stars(last)
    skill, last = stir([(6.0, 6.0), (8.0, 30.0)])
    assert skill.stars(last) == 0.0


def testAnUnevenHandHoldsTheStarsLower():
    # 每段笔画手速在 4 和 12 rad/s 之间来回换：手速变化超过 ln 比值 0.2 + 0.9 就一分不给
    uneven, last = stir([(0.25, 4.0), (0.25, 12.0)] * 24)
    steady, _ = stir([(12.0, 8.0)])
    assert steady.stars(last) > 2.99 and uneven.stars(last) < 2.4, (steady.stars(last), uneven.stars(last))


def testAHandThatSettlesIntoANewPaceEarnsTheStarsAgain():
    # 手速基准每段向新手速靠 40%：6 -> 9 rad/s 起初扣一点稳定分，几段之后习惯了又是满分
    skill, last = stir([(4.0, 6.0), (8.0, 9.0)])
    assert skill.stars(last) > 2.99, skill.stars(last)


def testTurningTheOtherWayCostsOnlyOneWindow():
    # 方向由上一段定；反着转的那一段质量为 0，之后以新方向为准重新涨
    skill, last = stir([(6.0, 6.0), (0.3, -6.0)])
    assert skill.stars(last) < 3.0
    skill, last = stir([(6.0, 6.0), (6.0, -6.0)])
    assert skill.stars(last) > 2.99, "反转一圈之后又稳了"


def testBackAndForthInsideAStrokeCountsAsShaking():
    # 每段笔画 5 步净转 1.5 rad（= 6 rad/s，和稳速搅一样快），但中间倒退了一小步 0.1 rad：整段质量为 0
    skill, angle, index = Stir.StirSkill(), 0.0, 0
    for _ in range(48):
        for delta in (0.4, 0.4, -0.1, 0.4, 0.4):
            skill.move(index * DT, math.cos(angle) * 0.9, math.sin(angle) * 0.9, True, 3)
            angle += delta
            index += 1
    assert steadyStars(6.0) > 2.99
    assert skill.stars(index * DT) < 0.01, "shaking back and forth earns none: %r" % skill.stars(index * DT)


def testAPauseStartsAFreshStroke():
    skill, last = stir([(6.0, 6.0)])
    before = skill.stars(last)
    angle = 6.0 * 6.0
    # 停了 1 秒（超过 BREAK 0.6 秒）再动：新的一段笔画，手速基准也重来，不会被"和之前比"扣分
    now = last + 1.0
    for index in range(int(round(6.0 / DT))):
        skill.move(now + index * DT, math.cos(angle) * 0.9, math.sin(angle) * 0.9, True, 3)
        angle += 9.0 * DT
    assert skill.stars(now + 6.0 - DT) > 2.99 and before > 2.99


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
