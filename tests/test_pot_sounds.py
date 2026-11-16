# -*- coding: utf-8 -*-
# runner: both
"""厨锅声音日程（Shared/Rules/HandsOn/PotSounds.py）：数值照 Hands-On Delight 的 PotBehavior.sounds / StationLoop / PotSounds。

每步 0.05 秒（一刻）。Java 的出处：持续声音量 BODY_RESTING 0.3 / BODY_COOKING 0.7 / STIR_VOLUME 0.7、每刻滑 12%、沸腾间隔 2.6 / 1.7 秒、
煎滋 3.0 秒 / 0.22 / 0.9、咕噜间隔 0.11 秒 / 0.32 / 0.9 + 0.04 * 队里剩的 / 最多 9 个。
"""
from __future__ import print_function

import fdtest

Sounds = fdtest.load("Shared.Rules.HandsOn.PotSounds")
TICK = 0.05
COOKING = {"heated": True, "cooking": True, "soup": True, "swirl": 0.0}
RESTING = {"heated": True, "cooking": False, "soup": True, "swirl": 0.0}
COLD = {"heated": False, "cooking": False, "soup": True, "swirl": 0.0}


def make(value=0.5):
    return Sounds.PotSounds(lambda: value)


def run(sounds, state, seconds, dt=TICK, start=0.0):
    """按 dt 推进 seconds 秒，返回 [(时刻, 决定)]。"""
    found, now = [], start
    for _ in range(int(round(seconds / dt))):
        for decision in sounds.step(dt, state):
            found.append((now, decision))
        now += dt
    return found


def plays(found, name):
    return [(round(at, 3), d) for at, d in found if d[0] == "play" and d[1] == name]


def gaps(found):
    """相邻两次的间隔。计时器是逐帧减的浮点数，到点那一帧可能因舍入晚一步：间隔在 [周期, 周期 + 一帧) 里。"""
    times = [at for at, _d in found]
    return [b - a for a, b in zip(times, times[1:])]


def testConstantsAreJavas():
    assert (Sounds.BODY_RESTING, Sounds.BODY_COOKING, Sounds.STIR_VOLUME) == (0.3, 0.7, 0.7)
    assert (Sounds.BLUB_VOLUME, Sounds.SIZZLE_VOLUME, Sounds.ADD_FOOD_VOLUME) == (0.32, 0.22, 0.16)
    assert (Sounds.BOIL_EVERY, Sounds.BOIL_EVERY_COOKING, Sounds.SIZZLE_EVERY) == (2.6, 1.7, 3.0)
    assert (Sounds.BLUB_GAP, Sounds.MOST_BLUBS, Sounds.GLIDE, Sounds.SILENT) == (0.11, 9, 0.12, 0.004)


def testSoundIdsNameJavasEvents():
    ids = Sounds.SOUND_IDS
    assert ids["body"] == "handson_delight:pot.body" and ids["blub"] == "handson_delight:pot.blub"
    assert ids["boil"] == "farmersdelight:block.cooking_pot.boil_soup" and ids["sizzle"] == "farmersdelight:block.skillet.sizzle"
    assert ids["chime"] == "minecraft:block.note_block.chime" and ids["egg_crack"] == "minecraft:block.turtle_egg.crack"


def testOneShotsTable():
    shotOf = Sounds.shotOf
    assert shotOf("plop", 0) == {"type": "sound", "name": "plop", "volume": 0.5, "pitch": 0.92, "at": "item_0"}
    assert abs(shotOf("plop", 5)["pitch"] - (0.92 + 0.15)) < 1e-9 and shotOf("plop", 5)["at"] == "item_5", "0.92 + 0.03 * 槽位"
    assert shotOf("plopDissolved")["volume"] == 0.25 and shotOf("plopDissolved")["pitch"] == 1.35
    assert shotOf("plopEgg")["volume"] == 0.35 and shotOf("plopEgg")["pitch"] == 1.25
    burst = shotOf("burst", 3)
    assert burst["name"] == "burst" and burst["volume"] == 0.55 and abs(burst["pitch"] - 1.1) < 1e-9 and burst["at"] == "broth"
    assert shotOf("scoop")["volume"] == 0.55 and shotOf("scoopBack")["volume"] == 0.45 and shotOf("scoopBack")["pitch"] == 1.1
    assert [shotOf("chime", star)["pitch"] for star in range(3)] == [1.0, 1.26, 1.5]
    assert shotOf("chime", 1)["volume"] == 0.35 and shotOf("chime", 1)["at"] == "badge"
    assert shotOf("addFood", 2)["volume"] == 0.16 and shotOf("addFood", 2)["pitch"] == 0.8
    assert shotOf("bucket")["name"] == "bucket_empty" and shotOf("bottle")["name"] == "bottle_empty" and shotOf("bucket")["at"] is None
    assert shotOf("sand")["pitch"] == 1.4 and shotOf("crack")["pitch"] == 1.5
    assert Sounds.playOf(shotOf("scoop")) == ("play", "scoop", 0.55, 1.0)


