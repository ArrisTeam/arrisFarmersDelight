# -*- coding: utf-8 -*-
# runner: both
"""厨锅里清水的颜色随所在群系变（Shared/Rules/PotWater + Compat/Diegesis/PotBiome，经 PotScenes.ensure 接到场景上，假引擎）。

JE：PotBehavior.colour（1047-1049）没放料、也不是怪物锅时水是 WATER_ALPHA << 24 | BiomeColors.getAverageWaterColor(level, pos) & 0xFFFFFF，
之后才往里混倒进去的液体色和料色（那一段早就移植了，用例在 test_pot_scene.py / test_pot_liquid.py）。getAverageWaterColor 是原版的群系混合：
pos 同一高度、5 x 5 列各自群系的水色，逐通道整数平均。群系名来自客户端 GetBiomeName（假引擎按坐标回名字）。
"""
from __future__ import print_function

import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
Water = C.load("Shared.Rules.PotWater")
Table = C.load("Shared.Data.BiomeWater").BiomeWater
BrothColors = C.load("Shared.Data.BrothColors")
PotLiquid = C.load("Shared.Rules.HandsOn.PotLiquid")
LiquidColor = C.load("Shared.Rules.HandsOn.PotLiquidColor")
Tint = C.load("Shared.Rules.PotTint")
POS = C.POS
DT = 1.0 / 60.0
DEFAULT = 0xA03F76E4                    # 查不到群系时的老样子：WATER_ALPHA + 平原的 #3F76E4


def build(biome=None, at=POS, biomes=None):
    """世界里 at 处是一口锅，那一带的群系是 biome（None = 接口没答案），biomes 里写了的坐标例外；返回建好的场景。"""
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    world.biomeAll = biome
    world.biomes = dict(biomes or {})
    world.blocks[at] = ("arris:cooking_pot", 0)
    return Scenes.ensure(0, at)


def run(scene, seconds):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, True)


def channels(rgb):
    return ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)


