# -*- coding: utf-8 -*-
# runner: both
"""煎锅、炉灶、厨锅场景的粒子散布照 Diegesis 的 SceneParticles.spawn（Shared/Rules/SceneScatter + Compat/Diegesis 的 PanFx / GrillFx / PotSceneFx）：

SceneParticles.java:68-70：起点 at + gauss * spread（每轴）、初速 velocity + gauss * max(0.3, |velocity| * 0.25)（每轴），gauss() = nextGaussian() * 0.5（:158-160，标准差是一半）；
spawnInLiquid :143：液内泡的起点高度 lerp(random * 0.6F, bottom + 0.2F, fill)，只取下 60%。
原来：煎锅的 gauss 没乘 0.5（散开一倍）；炉灶把 spread 当速度的均匀抖动、起点不散（一次 2~3 颗叠在一点）；厨锅的液内泡起点取了整段。引擎是 potclient / panclient 里的假的。

厨锅的 spawnInLiquid / spawnOnLiquid（SceneParticles.java:83-156）还有：液内泡的初速 velocity + (gauss * jitter * 0.3, gauss * jitter, gauss * jitter * 0.3)（:146-147，左右只有 0.3 倍）、
寿命 lerp(random, 样式寿命) * 3（:148，泡样式 0.6 ~ 1.4 秒）；泡在 update（:162-197）里先问有没有浮到液面（pos.y >= ceiling）：浮到了就换成破泡，破泡的寿命到了（0.45 ~ 0.85 秒）液面才起一圈水波（:177-182），
寿命先到的泡悄悄没了、不破不起波；spawnOnLiquid 的蒸汽、水花走 spawn（:63-76），每颗的初速各抖一次。"""
from __future__ import print_function

import json
import io
import math
import os
import random

import fdtest
import potclient as C

world = C.world
Scatter = C.load("Shared.Rules.SceneScatter")
PanFx = C.load("Compat.Diegesis.PanFx")
GrillFx = C.load("Compat.Diegesis.GrillFx")
PotSceneFx = C.load("Compat.Diegesis.PotSceneFx")
PotScenes = C.load("Compat.Diegesis.PotScenes")
PanModelMath = fdtest.load("Shared.Rules.PanModelMath")
StoveFx = fdtest.load("Shared.Rules.HandsOn.StoveFx")
BrothColors = C.load("Shared.Data.BrothColors")
POS = C.POS
SAMPLES = 4000


def _deviation(values):
    mean = sum(values) / len(values)
    return mean, math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _within(value, want, tolerance=0.07):
    return abs(value - want) <= want * tolerance


# ---------------------------------------------------------------- 算式

def testThePointAndTheVelocityAreScatteredByHalfAGaussianOfTheSpreadAndOfAQuarterOfTheSpeed():
    always = lambda: 1.0                                                  # noqa: E731 - 每次 nextGaussian() 都是 1 的"随机数"
    assert Scatter.spawnPoint((1.0, 2.0, 3.0), 2.0, always) == (2.0, 3.0, 4.0), "at + gauss * spread，gauss = 1 * 0.5"
    assert Scatter.spawnPoint((1.0, 2.0, 3.0), 0.0, always) == (1.0, 2.0, 3.0), "spread 0：不散"
    assert Scatter.jitterOf((0.0, 4.0, 0.0)) == 1.0 and Scatter.jitterOf((0.0, 0.0, 0.0)) == 0.3 and Scatter.jitterOf((0.0, 0.5, 0.0)) == 0.3, "至少 0.3"
    assert Scatter.jitterOf((3.0, 4.0, 0.0)) == 1.25, "长度的四分之一"
    assert Scatter.spawnVelocity((0.0, 4.0, 0.0), always) == (0.5, 4.5, 0.5), "每轴 + gauss(0.5) * 抖动 1.0"
    assert Scatter.spawnVelocity((0.0, 0.0, 0.0), always) == (0.15, 0.15, 0.15), "不动的也有 0.3 的抖动"
    assert Scatter.liquidBubbleHeight(2.0, 6.0, 0.0) == 2.2 and abs(Scatter.liquidBubbleHeight(2.0, 6.0, 1.0) - (2.2 + 3.8 * 0.6)) < 1e-9, "下 60%"
    assert all(2.2 <= Scatter.liquidBubbleHeight(2.0, 6.0, roll / 100.0) <= 2.2 + 3.8 * 0.6 + 1e-9 for roll in range(100))


