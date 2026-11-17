# -*- coding: utf-8 -*-
# runner: both
"""煎锅、炉灶、厨锅场景的粒子散布照 Diegesis 的 SceneParticles.spawn（Shared/Rules/SceneScatter + Compat/Diegesis 的 PanFx / GrillFx / PotSceneFx）：

SceneParticles.java:68-70：起点 at + gauss * spread（每轴）、初速 velocity + gauss * max(0.3, |velocity| * 0.25)（每轴），gauss() = nextGaussian() * 0.5（:158-160，标准差是一半）；
spawnInLiquid :143：液内泡的起点高度 lerp(random * 0.6F, bottom + 0.2F, fill)，只取下 60%。
原来：煎锅的 gauss 没乘 0.5（散开一倍）；炉灶把 spread 当速度的均匀抖动、起点不散（一次 2~3 颗叠在一点）；厨锅的液内泡起点取了整段。引擎是 potclient / panclient 里的假的。"""
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


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