def averageOf(parts):
    """Java 的写法（ClientLevel.calculateBlockTint）：[(0xRRGGBB, 几列)] -> 每个通道 总和 / 总列数 向下取整。"""
    total = sum(count for _color, count in parts)
    red, green, blue = (sum(channels(color)[index] * count for color, count in parts) // total for index in range(3))
    return (red << 16) | (green << 8) | blue


# ---------------------------------------------------------------- 纯规则（Shared/Rules/PotWater）

def testABiomeNameIsLookedUpWithOrWithoutTheNamespace():
    assert Water.waterOf("plains") == Water.waterOf("minecraft:plains") == 0x44AFF5
    assert Water.waterOf("swampland") == 0x617B64 and Water.waterOf("warm_ocean") == 0x02B0E5
    assert Water.waterOf("desert") != Water.waterOf("plains"), "各群系各有各的水色"


def testABiomeTheTableDoesNotKnowIsTheDefaultWater():
    assert Water.DEFAULT_BIOME_WATER == 0x3F76E4 == DEFAULT & 0xFFFFFF
    assert Water.waterOf("mymod:lava_lands") == Water.DEFAULT_BIOME_WATER, "别的模组加的群系"
    assert Water.waterOf("mymod:plains") == Water.DEFAULT_BIOME_WATER, "只有 minecraft: 的命名空间会被去掉：别人的 plains 不是平原"


def testTheBlendIsTheFiveByFiveAroundThePotAtItsOwnHeight():
    # ClientLevel.calculateBlockTint：Cursor3D(x - r, y, z - r, x + r, y, z + r)，r = 生物群系混合的缺省 2
    found = Water.columns((10, 64, 10))
    assert Water.BLEND_RADIUS == 2 and len(found) == 25 == len(set(found))
    assert sorted(set(x for x, _y, _z in found)) == [8, 9, 10, 11, 12] and sorted(set(z for _x, _y, z in found)) == [8, 9, 10, 11, 12]
    assert set(y for _x, y, _z in found) == set([64]) and (10, 64, 10) in found
    assert Water.columns((10, 64, 10), 0) == [(10, 64, 10)] and len(Water.columns((10, 64, 10), 1)) == 9


def testOnlyTheColumnsOfThePotsOwnChunkAreAsked():
    # 客户端对没加载的区块回 ocean、不回 None：锅在区块边上时，邻区块的列不取，免得把水色往海的颜色拽
    def square(xs, zs, y=64):
        return sorted((x, y, z) for x in xs for z in zs)

    assert sorted(Water.columns((0, 64, 0))) == square((0, 1, 2), (0, 1, 2)), "区块 (0, 0) 的角：5 x 5 剩 3 x 3"
    assert sorted(Water.columns((15, 70, 15))) == square((13, 14, 15), (13, 14, 15), 70)
    assert len(Water.columns((0, 64, 8))) == 15 and len(Water.columns((8, 64, 15))) == 15, "一条边上：3 x 5"
    assert sorted(Water.columns((-1, 64, -16))) == square((-3, -2, -1), (-16, -15, -14)), "负坐标向下取整：区块 (-1, -1) 是 -16 .. -1"
    assert sorted(Water.columns((16, 64, 16))) == square((16, 17, 18), (16, 17, 18))


def testTheAverageIsJavasIntegerAverageOfEveryChannel():
    def biomeAt(x, _y, _z):
        return "swampland" if x < 10 else "plains"          # 5 x 5 里 x = 8、9 两排（10 列）是沼泽，x = 10 .. 12（15 列）是平原

    found = Water.waterAt(biomeAt, (10, 64, 10))
    assert found == averageOf([(Table["swampland"], 10), (Table["plains"], 15)])
    assert channels(Table["swampland"])[2] < channels(found)[2] < channels(Table["plains"])[2], "混在两个值之间"
    assert Water.waterAt(lambda x, y, z: "plains", (10, 64, 10)) == Table["plains"], "全是一个群系：就是它的水色，不被取整带偏"


def testWhatTheEngineDoesNotAnswerIsLeftOutAndNoAnswerAtAllIsNone():
    only = {(10, 64, 10): "swampland"}
    assert Water.waterAt(lambda x, y, z: only.get((x, y, z)), (10, 64, 10)) == Table["swampland"], "只有锅那一列答上了：就是它的"
    assert Water.waterAt(lambda x, y, z: None, (10, 64, 10)) is None, "一列都没答上：留给调用方用缺省色"
    assert Water.waterAt(lambda x, y, z: "", (10, 64, 10)) is None


def testAColumnOfAnUnknownBiomeBlendsInAsTheDefaultWater():
    def biomeAt(x, _y, _z):
        return "mymod:lava_lands" if x < 10 else "plains"

    assert Water.waterAt(biomeAt, (10, 64, 10)) == averageOf([(0x3F76E4, 10), (Table["plains"], 15)])
    assert Water.waterAt(lambda x, y, z: "mymod:lava_lands", (10, 64, 10)) == 0x3F76E4


# ---------------------------------------------------------------- 场景（PotScenes.ensure -> PotBiome.bind -> PotScene.setWater）

def testAnEmptyPotsWaterIsTheWaterOfTheBiomeItStandsIn():
    for biome in ("plains", "swampland", "warm_ocean", "desert", "river", "hell", "the_end"):
        scene = build(biome)
        assert scene.water == LiquidColor.argb(LiquidColor.WATER_ALPHA, Table[biome]) == 0xA0000000 | Table[biome], biome
        scene.apply(C.look())
        assert scene.liquid.target == scene.water and scene.liquid.mottleWanted == 0.0, "空锅：汤面的目标色就是这一带的水（alpha 还是 WATER_ALPHA）"
    assert len(set(build(biome).water for biome in ("plains", "swampland", "warm_ocean", "desert"))) == 4


def testTheModelAndTheShaderGetThatWaterNotTheOldConstant():
    scene = build("swampland")
    scene.apply(C.look())
    run(scene, 0.5)
    pushed = world.uniforms[(POS, 1)]
    assert all(abs(a - b) < 1e-6 for a, b in zip(pushed, LiquidColor.toUnit(0xA0000000 | Table["swampland"]))), pushed
    assert abs(pushed[0] - 0x3F / 255.0) > 0.05, "不是平原的蓝 #3F76E4"
    assert scene.liquid.brothColor == Table["swampland"], "粒子（气泡、水花）染的也是这个颜色"


def testNothingAnsweringKeepsTheOldPlainsBlue():
    for biome in (None, "mymod:lava_lands"):
        scene = build(biome)
        assert scene.water == DEFAULT == PotLiquid.waterColor(), biome
        scene.apply(C.look())
        assert scene.liquid.target == DEFAULT


def testFoodAndPouredLiquidsStillMixIntoTheBiomeWater():
    swamp, plains = build("swampland"), build("plains")
    swamp.apply(C.look([("minecraft:carrot", 1)]))
    plains.apply(C.look([("minecraft:carrot", 1)]))
    carrot = [Tint.colorOf("minecraft:carrot")]
    assert swamp.liquid.target == LiquidColor.brothTarget(LiquidColor.waterColor(Table["swampland"]), carrot, False, 0.0, None, [], 0)[0]
    assert plains.liquid.target == LiquidColor.brothTarget(LiquidColor.waterColor(Table["plains"]), carrot, False, 0.0, None, [], 0)[0]
    assert swamp.liquid.target != plains.liquid.target, "同一根胡萝卜，水不一样，汤色也不一样"
    milk = build("swampland")
    milk.apply(C.look([("minecraft:milk_bucket", 1)], sunk=[0]))          # 刚看到时就在锅里的奶：从底色往奶色染（POURED_SHARE）
    water = LiquidColor.waterColor(Table["swampland"])
    poured = BrothColors.PouredColors["minecraft:milk_bucket"]
    assert milk.liquid.target == LiquidColor.brothTarget(water, [Tint.colorOf("minecraft:milk_bucket")], False, 0.0, None, [poured], 0)[0]


def testABystanderWhoNeverOpenedTheStationSeesTheBiomeWaterToo():
    # 场景由服务端广播（OnPotLook）或方块实体加载（ModBlockEntityLoadedClientEvent）建出来，没有任何人开站点；两条路都按所在群系给水色
    for how in ("broadcast", "loaded"):
        build("swampland")
        Scenes._scenes.clear()                                                # 要的是下面这一步来建场景，不是 build 里那一份
        if how == "broadcast":
            Scenes.OnPotLook(C.look([("minecraft:carrot", 1)]))
        else:
            Scenes.OnBlockEntityLoaded({"blockName": "arris:cooking_pot", "posX": POS[0], "posY": POS[1], "posZ": POS[2], "dimensionId": 0})
        scene = Scenes.sceneAt(0, POS)
        assert scene is not None and scene.water == 0xA0000000 | Table["swampland"], how
        if how == "broadcast":
            carrot = [Tint.colorOf("minecraft:carrot")]
            assert scene.liquid.target == LiquidColor.brothTarget(scene.water, carrot, False, 0.0, None, [], 0)[0]


def testTheEngineIsAskedOncePerSceneAndOnlyForTheColumnsOfThePotsChunk():
    scene = build("swampland")
    asked = list(world.biomeAsked)
    assert len(asked) == 25 == len(set(asked)) and set(y for _x, y, _z in asked) == set([POS[1]]), asked
    assert Scenes.ensure(0, POS) is scene and Scenes.ensure(0, POS) is scene
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 1.0)
    assert world.biomeAsked == asked, "建场景时问一次，之后（再找这口锅、状态变了、跑帧）不再问"
    corner = (0, 64, 0)
    build("swampland", corner)
    assert sorted(set((x, z) for x, _y, z in world.biomeAsked)) == [(x, z) for x in (0, 1, 2) for z in (0, 1, 2)], "区块角上的锅只问本区块的 3 x 3"


def testAPotAtABiomeBorderTakesTheBlendOfBothSides():
    swampWest = dict(((x, POS[1], z), "swampland") for x in (8, 9) for z in range(8, 13))        # 锅西边两排（10 列）是沼泽，其余平原
    scene = build("plains", biomes=swampWest)
    assert scene.water == 0xA0000000 | averageOf([(Table["swampland"], 10), (Table["plains"], 15)])
    assert Table["swampland"] != scene.water & 0xFFFFFF != Table["plains"]


def testBindingLaterRecolours():
    # setWater 在场景已经有状态时调（比如以后补问一次）：汤色的目标马上换，显示的颜色照老样子缓缓追上去
    scene = build(None)
    scene.apply(C.look())
    run(scene, 0.2)
    assert scene.liquid.target == DEFAULT
    scene.setWater(Table["swampland"])
    assert scene.liquid.target == 0xA0000000 | Table["swampland"] and scene.water == scene.liquid.target
    run(scene, 3.0)
    assert all(abs(a - b) <= 10 for a, b in zip(channels(scene.liquid.color & 0xFFFFFF), channels(Table["swampland"]))), hex(scene.liquid.color)


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
