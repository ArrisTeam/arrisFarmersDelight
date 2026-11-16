# -*- coding: utf-8 -*-
# runner: both
"""StirSkill 搅锅评星测试。

移植自 Hands-On Delight 的 PotTests：onlyGoodStirringEarnsStars、theCooksClockJudgesThePace、
aFloodOfStrokesFillsNoFaster、aCookWhoKnowsTheDishGetsMore、theFirstTimeHasOneStar。
原测试的时间以刻计，这里 tick / 20 换成秒；采样在 tick 0..200 每 2 刻一次（0.1 秒）。
"""
from __future__ import print_function

import math

import fdtest

Stir = fdtest.load("Shared.Rules.HandsOn.StirSkill")


def second(tick):
    return tick / 20.0


def onCircle(tick, radius):
    """原测试的勺尖：每 2 刻转 2*pi/10 弧度，即 6.28 rad/s。"""
    angle = tick * math.pi / 10.0
    return math.cos(angle) * radius, math.sin(angle) * radius


def stirWell(openStars, lastTick, step=2):
    """原 stirWell：宽圈、稳速的搅拌，每 step 刻一次，到 lastTick 为止（含）。"""
    skill = Stir.StirSkill()
    for tick in range(0, lastTick + 1, step):
        x, z = onCircle(tick, 0.9)
        skill.move(second(tick), x, z, True, openStars)
    return skill


def testOnlyGoodStirringEarnsStars():
    rounds, shaking, middle, cold = Stir.StirSkill(), Stir.StirSkill(), Stir.StirSkill(), Stir.StirSkill()
    for tick in range(0, 201, 2):
        now = second(tick)
        x, z = onCircle(tick, 0.9)
        rounds.move(now, x, z, True, 3)
        back = math.sin(tick * math.pi / 6.0)
        shaking.move(now, math.cos(back) * 0.9, math.sin(back) * 0.9, True, 3)
        middleX, middleZ = onCircle(tick, 0.2)
        middle.move(now, middleX, middleZ, True, 3)
        cold.move(now, x, z, False, 3)
    end = second(200)
    assert rounds.grade(end) == 3, "wide rounds one way earn three stars, got %r" % rounds.stars(end)
    assert shaking.grade(end) == 0, "shaking back and forth earns none, got %r" % shaking.stars(end)
    assert middle.grade(end) == 0, "circling the middle earns none, got %r" % middle.stars(end)
    assert cold.grade(end) == 0, "stirring a pot that does not cook earns none"
    assert rounds.grade(second(230)) == 2, "a pause takes a star, got %r" % rounds.stars(second(230))
    assert rounds.grade(second(400)) == 0, "a long one all of them"