def testBoilEveryTwoPointSixSecondsAndFasterWhileCooking():
    resting = plays(run(make(0.0), RESTING, 8.0), "boil")
    assert resting[0][0] == 0.0 and len(resting) == 4, "第一帧就响（计时器从 0 开始）"
    assert all(2.6 - 1e-9 <= gap < 2.6 + TICK + 1e-9 for gap in gaps(resting)), gaps(resting)
    cooking = plays(run(make(0.0), COOKING, 6.0), "boil")
    assert cooking[0][0] == 0.0 and len(cooking) == 4
    assert all(1.7 - 1e-9 <= gap < 1.7 + TICK + 1e-9 for gap in gaps(cooking)), gaps(cooking)
    assert all(d[2] == 1.0 for _at, d in resting), "音量 1.0"


def testBoilPitchIs095PlusTenthOfARandom():
    assert plays(run(make(0.0), RESTING, 0.1), "boil")[0][1][3] == 0.95
    assert abs(plays(run(make(1.0), RESTING, 0.1), "boil")[0][1][3] - 1.05) < 1e-9


def testNoBoilWhenColdOrEmpty():
    assert not plays(run(make(), COLD, 6.0), "boil")
    empty = dict(RESTING, soup=False)
    assert not plays(run(make(), empty, 6.0), "boil"), "锅里什么都没有：FD 自己的声音，这里不响"


def testSizzleOnlyWhileCookingEveryThreeSeconds():
    found = plays(run(make(), COOKING, 7.0), "sizzle")
    assert found[0][0] == 0.0 and len(found) == 3
    assert all(3.0 - 1e-9 <= gap < 3.0 + TICK + 1e-9 for gap in gaps(found)), gaps(found)
    assert found[0][1] == ("play", "sizzle", 0.22, 0.9)
    assert not plays(run(make(), RESTING, 7.0), "sizzle")


def testBlubsAreQueuedAtLeastAGapApartAndGoUpInPitchAsTheQueueEmpties():
    sounds = make()
    sounds.blub(3)
    found = plays(run(sounds, RESTING, 1.0), "blub")
    times = [at for at, _d in found]
    assert len(found) == 3 and all(b - a >= 0.11 - 1e-9 for a, b in zip(times, times[1:])), times
    assert [d[2] for _at, d in found] == [0.32, 0.32, 0.32]
    # 先减再算音高：队里剩 2、1、0 个
    assert [round(d[3], 3) for _at, d in found] == [0.98, 0.94, 0.9]
    assert abs(times[1] - times[0] - 0.15) < 1e-9, "间隔 0.11 秒，每步 0.05 秒，所以实际隔三步 0.15"


def testTheBlubQueueHoldsNineAtMost():
    sounds = make()
    sounds.blub(40)
    assert sounds.blubs == 9
    sounds.blub(1)
    assert sounds.blubs == 9
    found = plays(run(sounds, COLD, 3.0), "blub")
    assert len(found) == 9, "冷锅也咕噜（咕噜和烧没烧着无关，PB 1259）"
    assert abs(found[0][1][3] - (0.9 + 0.04 * 8)) < 1e-9, "第一声时队里还剩 8 个"
    sounds.blub(0)
    sounds.blub(-4)
    assert sounds.blubs == 0, "排完了，零和负数不动队列"


def testBodyLoopTargetsAndGlide():
    sounds = make()
    first = [d for d in sounds.step(TICK, COOKING) if d[0] == "loop" and d[1] == "body"][0]
    # 起声音量 0.004，一刻之后朝 0.7 走 12%
    assert abs(first[2] - (0.004 + (0.7 - 0.004) * 0.12)) < 1e-9 and first[3] == 1.0
    for _ in range(199):
        sounds.step(TICK, COOKING)
    assert abs(sounds.body.volume - 0.7) < 1e-3, "十秒后到位"
    resting = make()
    for _ in range(400):
        resting.step(TICK, RESTING)
    assert abs(resting.body.volume - 0.3) < 1e-3


