# -*- coding: utf-8 -*-
# runner: both
"""骨粉的效果（Shared/Rules/BoneMealRules.py、WildSpread.py、ColonyRules.py）照 JE 的 BonemealableBlock。

每个用例用 ScriptRng 指定随机数（randint 依次取 ints，夹进区间；random 取 randoms），覆盖每个分支和边界。
"""
from __future__ import print_function

import random

import fdtest
from farmkit import FakeWorld, ScriptRng

Bone = fdtest.load("Shared.Rules.BoneMealRules")
Wild = fdtest.load("Shared.Rules.WildSpread")
Colony = fdtest.load("Shared.Rules.ColonyRules")
FarmEdits = fdtest.load("Shared.Rules.FarmEdits")

POS = (0, 1, 0)
CABBAGE = "arris:cabbages_stage"
ONION = "arris:onions_stage"
BUDDING = "arris:budding_tomatoes_stage"
VINE = "arris:tomatoes_vine_stage"
RICE = "arris:rice_stage"
PANICLE = "arris:rice_upper_crop_stage"


def _stageAfter(name, world=None, ints=(), randoms=(0.0,), pos=POS):
    """用一次骨粉，返回 (valid, 该位置之后的方块名)；规则没改这一格就返回原名。"""
    world = world or FakeWorld().put(pos, name)
    valid, edits = Bone.boneMeal(world, name, pos, ScriptRng(randoms=randoms, ints=ints))
    after = dict((edit[1], edit[2]) for edit in edits if edit[0] == FarmEdits.BLOCK)
    return valid, after.get(pos, name)


# ---------------- 普通作物 ----------------

def testCabbageGrowsTwoToFiveStages():
    # CropBlock.getBonemealAgeIncrease：nextInt(2, 5)
    for inc in (2, 3, 4, 5):
        assert _stageAfter(CABBAGE + "0", ints=[inc]) == (True, CABBAGE + str(inc))
    assert _stageAfter(CABBAGE + "4", ints=[5]) == (True, CABBAGE + "7")      # 不超过最大阶段
    assert _stageAfter(CABBAGE + "7", ints=[5]) == (False, CABBAGE + "7")     # 已经成熟：不是合法目标，不用骨粉


def testOnionIncreaseIsCountedInJeAges():
    # 洋葱第 0 级是 JE 年龄 0、1：ints = [级内的年龄, 增量]
    assert _stageAfter(ONION + "0", ints=[0, 2]) == (True, ONION + "1")     # 0+2 = 2 → 第 1 级
    assert _stageAfter(ONION + "0", ints=[1, 2]) == (True, ONION + "1")     # 1+2 = 3 → 第 1 级
    assert _stageAfter(ONION + "0", ints=[0, 5]) == (True, ONION + "2")     # 5 → 第 2 级
    assert _stageAfter(ONION + "0", ints=[1, 5]) == (True, ONION + "2")     # 6 → 第 2 级（年龄 7 才是成熟）
    assert _stageAfter(ONION + "1", ints=[3, 5]) == (True, ONION + "3")     # 3+5 → 封顶 7 → 成熟
    assert _stageAfter(ONION + "2", ints=[4, 3]) == (True, ONION + "3")     # 4+3 = 7
    assert _stageAfter(ONION + "2", ints=[4, 2]) == (True, ONION + "2")     # 4+2 = 6 还在第 2 级：合法但没变
    assert _stageAfter(ONION + "3", ints=[0, 5]) == (False, ONION + "3")


def testAverageOnionBoostMatchesCabbage():
    # 增量按 JE 年龄算，所以洋葱平均一次骨粉推进的年龄和卷心菜一样（头几级里没有封顶）
    rnd = random.Random(5)
    total = 0.0
    trials = 4000
    for _ in range(trials):
        valid, edits = Bone.boneMeal(FakeWorld(), ONION + "0", POS, rnd)
        assert valid
        stage = int(edits[0][2][-1])
        total += (0, 2, 4, 7)[stage]            # 新的级对应的起始年龄
    assert 2.5 < total / trials < 4.5


def testBeetrootAndTorchflowerAndWheat():
    beet = "arris:rich_soil_beetroot"
    assert _stageAfter(beet + "0", ints=[2]) == (True, beet + "0")      # nextInt(2, 5) / 3：2 → 0
    assert _stageAfter(beet + "0", ints=[3]) == (True, beet + "1")
    assert _stageAfter(beet + "0", ints=[5]) == (True, beet + "1")
    assert _stageAfter(beet + "3", ints=[5]) == (False, beet + "3")
    torch = "arris:rich_soil_torchflower"
    assert _stageAfter(torch + "0") == (True, torch + "1")             # 每次 +1，第 2 级是开花的火把花
    assert _stageAfter(torch + "1") == (True, torch + "2")
    assert _stageAfter(torch + "2") == (False, torch + "2")
    wheat = "arris:rich_soil_wheat"
    assert _stageAfter(wheat + "1", ints=[4]) == (True, wheat + "5")


