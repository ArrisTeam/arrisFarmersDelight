# -*- coding: utf-8 -*-
# runner: both
"""StoveFx（烤架的热浪、蒸汽、烟、嗞嗞声和各个动作的声音与粒子）。数字来自 Hands-On Delight 的 client/StoveBehavior.java：
heat 257-306、hitsTheGrill 309-312、onPiece / roundPiece 319-328、turned 394-398、onEffect 480-497、taken 516。"""
from __future__ import print_function

import math

import fdtest

X = fdtest.load("Shared.Rules.HandsOn.StoveFx")


class Dice(object):
    """按给定的顺序一个个掷出 0..1 的数，用完了循环。"""

    def __init__(self, *values):
        self.values, self.at = values, 0

    def __call__(self):
        value = self.values[self.at % len(self.values)]
        self.at += 1
        return value


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def kinds(effects):
    return [(e.kind if isinstance(e, X.Spawn) else e.name) for e in effects]


def testTheLitGrillShimmersAtItsOwnPace():
    heat = X.Heat(Dice(0.5))
    assert heat.step(0.5, [], []) == [], "1.6 个每秒：半秒还不到一个"
    effects = heat.step(0.2, [], [])
    assert kinds(effects) == ["heat"], "0.7 秒 * 1.6 = 1.12：冒一个"
    spawn = effects[0]
    assert spawn.place is None and spawn.velocity == (0.0, 3.0, 0.0) and spawn.spread == 0.3 and spawn.count == 1 and spawn.color == 0
    near(spawn.offset[0], 0.0), near(spawn.offset[2], 0.0)
    assert 2.0 <= spawn.offset[1] <= 4.0, "离烤架 2 ~ 4 px 高"
    big = X.Heat(Dice(0.0)).step(10.0, [], [])
    assert kinds(big).count("heat") == 16, "10 秒 * 1.6 = 16 个"
    for e in big:
        assert abs(e.offset[0]) <= 5.5 and abs(e.offset[2]) <= 5.5, "烤架中心 ±5.5 px 里"


def testACookingPieceSteamsAndSizzlesQuietly():
    heat = X.Heat(Dice(0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5))
    effects = heat.step(1.0 / 0.9 + 0.001, [3], [])
    assert [e.kind for e in effects if isinstance(e, X.Spawn)].count("steam") == 1
    steam = [e for e in effects if isinstance(e, X.Spawn) and e.kind == "steam"][0]
    assert steam.place == 3 and steam.color == 0x40FFFFFF and steam.spread == 0.4 and steam.velocity[1] == 2.2
    assert steam.offset[1] == 0.6 and abs(steam.offset[0]) <= 1.2 and abs(steam.offset[2]) <= 1.2
    sizzle = [e for e in effects if isinstance(e, X.Sound)]
    assert len(sizzle) == 1 and sizzle[0].name == "sizzle" and sizzle[0].volume == 0.15 and 1.0 <= sizzle[0].pitch <= 1.1
    assert [e for e in heat.step(1.5, [3], []) if isinstance(e, X.Sound)] == [], "1.6 秒才再嗞一声"
    assert len([e for e in heat.step(0.2, [3], []) if isinstance(e, X.Sound)]) == 1


def testAPieceWaitingToBeTurnedSmokesAndSizzlesSharper():
    heat = X.Heat(Dice(0.0, 0.25))
    effects = heat.step(0.41, [], [2])
    smoke = [e for e in effects if isinstance(e, X.Spawn) and e.kind == "smoke"]
    assert len(smoke) == 1 and smoke[0].place == 2 and smoke[0].velocity[1] == 4.0 and smoke[0].spread == 0.3 and smoke[0].color == 0
    reach = math.sqrt(smoke[0].offset[0] ** 2 + smoke[0].offset[2] ** 2)
    assert 2.0 <= reach <= 2.76 and smoke[0].offset[1] == 0.15, "件的边上：半径 2.5 * (0.8 ~ 1.1)"
    sound = [e for e in effects if isinstance(e, X.Sound)][0]
    assert sound.volume == 0.3 and sound.pitch >= 1.15
    assert len([e for e in X.Heat(Dice(0.5)).step(1.2, [], [2]) if isinstance(e, X.Sound)]) == 1
    wait = X.Heat(Dice(0.5))
    wait.step(0.01, [], [2])
    assert len([e for e in wait.step(1.0, [], [2]) if isinstance(e, X.Sound)]) == 0
    assert len([e for e in wait.step(0.2, [], [2]) if isinstance(e, X.Sound)]) == 1, "等着翻的 1.1 秒一次"