def testGlideIsPerTickWhateverTheFrameLength():
    one = make()
    two = make()
    one.step(0.1, COOKING)
    two.step(0.05, COOKING)
    two.step(0.05, COOKING)
    # 起声那一刻都从 0.004 起，两个半步 = 一整步
    assert abs(one.body.volume - two.body.volume) < 1e-9


def testStirLoopFollowsTheSwirl():
    sounds = make()
    state = dict(COOKING, swirl=1.0)
    for _ in range(200):
        out = sounds.step(TICK, state)
    loop = [d for d in out if d[0] == "loop" and d[1] == "stir"][0]
    assert abs(loop[2] - 0.7) < 1e-3, "音量 = swirl * 0.7"
    assert abs(loop[3] - 1.05) < 1e-3, "音高 0.9 + 0.15 * swirl"
    half = make()
    for _ in range(200):
        out = half.step(TICK, dict(COOKING, swirl=0.4))
    loop = [d for d in out if d[0] == "loop" and d[1] == "stir"][0]
    assert abs(loop[2] - 0.28) < 1e-3 and abs(loop[3] - 0.96) < 1e-3


def testTheLoopsFadeOutAndStopWhenQuiet():
    sounds = make()
    for _ in range(100):
        sounds.step(TICK, COOKING)
    assert sounds.body.running
    out = []
    for _ in range(400):
        out += sounds.step(TICK, COLD)
    assert not sounds.body.running and sounds.body.volume == 0.0, "目标 0 且音量落到 0.004 以下就停"
    assert not [d for d in sounds.step(TICK, COLD) if d[0] == "loop"], "停了之后不再给 loop 决定"


def testQuantisedStepsRestartOnlyWhenTheStepChanges():
    sounds = make()
    out = sounds.step(TICK, COOKING)
    restarts = [d for d in out if d[0] == "restart" and d[1] == "body"]
    assert restarts == [("restart", "body", 0.7, 1.0)], "起声：直接进最高档"
    for _ in range(100):
        assert not [d for d in sounds.step(TICK, COOKING) if d[0] in ("restart", "stop")], "没变档，不重启"
    out = sounds.step(TICK, RESTING)
    assert [d for d in out if d[0] == "restart" and d[1] == "body"] == [("restart", "body", 0.3, 1.0)]
    out = sounds.step(TICK, COLD)
    assert [d for d in out if d[0] == "stop" and d[1] == "body"] and sounds.body.notch == 0


def testStirStepsAreThreeWithHysteresis():
    loop = Sounds.Loop("stir", Sounds.STIR_LEVELS, Sounds.stirPitch)
    levels = []
    for volume in (0.0, 0.05, 0.12, 0.2, 0.3, 0.4, 0.45, 0.55, 0.62, 0.7):
        for d in loop.step(TICK, volume, 1.0):
            if d[0] in ("restart", "stop"):
                levels.append((volume, d[0], d[2]))
    assert [(kind, level) for _v, kind, level in levels] == [("restart", 0.2), ("restart", 0.45), ("restart", 0.7)]
    assert [round(Sounds.stirPitch(level), 4) for level in Sounds.STIR_LEVELS] == [0.9429, 0.9964, 1.05]


def testTheQuantiserDoesNotFlapOnABoundary():
    loop = Sounds.Loop("stir", Sounds.STIR_LEVELS, Sounds.stirPitch)
    loop.step(TICK, 0.45, 1.0)
    assert loop.notch == 2
    changes = 0
    boundary = (0.45 + 0.7) / 2.0
    for volume in (boundary - 0.02, boundary + 0.02, boundary - 0.01, boundary + 0.025, boundary):
        changes += len([d for d in loop.step(TICK, volume, 1.0) if d[0] in ("restart", "stop")])
    assert changes == 0, "分界附近 0.03 以内抖动不换档"
    assert [d[0] for d in loop.step(TICK, boundary + 0.04, 1.0) if d[0] in ("restart", "stop")] == ["restart"]
    assert loop.notch == 3


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