# ---------------- 番茄 ----------------

def _tomatoColumn(base, vines=(), rope=True):
    world = FakeWorld().put(POS, base)
    for index, vine in enumerate(vines):
        world.put((0, 2 + index, 0), vine)
    if rope:
        world.put((0, 2 + len(vines), 0), "arris:rope")
    return world


def testBuddingTomatoUsesOneToFourOnTheAgeAxis():
    # BuddingTomatoBlock.performBonemeal：年龄轴 0-7（budding 0-3 接番茄 0-3）+ nextInt(1, 4)
    assert _stageAfter(BUDDING + "0", ints=[1]) == (True, BUDDING + "1")
    assert _stageAfter(BUDDING + "0", ints=[3]) == (True, BUDDING + "2")       # 年龄 3 并在第 2 级
    assert _stageAfter(BUDDING + "0", ints=[4]) == (True, BUDDING + "3")       # 年龄 4 = 番茄年龄 0
    assert _stageAfter(BUDDING + "1", ints=[4]) == (True, BUDDING + "4")
    assert _stageAfter(BUDDING + "2", ints=[3, 1]) == (True, BUDDING + "3")    # 级内年龄 3 + 1
    assert _stageAfter(BUDDING + "2", ints=[2, 1]) == (True, BUDDING + "2")    # 2 + 1 = 3 还是第 2 级
    assert _stageAfter(BUDDING + "2", ints=[3, 4]) == (True, BUDDING + "6")    # 3 + 4 = 7 成熟


def testTomatoCropGrowsOneOrTwo():
    # TomatoBlock：nextInt(2, 5) / 2 = 1 或 2；长了以后 30% 顺手往绳上爬
    base = BUDDING + "4"
    world = _tomatoColumn(base)
    valid, edits = Bone.boneMeal(world, base, POS, ScriptRng(randoms=[0.5], ints=[3]))
    assert valid and edits == [FarmEdits.block(POS, BUDDING + "5")]
    valid, edits = Bone.boneMeal(world, base, POS, ScriptRng(randoms=[0.5], ints=[5]))
    assert edits == [FarmEdits.block(POS, BUDDING + "6")]
    valid, edits = Bone.boneMeal(world, base, POS, ScriptRng(randoms=[0.29], ints=[2]))
    assert edits == [FarmEdits.block(POS, BUDDING + "5"), FarmEdits.block((0, 2, 0), VINE + "0")]
    valid, edits = Bone.boneMeal(world, base, POS, ScriptRng(randoms=[0.3], ints=[2]))
    assert edits == [FarmEdits.block(POS, BUDDING + "5")]


def testTomatoThatWouldOvershootClimbsInstead():
    # 年龄 2 的番茄 + 2 = 4 > 3：JE 不把它长满，改去爬绳子 / 催上面的藤
    base = BUDDING + "5"
    valid, edits = Bone.boneMeal(_tomatoColumn(base), base, POS, ScriptRng(ints=[5]))
    assert valid and edits == [FarmEdits.block((0, 2, 0), VINE + "0")]
    valid, edits = Bone.boneMeal(_tomatoColumn(base, rope=False), base, POS, ScriptRng(ints=[5]))
    assert valid and edits == []                    # 没有绳子也没有藤：骨粉照样用掉，什么都没发生
    world = _tomatoColumn(base, [VINE + "1"])
    valid, edits = Bone.boneMeal(world, base, POS, ScriptRng(randoms=[0.9], ints=[5, 3]))
    assert valid and edits == [FarmEdits.block((0, 2, 0), VINE + "2")]      # 催上面的藤（藤的增量 3 // 2 = 1）


def testMatureTomatoNeedsRopeOrYoungVineAbove():
    base = BUDDING + "6"
    assert Bone.boneMeal(_tomatoColumn(base, rope=False), base, POS, ScriptRng())[0] is False
    valid, edits = Bone.boneMeal(_tomatoColumn(base), base, POS, ScriptRng())
    assert valid and edits == [FarmEdits.block((0, 2, 0), VINE + "0")]
    # 上面有熟了的藤，再上面是绳子：合法（藤是熟的，继续看第二格）
    ripe = _tomatoColumn(base, [VINE + "3"])
    valid, edits = Bone.boneMeal(ripe, base, POS, ScriptRng())
    assert valid
    # 上面是熟藤、再上面不是绳子：不合法
    assert Bone.boneMeal(_tomatoColumn(base, [VINE + "3"], rope=False), base, POS, ScriptRng())[0] is False
    # 上面是没熟的藤：合法
    assert Bone.boneMeal(_tomatoColumn(base, [VINE + "2"], rope=False), base, POS, ScriptRng())[0] is True


