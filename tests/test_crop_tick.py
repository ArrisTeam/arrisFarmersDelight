# -*- coding: utf-8 -*-
# runner: both
"""作物随机刻（Shared/Rules/CropTick.py）：脚下耕地的公式、长一级的概率、稻苗长穗、番茄沿绳子往上爬。

概率的期望值照 JE 手算（CropBlock / RiceBlock / TomatoBlock），再按 Bedrock 随机刻换算（×3 封顶 1，一级含几次转变就除以几）。
"""
from __future__ import print_function

import random

import fdtest
from farmkit import FakeWorld, ScriptRng, plot

CropTick = fdtest.load("Shared.Rules.CropTick")
CropGrowth = fdtest.load("Shared.Rules.CropGrowth")
FarmEdits = fdtest.load("Shared.Rules.FarmEdits")

CABBAGE = "arris:cabbages_stage"
ONION = "arris:onions_stage"
BUDDING = "arris:budding_tomatoes_stage"
VINE = "arris:tomatoes_vine_stage"
POS = (0, 1, 0)


def _near(a, b, eps=1e-9):
    assert abs(a - b) < eps, (a, b)


def _chances(world, prefix, pos=POS):
    return [CropTick.growChance(world, prefix, stage, pos) for stage in range(CropGrowth.lastStage(prefix) + 1)]


def _wet():
    return plot(FakeWorld(), POS)


# ---------------- 脚下 3×3 的公式 ----------------

def testSoilValuesOfEveryGround():
    w = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=7)
    assert CropTick._soilValue(w, "farmland", (0, 0, 0)) == 3.0
    w.put((1, 0, 0), "minecraft:farmland", moisture=0)
    assert CropTick._soilValue(w, "farmland", (1, 0, 0)) == 1.0
    w.put((2, 0, 0), "arris:rich_soil_farmland_moist")
    w.put((3, 0, 0), "arris:rich_soil_farmland")
    w.put((4, 0, 0), "minecraft:grass_block")
    assert [CropTick._soilValue(w, "farmland", (x, 0, 0)) for x in (2, 3, 4, 5)] == [3.0, 1.0, 0.0, 0.0]


def testCropSpeedOfCommonPlots():
    wet = _wet()
    _near(CropTick.cropSpeed(wet, CABBAGE, POS), 10.0)
    dry = plot(FakeWorld(), POS, moisture=0)
    _near(CropTick.cropSpeed(dry, CABBAGE, POS), 4.0)
    lone = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=5)
    _near(CropTick.cropSpeed(lone, CABBAGE, POS), 4.0)
    rich = plot(FakeWorld(), POS, "arris:rich_soil_farmland_moist")
    _near(CropTick.cropSpeed(rich, CABBAGE, POS), 10.0)
    richDry = plot(FakeWorld(), POS, "arris:rich_soil_farmland")
    _near(CropTick.cropSpeed(richDry, CABBAGE, POS), 4.0)


def testCropSpeedHalvesWhenSameCropOnBothAxesOrDiagonal():
    w = _wet()
    w.put((1, 1, 0), CABBAGE + "3")
    _near(CropTick.cropSpeed(w, CABBAGE, POS), 10.0)             # 只有东边一株：不减半
    w.put((0, 1, 1), CABBAGE + "0")
    _near(CropTick.cropSpeed(w, CABBAGE, POS), 5.0)              # 东、南都有：减半
    d = _wet().put((1, 1, 1), CABBAGE + "7")
    _near(CropTick.cropSpeed(d, CABBAGE, POS), 5.0)              # 只在斜角：减半
    other = _wet().put((1, 1, 0), ONION + "0").put((0, 1, 1), ONION + "1")
    _near(CropTick.cropSpeed(other, CABBAGE, POS), 10.0)         # 邻居是别的作物：不算