def testTheCooksClockJudgesThePace():
    # 包被网络攒成一批一批到达（每 6 刻到一次），厨师自己的钟仍是均匀的：照样三颗星
    bunched = Stir.StirSkill()
    for tick in range(0, 201, 2):
        x, z = onCircle(tick, 0.9)
        bunched.move(second(tick // 6 * 6 + 1), x, z, True, 3, second(tick))
    assert bunched.grade(second(199)) == 3, "got %r" % bunched.stars(second(199))


def testASlowServerIsJudgedByTheCooksClock():
    # 服务器掉刻，游戏时间只有真实时间的一半：手速 9 rad/s 的搅拌在服务器看来是 18 rad/s，快得扣分。
    # 带上厨师的钟就按厨师自己的 9 rad/s 判（这是原版注释里说的第二个理由：服务器 tick 比手转得慢）
    judged, naive = Stir.StirSkill(), Stir.StirSkill()
    for index in range(0, 101):
        real = index * 0.1
        angle = index * 0.9
        x, z = math.cos(angle) * 0.9, math.sin(angle) * 0.9
        judged.move(real / 2.0, x, z, True, 3, real)
        naive.move(real / 2.0, x, z, True, 3)
    assert judged.grade(5.0) == 3, "got %r" % judged.stars(5.0)
    assert naive.grade(5.0) < 3, "got %r" % naive.stars(5.0)


def testAFloodOfStrokesFillsNoFaster():
    # 一个服务器时刻里灌 201 个包，每个都声称厨师的钟又走了 0.1 秒：同一时刻到的包共享 SLACK 这一份余量
    flood = Stir.StirSkill()
    for stroke in range(0, 201):
        angle = stroke * 0.6
        flood.move(second(100), math.cos(angle) * 0.9, math.sin(angle) * 0.9, True, 3, stroke * 2.0 / 20.0)
    assert flood.grade(second(100)) == 0, "got %r" % flood.stars(second(100))
    assert flood.stars(second(100)) < 0.3, "至多评了一段笔画：%r" % flood.stars(second(100))
    # 钟最多比起点多走 SLACK 秒
    assert abs(flood._lastAt - (second(100) + Stir.SLACK)) < 1.0e-9, flood._lastAt


def testOnARealTimeServerClockAFloodGetsNoMoreThanTheCap():
    """基岩版移植：服务器钟是 time.time()，灌的包各自落在不同时刻。HoD 的"每个新时刻一份余量"挡不住，realTime 挡得住。"""
    def flood(skill):
        for stroke in range(0, 201):
            angle = stroke * 0.6
            skill.move(5.0 + stroke * 0.001, math.cos(angle) * 0.9, math.sin(angle) * 0.9, True, 3, stroke * 0.1)
        return skill
    tickWise, realTime = flood(Stir.StirSkill()), flood(Stir.StirSkill(realTime=True))
    end = 5.0 + 0.2
    assert tickWise.grade(end) == 3, "不加上限时 0.2 秒灌出满星：%r" % tickWise.stars(end)
    assert realTime.stars(end) < 1.0, "累计最多领先 LEAD_MOST 秒：%r" % realTime.stars(end)
    assert realTime._lastAt - 5.0 <= 0.2 + Stir.LEAD_MOST + 1.0e-9, realTime._lastAt


def testOnARealTimeServerClockHonestStirringStillFillsUp():
    honest, bunched = Stir.StirSkill(realTime=True), Stir.StirSkill(realTime=True)
    for tick in range(0, 201, 2):
        x, z = onCircle(tick, 0.9)
        honest.move(second(tick), x, z, True, 3, second(tick) + 7.0)
        bunched.move(second(tick // 6 * 6 + 1), x, z, True, 3, second(tick))
    assert honest.grade(second(200)) == 3, "got %r" % honest.stars(second(200))
    assert bunched.grade(second(199)) == 3, "网络攒包照样三星：%r" % bunched.stars(second(199))


def testTheCooksClockNeverRunsBack():
    skill = Stir.StirSkill()
    for index in range(0, 41):
        x, z = onCircle(index * 2, 0.9)
        # 声称的钟越走越小：每包的 step 夹到 0，钟不动，窗口攒不满，永远评不了分
        skill.move(second(index * 2), x, z, True, 3, 10.0 - index * 0.1)
    assert skill.stars(second(80)) == 0.0
    assert abs(skill._lastAt - 0.0) < 1.0e-9, skill._lastAt


def testACookWhoKnowsTheDishGetsMore():
    # 做过 40 份的菜开 3 颗星：6 秒搅满
    skill = stirWell(3, 120)
    assert skill.stars(second(120)) > 2.99, skill.stars(second(120))


def testTheFirstTimeHasOneStar():
    # 第一次做只开 1 颗星：搅得再好也只有 1.0
    skill = stirWell(1, 120)
    assert skill.stars(second(120)) == 1.0, skill.stars(second(120))
    assert skill.grade(second(120)) == 1
    skill = stirWell(2, 240)
    assert skill.stars(second(240)) == 2.0, "开两颗星就封顶两颗"


def testOpenStarsCapAppliesOnTheNextStroke():
    skill = stirWell(3, 120)
    assert skill.grade(second(120)) == 3
    x, z = onCircle(122, 0.9)
    skill.move(second(122), x, z, True, 1)
    assert skill.stars(second(122)) == 1.0, "开星数降下来，星数立刻被截到上限"


def testStarsDrainAfterTheSpoonStops():
    skill = stirWell(3, 200)
    last = second(200)
    assert skill.stars(last + 0.5) == 3.0, "GRACE 0.5 秒内不掉"
    assert abs(skill.stars(last + 1.5) - (3.0 - 0.75 * 1.0)) < 1.0e-9, "过了 GRACE，每秒掉 0.75 颗"
    assert skill.stars(last + 20.0) == 0.0


def testTooSlowOrTooFastEarnsNothing():
    for speed in (1.0, 30.0):
        skill = Stir.StirSkill()
        for index in range(0, 101):
            angle = index * 0.1 * speed
            skill.move(index * 0.1, math.cos(angle) * 0.9, math.sin(angle) * 0.9, True, 3)
        assert skill.stars(10.0) == 0.0, "speed %r gave %r" % (speed, skill.stars(10.0))


def testSpoonCoordinatesAreSanitisedByTheServer():
    assert Stir.clampSpoon(0.5) == 0.5
    assert Stir.clampSpoon(5.0) == 1.0 and Stir.clampSpoon(-5.0) == -1.0
    assert Stir.clampSpoon(float("nan")) == 0.0 and Stir.clampSpoon(float("inf")) == 0.0
    skill = Stir.StirSkill()
    skill.move(0.0, float("nan"), 0.0, True, 3)
    skill.move(0.1, 0.9, 0.0, True, 3, float("nan"))   # 厨师的钟是 NaN：当作没有
    assert skill.stars(0.1) == 0.0


def testScoreSamples():
    samples = []
    for tick in range(0, 201, 2):
        x, z = onCircle(tick, 0.9)
        samples.append((second(tick), x, z))
    stars, grade = Stir.scoreSamples(samples)
    assert grade == 3 and stars > 2.99
    assert Stir.scoreSamples(samples, cooking=False) == (0.0, 0)
    assert Stir.scoreSamples(samples, openStars=1)[1] == 1
    assert Stir.scoreSamples([]) == (0.0, 0)
    stars, grade = Stir.scoreSamples(samples, endTime=second(230))
    assert grade == 2, "第四个参数是评分时刻：停手 1 秒后掉到 2 星"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