def testVineGrowsAndClimbsLikeTheCrop():
    world = _tomatoColumn(BUDDING + "6", [VINE + "0"])
    pos = (0, 2, 0)
    valid, edits = Bone.boneMeal(world, VINE + "0", pos, ScriptRng(randoms=[0.9], ints=[4]))
    assert valid and edits == [FarmEdits.block(pos, VINE + "2")]
    valid, edits = Bone.boneMeal(world, VINE + "3", pos, ScriptRng())
    assert valid                                    # 熟藤上面是绳子：合法
    world2 = _tomatoColumn(BUDDING + "6", [VINE + "3"], rope=False)
    assert Bone.boneMeal(world2, VINE + "3", pos, ScriptRng())[0] is False


# ---------------- 稻米 ----------------

def testRiceGrowsOneToFour():
    world = FakeWorld().put(POS, RICE + "0")
    for inc, stage in ((1, "1"), (3, "3")):
        valid, edits = Bone.boneMeal(world, RICE + "0", POS, ScriptRng(ints=[inc]))
        assert valid and edits == [FarmEdits.block(POS, RICE + stage)]


def testRiceOverflowGrowsPanicleAboveOrFeedsTheOneThere():
    # 稻苗年龄 + 增量超过 3：上面是空气就长出稻穗（年龄 = 超出的部分 - 1），下半变成 rice_supporting
    world = FakeWorld().put(POS, RICE + "3")
    valid, edits = Bone.boneMeal(world, RICE + "3", POS, ScriptRng(ints=[1]))
    assert valid and edits == [FarmEdits.block(POS, "arris:rice_supporting"), FarmEdits.block((0, 2, 0), PANICLE + "0")]
    valid, edits = Bone.boneMeal(world, RICE + "3", POS, ScriptRng(ints=[4]))
    assert edits == [FarmEdits.block(POS, "arris:rice_supporting"), FarmEdits.block((0, 2, 0), PANICLE + "3")]
    # 上面已经有没熟的稻穗：催稻穗（nextInt(2, 5) / 3：5 → +1）
    world.put((0, 2, 0), PANICLE + "1")
    valid, edits = Bone.boneMeal(world, "arris:rice_supporting", POS, ScriptRng(ints=[4, 5]))
    assert valid and edits == [FarmEdits.block((0, 2, 0), PANICLE + "2")]
    valid, edits = Bone.boneMeal(world, "arris:rice_supporting", POS, ScriptRng(ints=[4, 2]))
    assert valid and edits == [FarmEdits.block((0, 2, 0), PANICLE + "1")]       # 2 // 3 = 0：这次没长
    # 稻穗熟了：不是合法目标
    world.put((0, 2, 0), PANICLE + "3")
    assert Bone.boneMeal(world, "arris:rice_supporting", POS, ScriptRng(ints=[4]))[0] is False
    assert Bone.boneMeal(world, RICE + "3", POS, ScriptRng(ints=[4]))[0] is False
    # 上面是别的东西挡着：合法但长不出来
    world.put((0, 2, 0), "minecraft:water")
    assert Bone.boneMeal(world, RICE + "3", POS, ScriptRng(ints=[4])) == (True, [])


def testPanicleBoneMeal():
    world = FakeWorld().put(POS, PANICLE + "0")
    valid, edits = Bone.boneMeal(world, PANICLE + "0", POS, ScriptRng(ints=[3]))
    assert valid and edits == [FarmEdits.block(POS, PANICLE + "1")]
    valid, edits = Bone.boneMeal(world, PANICLE + "0", POS, ScriptRng(ints=[2]))
    assert valid and edits == [FarmEdits.block(POS, PANICLE + "0")]
    assert Bone.boneMeal(world, PANICLE + "3", POS, ScriptRng(ints=[5]))[0] is False


# ---------------- 蘑菇菌落 ----------------

def testColonyBoneMealMovesBetweenJeAges():
    for color in ("brown", "red"):
        name = "arris:%s_mushroom_colony" % color
        world = FakeWorld().put(POS, name, growth=2)
        valid, edits = Bone.boneMeal(world, name, POS, ScriptRng(ints=[1]))
        assert valid and edits == [FarmEdits.states(POS, {"arris:growth": 4})]
        valid, edits = Bone.boneMeal(world, name, POS, ScriptRng(ints=[2]))
        assert edits == [FarmEdits.states(POS, {"arris:growth": 6})]
        world.put(POS, name, growth=6)
        valid, edits = Bone.boneMeal(world, name, POS, ScriptRng(ints=[2]))
        assert edits == [FarmEdits.states(POS, {"arris:growth": 7})]           # 年龄封顶 3
        world.put(POS, name, growth=7)
        assert Bone.boneMeal(world, name, POS, ScriptRng()) == (False, [])
        world.put(POS, name, growth=0)                                          # 刚放下的单个蘑菇外观：年龄 0
        assert Bone.boneMeal(world, name, POS, ScriptRng(ints=[1]))[1] == [FarmEdits.states(POS, {"arris:growth": 4})]