def testBuddingTomatoRowsOnlyCountBuddingStages():
    # JE 里 budding 与番茄是两种方块：budding 的行判断不把已经长成番茄的邻居（第 3 级起）算进去
    w = _wet().put((1, 1, 0), BUDDING + "4").put((0, 1, 1), BUDDING + "5")
    _near(CropTick.cropSpeed(w, BUDDING, POS), 10.0)
    w.put((1, 1, 0), BUDDING + "1").put((0, 1, 1), BUDDING + "2")
    _near(CropTick.cropSpeed(w, BUDDING, POS), 5.0)


# ---------------- 每族每一级的概率 ----------------

def testCabbageOnWetPlotGrowsEveryTick():
    # JE 1/3 → Bedrock 1：满湿的田里卷心菜每次随机刻长一级
    assert _chances(_wet(), CABBAGE) == [1.0] * 7 + [0.0]


def testCabbageOnLoneFarmland():
    lone = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=3)
    _near(CropTick.growChance(lone, CABBAGE, 0, POS), 3.0 / 7)      # speed 4 → 1/7
    dryLone = FakeWorld().put((0, 0, 0), "arris:rich_soil_farmland")
    _near(CropTick.growChance(dryLone, CABBAGE, 0, POS), 3.0 / 13)  # speed 2 → 1/13


def testOnionStagesNeedSeveralJeTransitions():
    # 洋葱 JE 8 个年龄合成 4 级：一级要 2 / 2 / 3 次转变，满湿田里每次 1/3
    chances = _chances(_wet(), ONION)
    _near(chances[0], 0.5)
    _near(chances[1], 0.5)
    _near(chances[2], 1.0 / 3)
    assert chances[3] == 0.0


def testOnionTotalTimeMatchesJe():
    # 平均要等的随机刻数 × 3 就是 JE 的：7 次转变，每次平均 3 个 JE 随机刻
    ticks = sum(1.0 / chance for chance in _chances(_wet(), ONION)[:3])
    _near(ticks * 3, 7 * 3.0)


def testBuddingTomatoStagesMixSoilAndTomatoChances():
    chances = _chances(_wet(), BUDDING)
    # 第 0、1 级各 1 次 CropBlock 公式（1/3 → 1）；第 2 级 budding 年龄 2→3 加上长成番茄共 2 次（→ 0.5）；
    # 第 3、4、5 级是番茄年龄 0→1→2→3，每次 1/6 → 0.5
    assert chances == [1.0, 1.0, 0.5, 0.5, 0.5, 0.5, 0.0]


def testVineGrowsAtTomatoRate():
    # 绳上的番茄 speed 固定 5：1/6 → 0.5，和脚下的田无关
    assert _chances(FakeWorld(), VINE) == [0.5, 0.5, 0.5, 0.0]
    assert _chances(_wet(), VINE) == [0.5, 0.5, 0.5, 0.0]


def testRiceGrowsAtOneThird():
    prefix = "arris:rice_stage"
    assert _chances(FakeWorld(), prefix)[:3] == [1.0, 1.0, 1.0]
    assert CropTick.growChance(FakeWorld(), prefix, 3, POS) == 0.0


def testPanicleSpeedFollowsRiceBelow():
    prefix = "arris:rice_upper_crop_stage"
    one = FakeWorld().put((0, 0, 0), "arris:rice_supporting")
    _near(CropTick.cropSpeed(one, prefix, POS), 2.0)                 # 1 + 脚下一株稻苗
    _near(CropTick.growChance(one, prefix, 0, POS), 3.0 / 13)        # JE 1/13
    paddy = FakeWorld()
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            paddy.put((dx, 0, dz), "arris:rice_stage1")
    _near(CropTick.cropSpeed(paddy, prefix, POS), 4.0)               # 1 + 1 + 8 × 1/4
    paddy.put((1, 1, 0), prefix + "0").put((0, 1, 1), prefix + "3")  # 东、南各有一株稻穗：减半
    _near(CropTick.cropSpeed(paddy, prefix, POS), 2.0)