def testSmokeAndVapourScaleWithHowManyPiecesAreDoingIt():
    heat = X.Heat(Dice(0.0, 0.5, 0.5))
    effects = heat.step(1.0, [0, 1, 2], [3, 4])
    spawns = [e.kind for e in effects if isinstance(e, X.Spawn)]
    assert spawns.count("steam") == 2 and spawns.count("smoke") == 5, "0.9 * 3 = 2.7 口汽、2.5 * 2 = 5 口烟"


def testNothingCookingMeansNoSizzleAndATimerThatStartsOver():
    heat = X.Heat(Dice(0.5))
    assert any(isinstance(e, X.Sound) for e in heat.step(0.1, [0], []))
    assert not any(isinstance(e, X.Sound) for e in heat.step(0.1, [0], []))
    assert not any(isinstance(e, X.Sound) for e in heat.step(0.1, [], []))
    assert any(isinstance(e, X.Sound) for e in heat.step(0.1, [0], [])), "一件都没有了又放上新的：马上嗞一声"
    heat.idle()
    assert heat.sizzle == 0.0


def testAPieceLandingOnTheHotGrillHissesAndSteams():
    effects = X.hitsTheGrill(2, Dice(0.5))
    assert kinds(effects) == ["steam", "add_food"]
    steam, sound = effects
    assert steam.place == 2 and steam.count == 2 and steam.spread == 1.2 and steam.color == 0x50FFFFFF and steam.velocity == (0.0, 3.0, 0.0)
    assert sound.volume == 0.45 and near(sound.pitch, 1.05 + 0.05) is None


def testTurningMakesAClinkWhenItLeavesAndAHissWhenItLandsBack():
    start = X.turnStarts()
    assert kinds(start) == ["lantern_step"] and start[0].volume == 0.25 and start[0].pitch == 1.3
    lands = X.turnLands(1, Dice(0.5))
    assert kinds(lands) == ["add_food", "steam"]
    assert lands[0].volume == 0.5 and near(lands[0].pitch, 1.0 + 0.5 * 0.15) is None
    assert lands[1].spread == 0.8 and lands[1].count == 2 and lands[1].color == 0x50FFFFFF


def testAPieceDoneOnBothSidesSteamsGlintsAndChimes():
    effects = X.grilled(4, Dice(0.5))
    assert kinds(effects) == ["steam", "glint", "item_pickup"]
    steam, glint, sound = effects
    assert steam.count == 3 and steam.spread == 1.5 and steam.color == 0x60FFFFFF and steam.velocity == (0.0, 3.0, 0.0)
    assert glint.count == 3 and glint.spread == 1.5 and glint.color == 0xFFFFE9A0 and glint.velocity == (0.0, 2.0, 0.0)
    assert sound.volume == 0.3 and sound.pitch == 1.3


def testLayingOnAndTakingOffEachMakeTheirOwnOneSound():
    """StoveBehavior.onEffect 的 EFFECT_PLACED（灯笼放下 0.4 / 1.1）和 taken（拾取 0.3 / 1.5）：一回事件一声。"""
    assert [(s.name, s.volume, s.pitch) for s in X.placed()] == [("lantern_place", 0.4, 1.1)]
    assert [(s.name, s.volume, s.pitch) for s in X.taken()] == [("item_pickup", 0.3, 1.5)]


def testARefusedPieceBouncesBackWithAClink():
    assert [(s.name, s.volume, s.pitch) for s in X.refused()] == [("lantern_hit", 0.4, 1.3)]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