# ---------------- 野生作物 / 沙地灌木 ----------------

def _flatland(name, radius=6):
    world = FakeWorld().put(POS, name)
    for x in range(-radius, radius + 1):
        for z in range(-radius, radius + 1):
            world.put((x, 0, z), "minecraft:dirt")
    world.put(POS, name)
    return world


def testWildCropSpreadsOneCopyWithEightyPercent():
    name = "arris:wild_cabbages"
    world = _flatland(name)
    # 游走全朝 +x（randint 依次是 x:2 → +1，y:1 - 1 → 0，z:1 → 0）：5 步以后落在 (5, 1, 0)
    step = [2, 1, 1, 1]
    valid, edits = Bone.boneMeal(world, name, POS, ScriptRng(randoms=[0.79], ints=step * 5))
    assert valid and edits == [FarmEdits.block((5, 1, 0), name)]
    # 80% 的成功率：0.8 不算成功，但骨粉照样用掉
    assert Bone.boneMeal(world, name, POS, ScriptRng(randoms=[0.8], ints=step * 5)) == (True, [])


def testWildCropSpreadStopsAtTenNeighbours():
    name = "arris:wild_onions"
    world = _flatland(name)
    for index in range(9):                      # 加上自己 10 株
        world.put((index - 4, 1, 3), name)
    assert Wild.wildCropEdits(world, name, POS, ScriptRng(ints=[2, 1, 1, 1] * 5)) == []
    world.put((0, 1, 3), "minecraft:air")      # 少一株就可以长
    assert len(Wild.wildCropEdits(world, name, POS, ScriptRng(ints=[2, 1, 1, 1] * 5))) == 1


def testWildCropNeedsAirAndAllowedGround():
    name = "arris:wild_potatoes"
    world = _flatland(name)
    world.put((1, 0, 0), "minecraft:stone")     # 第一步的落点脚下是石头：不能种，也不挪过去
    edits = Wild.wildCropEdits(world, name, POS, ScriptRng(ints=[2, 1, 1, 1] * 5))
    assert edits == []                          # 之后每一步都还是 (1,1,0)：脚下是石头，最后落点同样不行
    world.put((1, 0, 0), "minecraft:dirt").put((1, 1, 0), "minecraft:stone")
    assert Wild.wildCropEdits(world, name, POS, ScriptRng(ints=[2, 1, 1, 1] * 5)) == []   # 落点被占了


def testWildRiceDropsItselfWithThirtyPercent():
    world = FakeWorld().put(POS, "arris:wild_rice")
    valid, edits = Bone.boneMeal(world, "arris:wild_rice", POS, ScriptRng(randoms=[0.29]))
    assert valid and edits == [FarmEdits.drop(POS, "arris:wild_rice", 1)]
    assert Bone.boneMeal(world, "arris:wild_rice", POS, ScriptRng(randoms=[0.3])) == (True, [])


def testSandyShrubScattersOnSandOnly():
    world = FakeWorld().put(POS, "arris:sandy_shrub")
    for x in range(-8, 9):
        for z in range(-8, 9):
            world.put((x, 0, z), "minecraft:sand" if x % 2 == 0 else "minecraft:grass_block")
    world.put(POS, "arris:sandy_shrub")
    valid, edits = Bone.boneMeal(world, "arris:sandy_shrub", POS, random.Random(3))
    assert valid and edits
    cells = [edit[1] for edit in edits]
    assert len(cells) == len(set(cells)) and len(cells) <= Wild.SHRUB_TRIES
    for edit in edits:
        x, y, z = edit[1]
        assert edit[2] == "arris:sandy_shrub"
        assert world.nameAt((x, y, z)) == "minecraft:air"
        assert world.nameAt((x, y - 1, z)) in Wild.SAND
        # random_patch 的范围：水平 ±2、竖直 ±3，中心是灌木上方一格
        assert abs(x) <= 2 and abs(z) <= 2 and abs(y - 2) <= 3


def testUnknownBlocksAreNotTargets():
    world = FakeWorld().put(POS, "minecraft:stone")
    assert Bone.boneMeal(world, "minecraft:stone", POS, ScriptRng()) == (False, [])
    assert Bone.boneMeal(world, "arris:rich_soil", POS, ScriptRng()) == (False, [])
    assert Bone.boneMeal(world, "arris:organic_compost_stage1", POS, ScriptRng()) == (False, [])


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