def testTotalTimeToMaturityMatchesJeForEveryFamily():
    # 一级方块含几次 JE 转变，Bedrock 就按等待时间相加换算：从第 0 级长到最后一级平均要的随机刻数 × 3，
    # 等于 JE 把全部年龄转变走完要的随机刻数（挑一块干耕地，这样每一级的概率都不到封顶 1）
    Rates = fdtest.load("Shared.Rules.GrowthRates")
    lone = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=0)
    ricePlot = FakeWorld().put((0, 0, 0), "arris:rice_supporting")
    for prefix, spec in CropGrowth.FAMILIES.items():
        world = ricePlot if spec.get("speed") == "rice" else lone
        vanilla = Rates.vanillaChance(CropTick.cropSpeed(world, prefix, POS))
        jeTicks = 0.0
        for rate in spec["rates"]:
            if rate == "soil":
                chance = vanilla
            elif isinstance(rate, tuple):
                chance = vanilla * rate[1]
            else:
                chance = rate
            jeTicks += 1.0 / chance
        bedrockTicks = sum(1.0 / CropTick.growChance(world, prefix, stage, POS) for stage in range(CropGrowth.lastStage(prefix)))
        _near(bedrockTicks * Rates.TICK_RATIO, jeTicks, 1e-6)


def testWheatAndVanillaCropsUseTheSameFormula():
    assert _chances(_wet(), "arris:rich_soil_wheat") == [1.0] * 7 + [0.0]
    # 甜菜根、火把花苗再过一道 nextInt(3) != 0：2/3 × 1/3 = 2/9 → 3 × 2/9
    beet = _chances(_wet(), "arris:rich_soil_beetroot")
    for chance in beet[:3]:
        _near(chance, 2.0 / 3)
    torch = _chances(_wet(), "arris:rich_soil_torchflower")
    _near(torch[0], 2.0 / 3)
    _near(torch[1], 2.0 / 3)
    assert torch[2] == 0.0
    # 胡萝卜、土豆和洋葱一样 8 个年龄合 4 级
    for prefix in ("arris:rich_soil_carrots", "arris:rich_soil_potatoes"):
        chances = _chances(_wet(), prefix)
        _near(chances[0], 0.5)
        _near(chances[1], 0.5)
        _near(chances[2], 1.0 / 3)
        assert chances[3] == 0.0


# ---------------- randomTick ----------------

def testRandomTickRespectsLight():
    w = _wet().put(POS, CABBAGE + "0")
    rnd = ScriptRng(randoms=[0.0])
    assert CropTick.randomTick(w, CABBAGE + "0", POS, 8, rnd) == []
    assert CropTick.randomTick(w, CABBAGE + "0", POS, 9, rnd) == [FarmEdits.block(POS, CABBAGE + "1")]
    rice = FakeWorld().put(POS, "arris:rice_stage0")
    assert CropTick.randomTick(rice, "arris:rice_stage0", POS, 5, rnd) == []
    assert CropTick.randomTick(rice, "arris:rice_stage0", POS, 6, rnd) == [FarmEdits.block(POS, "arris:rice_stage1")]


def testRandomTickRollsAgainstTheChance():
    lone = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=3)     # 孤零零一块湿耕地：JE 1/7 → Bedrock 3/7
    for roll, grows in ((0.0, True), (0.428, True), (0.429, False), (0.99, False)):
        edits = CropTick.randomTick(lone, CABBAGE + "0", POS, 15, ScriptRng(randoms=[roll]))
        assert (edits == [FarmEdits.block(POS, CABBAGE + "1")]) == grows, roll
        assert edits == [] or len(edits) == 1


def testRandomTickIgnoresUnknownAndMatureBlocks():
    w = _wet()
    rnd = ScriptRng(randoms=[0.0])
    assert CropTick.randomTick(w, "arris:rich_soil", POS, 15, rnd) == []
    assert CropTick.randomTick(w, "arris:organic_compost_stage1", POS, 15, rnd) == []
    assert CropTick.randomTick(w, CABBAGE + "7", POS, 15, rnd) == []
    assert CropTick.randomTick(w, "arris:onions_stage3", POS, 15, rnd) == []