def testTheSpreadOfTheStandardGaussianIsHalfNotOne():
    random.seed(11)
    offsets = [Scatter.spawnPoint((0.0, 0.0, 0.0), 1.0)[0] for _ in range(SAMPLES)]
    mean, deviation = _deviation(offsets)
    assert abs(mean) < 0.03 and _within(deviation, 0.5), (mean, deviation)
    speeds = [Scatter.spawnVelocity((0.0, 4.0, 0.0))[1] for _ in range(SAMPLES)]
    mean, deviation = _deviation(speeds)
    assert _within(mean, 4.0, 0.02) and _within(deviation, 0.5), (mean, deviation)


def testTheBoardDustsParticleFileScattersWithTheSameVarianceInAUniformBox():
    """砧板碎屑的散布在粒子 JSON 里（方盒发射器和方向的均匀随机）：均匀分布 [-h, h] 的标准差是 h / sqrt(3)，要和高斯 0.5 * spread 一样，所以 h = sqrt(3) * 0.5 * spread。"""
    with io.open(os.path.join(fdtest.ROOT, "rp", "particles", "arris_board_dust.json"), encoding="utf-8") as handle:
        components = json.load(handle)["particle_effect"]["components"]
    uniform = math.sqrt(3.0) * Scatter.GAUSS
    assert all(("variable.spread * %.3f" % uniform) in half for half in components["minecraft:emitter_shape_box"]["half_dimensions"]), "起点：半宽 = 0.866 * spread"
    direction = components["minecraft:emitter_shape_box"]["direction"][1]
    assert ("math.max(%.4f, %.4f * " % (Scatter.JITTER_MIN / 16.0 * uniform, Scatter.JITTER_PER_SPEED * uniform)) in direction, "初速：均匀幅度 0.866 * max(0.3 / 16, |v| * 0.25)"


# ---------------------------------------------------------------- 煎锅

def _panParticles(spread, velocity, count):
    world.reset()
    fx = PanFx.PanFx(POS, PanModelMath.facingOf(0))
    fx.play([{"type": "particle", "style": "oil_pop", "pos": (8.0, 2.0, 8.0), "vel": velocity, "spread": spread, "count": count, "color": 0}])
    return world.particles


def testPanParticlesAreScatteredByHalfTheSpreadNotTheWholeOfIt():
    random.seed(3)
    particles = _panParticles(4.0, (0.0, 4.0, 0.0), SAMPLES)
    assert len(particles) == SAMPLES
    for axis in (0, 1, 2):
        mean, deviation = _deviation([particle["pos"][axis] for particle in particles])
        assert _within(deviation, 0.5 * 4.0 / 16.0), (axis, deviation)              # 像素换成格：0.5 * 4 / 16
    mean, deviation = _deviation([particle["vars"]["variable.vy"] for particle in particles])
    assert _within(mean, 4.0, 0.02) and _within(deviation, 0.5), (mean, deviation)


def testAPanParticleWithNoSpreadStaysWhereTheSceneSaidAndOnlyItsSpeedJitters():
    random.seed(5)
    particles = _panParticles(0.0, (0.0, 0.0, 0.0), 200)
    assert len(set(particle["pos"] for particle in particles)) == 1, "spread 0：起点不散"
    assert _within(_deviation([particle["vars"]["variable.vy"] for particle in particles])[1], 0.15, 0.2), "没速度的也有 0.3 的抖动（标准差 0.15）"


# ---------------------------------------------------------------- 炉灶

BASE = (10.5, 65.0, 10.5)