def testRandomTickGrowthIsStatisticallyTheChance():
    lone = FakeWorld().put((0, 0, 0), "minecraft:farmland", moisture=3)
    expected = CropTick.growChance(lone, CABBAGE, 0, POS)
    _near(expected, 3.0 / 7)
    rnd = random.Random(20261116)
    trials = 20000
    grown = sum(1 for _ in range(trials) if CropTick.randomTick(lone, CABBAGE + "0", POS, 15, rnd))
    assert abs(grown / float(trials) - expected) < 0.02, grown / float(trials)


# ---------------- 稻苗长穗 ----------------

def testRiceHeadGrowsPanicleWhenAirAbove():
    w = FakeWorld().put(POS, "arris:rice_stage3")
    edits = CropTick.randomTick(w, "arris:rice_stage3", POS, 15, ScriptRng(randoms=[0.0]))
    assert edits == [FarmEdits.block(POS, "arris:rice_supporting"), FarmEdits.block((0, 2, 0), "arris:rice_upper_crop_stage0")]
    w.put((0, 2, 0), "minecraft:water")
    assert CropTick.randomTick(w, "arris:rice_stage3", POS, 15, ScriptRng(randoms=[0.0])) == []
    assert CropTick.randomTick(w, "arris:rice_stage3", POS, 5, ScriptRng(randoms=[0.0])) == []


# ---------------- 番茄爬绳子 ----------------

def _column(base, vines=0, rope=True):
    w = FakeWorld()
    w.put((0, 1, 0), base)
    for index in range(vines):
        w.put((0, 2 + index, 0), VINE + "1")
    if rope:
        w.put((0, 2 + vines, 0), "arris:rope")
    return w


def testTomatoClimbsAtAnyStageOfTheCropButNotWhileBudding():
    for stage, climbs in ((0, False), (2, False), (3, True), (4, True), (6, True)):
        w = _column(BUDDING + str(stage))
        edits = CropTick.randomTick(w, BUDDING + str(stage), POS, 15, ScriptRng(randoms=[0.99]))
        vineEdits = [e for e in edits if e == FarmEdits.block((0, 2, 0), VINE + "0")]
        assert bool(vineEdits) == climbs, stage


def testVineClimbStopsAtThreeHangingVines():
    # 地上那株往上最多挂 3 节：0 节、1 节、2 节藤的时候最上面的一节还能再长一节，3 节就到顶
    base = BUDDING + "6"
    for vines, climbs in ((0, True), (1, True), (2, True)):
        w = _column(base, vines)
        assert (CropTick.climbEdit(w, (0, 1, 0), False) is not None) == (vines == 0)
        if vines:
            top = (0, 1 + vines, 0)
            assert (CropTick.climbEdit(w, top, True) is not None) == climbs, vines
    w = _column(base, 3)
    assert CropTick.climbEdit(w, (0, 4, 0), True) is None
    assert CropTick.climbEdit(_column(base, 0, rope=False), (0, 1, 0), False) is None


def testVineAtAnyAgeClimbsWhenRopeAbove():
    w = _column(BUDDING + "6", 1)
    edits = CropTick.randomTick(w, VINE + "1", (0, 2, 0), 15, ScriptRng(randoms=[0.99]))
    assert FarmEdits.block((0, 3, 0), VINE + "0") in edits
    # 光照不够的时候什么都不做（连爬绳子也不爬）
    assert CropTick.randomTick(w, VINE + "1", (0, 2, 0), 8, ScriptRng(randoms=[0.0])) == []


def testGrowthAndClimbHappenInTheSameTick():
    w = _column(BUDDING + "5")
    edits = CropTick.randomTick(w, BUDDING + "5", POS, 15, ScriptRng(randoms=[0.0]))
    assert edits == [FarmEdits.block(POS, BUDDING + "6"), FarmEdits.block((0, 2, 0), VINE + "0")]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