def _stoveParticles(spread, velocity, count, plays=1):
    world.reset()
    for _ in range(plays):
        GrillFx.play([StoveFx.Spawn("steam", 0, (0.0, 0.0, 0.0), velocity, spread, count, 0x60FFFFFF)], lambda place, offset: BASE)
    return world.particles


def testStoveParticlesOfOneBurstDoNotPileUpOnOnePoint():
    """HoD 的炉灶一次放 2~3 颗（spread 1.5 之类）：原来每颗在同一个点、只把 spread 当速度的均匀抖动；现在每颗起点各散一点（像素换成格）。"""
    random.seed(9)
    burst = _stoveParticles(1.5, (0.0, 3.0, 0.0), 3)
    assert len(burst) == 3 and len(set(particle["pos"] for particle in burst)) == 3, "三颗三个点"
    particles = _stoveParticles(1.5, (0.0, 3.0, 0.0), 3, plays=SAMPLES // 3)
    for axis in (0, 1, 2):
        mean, deviation = _deviation([particle["pos"][axis] - BASE[axis] for particle in particles])
        assert abs(mean) < 0.01 and _within(deviation, 0.5 * 1.5 / 16.0), (axis, mean, deviation)
    mean, deviation = _deviation([particle["vars"]["variable.vy"] for particle in particles])
    assert _within(mean, 3.0, 0.02) and _within(deviation, 0.5 * 0.75), "速度的抖动是 max(0.3, |v| * 0.25) 的一半，不是 spread"
    for axis in ("variable.vx", "variable.vz"):
        assert _within(_deviation([particle["vars"][axis] for particle in particles])[1], 0.5 * 0.75), axis


def testAStoveParticleWithNoSpreadStaysOnItsPointAndOnlyItsSpeedJitters():
    random.seed(13)
    particles = _stoveParticles(0.0, (0.0, 3.0, 0.0), 3, plays=60)
    assert set(particle["pos"] for particle in particles) == set([BASE]), "spread 0：不散"
    assert len(set(round(particle["vars"]["variable.vy"], 6) for particle in particles)) > 100, "速度照样抖"


# ---------------------------------------------------------------- 厨锅

def _bubbleHeights(roll):
    """一口煮着的锅放一个液内泡：返回它起点的站点高度（像素）；random.random 换成定值 roll（站点里别处的随机数也是它）。"""
    C.reset()
    PotScenes._scenes.clear()
    PotScenes.enable(BrothColors.BrothColors.get)
    scene = PotScenes.ensure(0, POS)
    scene.apply(C.look([("minecraft:carrot", 2)], heated=True, cooking=True, rate=1.0))
    for _ in range(30):
        scene.frame(1.0 / 60.0, True)
    world.particles[:] = []
    scene.liquid.emitBubbles, scene.liquid.emitSteam, scene.liquid.emitEdge = 1, 0, 0
    real = PotSceneFx.random.random
    PotSceneFx.random.random = lambda: roll
    try:
        scene.fx._particles(0.0)
    finally:
        PotSceneFx.random.random = real
    bubbles = [particle for particle in world.particles if particle["id"] == "arris_diegesis:bubble"]
    assert len(bubbles) == 1
    return scene, bubbles[0]["pos"]


def testABubbleInsideTheBrothStartsInTheLowerSixtyPercentOfTheWaterNotAnywhere():
    for roll in (0.0, 0.5, 0.999999):
        scene, where = _bubbleHeights(roll)
        floor, surface = PotSceneFx.FLOOR, scene.liquid.surfaceY()
        want = Scatter.liquidBubbleHeight(floor, surface, roll)
        assert abs(want - (floor + 0.2 + (surface - floor - 0.2) * roll * 0.6)) < 1e-9
        local = scene.world(PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * (0.15 + 0.7 * roll), want, PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * (0.15 + 0.7 * roll))
        assert all(abs(a - b) < 1e-6 for a, b in zip(where, local)), (roll, where, local)
    scene, high = _bubbleHeights(0.999999)
    top = scene.world(PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * 0.85, scene.liquid.surfaceY(), PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * 0.85)
    assert high[1] < top[1], "最高的泡也在液面下面（原来最高到液面）"


# ---------------------------------------------------------------- 液内泡（spawnInLiquid）：初速、寿命、浮到液面、水波

def _simulate(height, speed, dt=1.0 / 4000.0):
    """SceneParticles.update 的原样一步一步走（:185-186、192：重力 -6 减出向上 6 像素每二次方秒、再乘 (1 - 0.8) ^ dt、再挪），数出浮过 height 像素要多久。"""
    clock, rise = 0.0, 0.0
    while rise < height:
        speed += 6.0 * dt
        speed *= 0.2 ** dt
        rise += speed * dt
        clock += dt
    return clock


def testALiquidBubbleJittersSidewaysByAThirdOfWhatItJittersUpAndDown():
    always = lambda: 1.0                                                  # noqa: E731
    velocity = Scatter.liquidBubbleVelocity((0.0, 3.5, 0.0), always)
    assert abs(velocity[0] - 0.13125) < 1e-9 and abs(velocity[2] - 0.13125) < 1e-9 and abs(velocity[1] - 3.9375) < 1e-9, "抖动 max(0.3, 3.5 * 0.25) = 0.875，gauss 0.5：y 加 0.4375、x z 加 0.4375 * 0.3"
    random.seed(17)
    samples = [Scatter.liquidBubbleVelocity((0.0, 3.5, 0.0)) for _ in range(SAMPLES)]
    for axis, deviation in ((0, 0.13125), (1, 0.4375), (2, 0.13125)):
        mean, got = _deviation([sample[axis] for sample in samples])
        assert abs(mean - (3.5 if axis == 1 else 0.0)) < 0.03 and _within(got, deviation), (axis, mean, got)


def testALiquidBubbleLivesThreeTimesTheBubbleStylesLife():
    assert abs(Scatter.liquidBubbleLife(0.0) - 1.8) < 1e-9 and abs(Scatter.liquidBubbleLife(1.0) - 4.2) < 1e-9 and abs(Scatter.liquidBubbleLife(0.5) - 3.0) < 1e-9, "0.6 ~ 1.4 秒 * 3"


def testTheRiseTimeIsHowLongBuoyancyAndDragTakeToCarryItThroughTheWater():
    assert Scatter.riseTime(0.0, 3.5) == 0.0 and Scatter.riseTime(-1.0, 3.5) == 0.0, "已经在液面上"
    for height, speed in ((1.0, 3.5), (3.0, 3.5), (6.0, 3.5), (3.0, 3.0), (6.0, 4.4), (0.4, 2.6)):
        want = _simulate(height, speed)
        got = Scatter.riseTime(height, speed)
        assert abs(got - want) < 0.006 + 0.004 * want, (height, speed, got, want)
    assert Scatter.riseTime(2.0, 4.4) < Scatter.riseTime(2.0, 3.5) < Scatter.riseTime(2.0, 2.6) < Scatter.riseTime(5.0, 2.6), "越快越早到、越深越晚到"


def _boilingScene():
    C.reset()
    PotScenes._scenes.clear()
    PotScenes.enable(BrothColors.BrothColors.get)
    scene = PotScenes.ensure(0, POS)
    scene.apply(C.look([("minecraft:carrot", 2)], heated=True, cooking=True, rate=1.0))
    for _ in range(30):
        scene.frame(1.0 / 60.0, True)
    world.particles[:] = []
    scene.liquid.emitBubbles, scene.liquid.emitSteam, scene.liquid.emitEdge = 0, 0, 0
    del scene.fx.pops[:]
    return scene


def _bubbles():
    return [particle for particle in world.particles if particle["id"] == "arris_diegesis:bubble"]


def _rolling(rolls):
    """顶替 PotSceneFx 里的 random.random：按给定的次序一个一个吐，吐完回到真随机（别处的随机数不能把用例吃光）。"""
    queue = list(rolls)
    real = random.random
    return lambda: queue.pop(0) if queue else real()


def _spawnOne(scene, y, roll, surface=None):
    """在站点高度 y 放一个液内泡（寿命的随机数是 roll）；surface 给了就把液面抬到那儿（深水里才有浮不到顶的泡）。"""
    if surface is not None:
        scene.liquid.surfaceY = lambda: surface
    real = PotSceneFx.random.random
    PotSceneFx.random.random = _rolling([roll])
    try:
        scene.fx._bubble(8.0, 8.0, y)
    finally:
        PotSceneFx.random.random = real
    return _bubbles()[-1]


def testABubbleStartsWithTheJavaRiseAndItsSidewaysJitterAndLivesThreeTimesTheStyleLife():
    random.seed(21)
    scene = _boilingScene()
    deep = PotSceneFx.FLOOR + 40.0                                         # 深水：一个泡一辈子都浮不到顶，寿命就是它自己的 3 倍
    made = [_spawnOne(scene, PotSceneFx.FLOOR + 0.2, roll / 100.0, surface=deep) for roll in range(100)]
    lives = [bubble["vars"]["variable.life"] for bubble in made]
    assert abs(min(lives) - 1.8) < 1e-9 and abs(max(lives) - 4.2) < 0.05 and all(1.8 - 1e-9 <= life <= 4.2 + 1e-9 for life in lives), "lerp(random, 0.6, 1.4) * 3"
    assert [round(lives[roll], 6) for roll in (0, 50)] == [1.8, 3.0]
    for bubble in made:
        assert bubble["vars"]["variable.speed_set"] == 1.0, "带着自己的初速（不是粒子文件里的缺省）"
    for axis in ("variable.vx", "variable.vz"):
        mean, got = _deviation([bubble["vars"][axis] for bubble in made])
        assert abs(mean) < 0.08 and _within(got, 0.13125, 0.25), (axis, mean, got)
    mean, got = _deviation([bubble["vars"]["variable.vy"] for bubble in made])
    assert abs(mean - 3.5) < 0.12 and _within(got, 0.4375, 0.25), (mean, got)
    assert not scene.fx.pops, "一个都没浮到顶：没有要破的泡"


def testABubbleThatRunsOutOfLifeBeforeTheSurfaceJustGoesAndRingsNothing():
    random.seed(5)
    scene = _boilingScene()
    waves = []
    scene.model.ripple = lambda x, z, strength: waves.append((x, z, strength))
    _spawnOne(scene, PotSceneFx.FLOOR + 0.2, 0.0, surface=PotSceneFx.FLOOR + 40.0)
    assert not scene.fx.pops and not scene.fx.rings
    for _ in range(600):                                                   # 10 秒
        scene.fx._particles(1.0 / 60.0)
    assert waves == [] and [p for p in world.particles if p["id"] == "arris_diegesis:bubble_pop"] == [], "寿命先到：没有破泡，液面不起波"


def testABubbleThatReachesTheSurfaceEndsThereThenPopsAndOnlyWhenThePopIsOverTheLiquidRings():
    random.seed(9)
    scene = _boilingScene()
    waves = []
    scene.model.ripple = lambda x, z, strength: waves.append((x, z, strength))
    surface = scene.liquid.surfaceY()
    start = PotSceneFx.FLOOR + 0.2
    bubble = _spawnOne(scene, start, 0.99)                                 # 寿命 4.2 秒，水深只有几像素：先浮到顶
    reach = Scatter.riseTime(surface - start, bubble["vars"]["variable.vy"])
    assert abs(bubble["vars"]["variable.life"] - reach) < 1e-9 and reach < 4.2, "粒子在液面那一刻结束（它不会穿出液面）"
    assert len(scene.fx.pops) == 1
    clock, popAt, ringAt, popLife = 0.0, None, None, None
    while clock < reach + 1.5 and ringAt is None:
        scene.fx._particles(1.0 / 60.0)
        clock += 1.0 / 60.0
        pops = [p for p in world.particles if p["id"] == "arris_diegesis:bubble_pop"]
        if pops and popAt is None:
            popAt, popLife = clock, pops[0]["vars"]["variable.life"]
            assert not waves, "破泡刚冒出来，水波还没有"
        if waves:
            ringAt = clock
    assert popAt is not None and abs(popAt - reach) < 0.03, (popAt, reach)
    assert 0.45 <= popLife <= 0.85, "破泡的寿命（样式 0.45 ~ 0.85 秒）由脚本掷、告诉粒子"
    assert ringAt is not None and abs((ringAt - popAt) - popLife) < 0.03, "破泡的寿命到了才起波（SceneParticles.java:177-182）"
    assert len(waves) == 1 and abs(waves[0][2] - 0.09) < 1e-9 and waves[0][:2] == (8.0, 8.0), "POP_RIPPLE 0.09，在泡浮上来的地方"
    assert not scene.fx.pops and not scene.fx.rings


def testTheBubblesOfSomethingDissolvingStartAnywhereInTheLowerSixtyPercentLikeTheOnesOfASimmer():
    """wentIn（6 个）、cookedThrough（10 个）走的是同一个 spawnInLiquid：起点高度同样取下 60%；原来全是锅底。"""
    scene = _boilingScene()
    surface, floor = scene.liquid.surfaceY(), PotSceneFx.FLOOR
    real = PotSceneFx.random.random
    heights = []
    for roll in (0.0, 0.5, 0.999999):
        PotSceneFx.random.random = lambda roll=roll: roll
        try:
            world.particles[:] = []
            scene.fx.bubbles(1)
        finally:
            PotSceneFx.random.random = real
        origin = scene.world(PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * (0.15 + 0.7 * roll), 0.0, PotSceneFx.INNER_LO + PotSceneFx.INNER_SPAN * (0.15 + 0.7 * roll))[1]
        heights.append(_bubbles()[0]["pos"][1] - origin)
    wants = [Scatter.liquidBubbleHeight(floor, surface, roll) for roll in (0.0, 0.5, 0.999999)]
    assert wants[0] < wants[1] < wants[2] < surface
    assert all(abs(got - want / 16.0) < 1e-6 for got, want in zip(heights, wants)), (heights, wants)


# ---------------------------------------------------------------- 液面上的粒子（spawnOnLiquid）：每颗的初速各抖一次

def testTheSteamOffTheSoupGetsAJitteredRiseEachLikeSpawnDoes():
    """spawnOnLiquid 一颗颗走 spawn（SceneParticles.java:83-89），spread 0 但初速 (0, 3.2, 0) 每轴抖 gauss * max(0.3, 0.8)。"""
    random.seed(31)
    scene = _boilingScene()
    scene.liquid.emitSteam = 1
    for _ in range(SAMPLES // 4):
        scene.fx._particles(0.0)
    steam = [particle for particle in world.particles if particle["id"] == "arris_diegesis:steam"]
    assert len(steam) == SAMPLES // 4
    for axis, want in (("variable.vx", 0.0), ("variable.vy", 3.2), ("variable.vz", 0.0)):
        mean, got = _deviation([particle["vars"][axis] for particle in steam])
        assert abs(mean - want) < 0.05 and _within(got, 0.4, 0.1), (axis, mean, got)
    assert all(particle["vars"]["variable.speed_set"] == 1.0 for particle in steam)


def testTheSplashesOfALadleGoingIntoTheSoupAreJitteredOneByOne():
    random.seed(37)
    scene = _boilingScene()
    for _ in range(SAMPLES // 4):
        scene.fx.scoopSplash()
    splash = [particle for particle in world.particles if particle["id"] == "arris_diegesis:splash"]
    assert len(splash) == SAMPLES
    mean, got = _deviation([particle["vars"]["variable.vy"] for particle in splash])
    assert abs(mean - 7.0) < 0.06 and _within(got, 0.5 * 1.75, 0.1), (mean, got)
    for axis in ("variable.vx", "variable.vz"):
        mean, got = _deviation([particle["vars"][axis] for particle in splash])
        assert abs(mean) < 0.06 and _within(got, 0.5 * 1.75, 0.1), (axis, mean, got)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
