# -*- coding: utf-8 -*-
# runner: both
"""种植的服务端模块（Server/Crops、CropTicks、BoneMeal、RichSoil、OrganicCompost、MushroomColony、Straw）对着假引擎跑一遍。

规则本身在 test_crop_tick / test_bone_meal_rules / test_farm_misc_rules 里测过；这里管的是接线：
事件参数的字段名、注册表的匹配、读世界 / 写世界的接口调用、随机数用在哪、特效和扣骨粉。
"""
from __future__ import print_function

import fdtest
import farmengine
from farmkit import ScriptRng

LEVEL = farmengine.Level()
farmengine.install(LEVEL)

Registry = fdtest.load("Server.EventRegistry")
Crops = fdtest.load("Server.Crops")
CropTicks = fdtest.load("Server.CropTicks")
BoneMeal = fdtest.load("Server.BoneMeal")
RichSoil = fdtest.load("Server.RichSoil")
OrganicCompost = fdtest.load("Server.OrganicCompost")
MushroomColony = fdtest.load("Server.MushroomColony")
Straw = fdtest.load("Server.Straw")
Farming = fdtest.load("Shared.Data.Farming")

TICK = "BlockRandomTickServerEvent"
FARMLAND = "minecraft:farmland"
CABBAGE = "arris:cabbages_stage"


def _fresh():
    LEVEL.__init__()
    return LEVEL


def _tick(name, pos, light=15, dim=0):
    args = {"fullName": name, "blockName": name, "posX": pos[0], "posY": pos[1], "posZ": pos[2], "dimensionId": dim,
            "brightness": light, "auxValue": 0}
    Registry.dispatch(TICK, args, name)


def _plot(level, y=0, moisture=7):
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            level.put((dx, y, dz), FARMLAND, moisturized_amount=moisture)
    return level


def _rng(*randoms, **kwargs):
    return ScriptRng(randoms=list(randoms) or [0.0], ints=kwargs.get("ints", ()))


def _patchRandom(rnd, *modules):
    for module in modules:
        module.random = rnd


# ---------------- 作物随机刻 ----------------

def testCropRandomTickGrowsOnWetFarmland():
    level = _plot(_fresh()).put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.0), CropTicks)
    _tick(CABBAGE + "0", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "1"
    assert level.setCalls[-1][4] is False                       # 长一级不通知邻居
    _tick(CABBAGE + "1", (0, 1, 0), light=8)                    # 光照不够
    assert level.nameAt((0, 1, 0)) == CABBAGE + "1"


def testWetPlotChanceIsExactlyOne():
    # 满湿的 3×3 田：JE 1/3 → Bedrock 每刻必长（最大值 1，随机数取 0.999999 也长）
    level = _plot(_fresh()).put((0, 1, 0), CABBAGE + "2")
    _patchRandom(_rng(0.999999), CropTicks)
    _tick(CABBAGE + "2", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "3"


def testLoneDryFarmlandIsSlow():
    level = _fresh().put((0, 0, 0), FARMLAND, moisturized_amount=0).put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.2), CropTicks)                          # JE 1/13 → 3/13 ≈ 0.2308
    _tick(CABBAGE + "0", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "1"
    level.put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.25), CropTicks)
    _tick(CABBAGE + "0", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "0"


def testRiceHeadsAndTomatoClimbsViaTheRegistry():
    level = _fresh().put((0, 1, 0), "arris:rice_stage3")
    _patchRandom(_rng(0.0), CropTicks)
    _tick("arris:rice_stage3", (0, 1, 0), light=6)
    assert level.nameAt((0, 1, 0)) == "arris:rice_supporting" and level.nameAt((0, 2, 0)) == "arris:rice_upper_crop_stage0"
    level = _fresh().put((0, 1, 0), "arris:budding_tomatoes_stage6").put((0, 2, 0), "arris:rope")
    _tick("arris:budding_tomatoes_stage6", (0, 1, 0))
    assert level.nameAt((0, 2, 0)) == "arris:tomatoes_vine_stage0"


def testDownstreamCropsKeepTheOldRule():
    level = _fresh().put((0, 1, 0), "test:corn0")
    Farming.cropsDict["test:corn0"] = "test:corn1"
    Farming.cropsDict["test:corn1"] = ""
    try:
        _tick("test:corn0", (0, 1, 0), light=8)
        assert level.nameAt((0, 1, 0)) == "test:corn0"
        _tick("test:corn0", (0, 1, 0), light=9)
        assert level.nameAt((0, 1, 0)) == "test:corn1"
        _tick("test:corn1", (0, 1, 0), light=15)
        assert level.nameAt((0, 1, 0)) == "test:corn1"
    finally:
        del Farming.cropsDict["test:corn0"]
        del Farming.cropsDict["test:corn1"]


# ---------------- 骨粉 ----------------

def testBoneMealOnCabbage():
    level = _fresh().put((0, 1, 0), CABBAGE + "0")
    item = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 3}
    _patchRandom(_rng(0.0, ints=[4]), BoneMeal)
    assert BoneMeal.ApplyBoneMeal("p1", item, CABBAGE + "0", (0, 1, 0), 0) is True
    assert level.nameAt((0, 1, 0)) == CABBAGE + "4"
    assert item["count"] == 2
    assert level.sounds[-1][2] == "item.bone_meal.use" and level.particles
    ripe = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 3}
    level.put((0, 1, 0), CABBAGE + "7")
    assert BoneMeal.ApplyBoneMeal("p1", ripe, CABBAGE + "7", (0, 1, 0), 0) is False
    assert ripe["count"] == 3                                  # 成熟了：不是合法目标，不扣骨粉


def testBoneMealOnWildCropUsesTheItemEvenWhenItDoesNotSpread():
    level = _fresh().put((0, 1, 0), "arris:wild_onions")
    item = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 1}
    _patchRandom(_rng(0.9), BoneMeal)                          # 80% 的成功率没过
    assert BoneMeal.ApplyBoneMeal("p1", item, "arris:wild_onions", (0, 1, 0), 0) is True
    assert item["count"] == 0 and level.entities == []


def testBoneMealOnWildRiceDropsAnItem():
    level = _fresh().put((0, 1, 0), "arris:wild_rice")
    item = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 1}
    _patchRandom(_rng(0.1), BoneMeal)
    assert BoneMeal.ApplyBoneMeal("p1", item, "arris:wild_rice", (0, 1, 0), 0) is True
    assert level.entities[0][0]["itemName"] == "arris:wild_rice"


def testBoneMealOnColonySetsTheGrowthState():
    level = _fresh().put((0, 1, 0), "arris:red_mushroom_colony", **{"arris:growth": 2})
    item = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 1}
    _patchRandom(_rng(0.0, ints=[2]), BoneMeal)
    assert BoneMeal.ApplyBoneMeal("p1", item, "arris:red_mushroom_colony", (0, 1, 0), 0) is True
    assert level.statesAt((0, 1, 0))["arris:growth"] == 6


# ---------------- 沃土 / 沃土耕地 ----------------

def _richFarmland(level, name="arris:rich_soil_farmland_moist"):
    level.put((0, 0, 0), name).put((0, 1, 0), CABBAGE + "0")
    return level


def testMoistRichFarmlandBoostsThePlantAboveWithTwentyPercent():
    level = _richFarmland(_fresh())
    level.water = set([(0, 3, 0, 0)])                            # (维度, x, y, z)：水平 3 格外的水
    _patchRandom(_rng(0.59, ints=[2]), RichSoil, BoneMeal)       # 20% × 3 = 0.6：0.59 催熟
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "2" and level.particles
    level.put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.6, ints=[2]), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 1, 0)) == CABBAGE + "0"


def testRichFarmlandDoesNotBoostUnaffectedPlants():
    level = _fresh().put((0, 0, 0), "arris:rich_soil_farmland_moist").put((0, 1, 0), "arris:wild_carrots")
    level.water = set([(0, 1, 0, 0)])
    _patchRandom(_rng(0.0), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 1, 0)) == "arris:wild_carrots" and not level.particles


def testDryRichFarmlandBecomesMoistNearWaterWithoutBoosting():
    level = _richFarmland(_fresh(), "arris:rich_soil_farmland")
    _patchRandom(_rng(0.0, ints=[5]), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland", (0, 0, 0))                # 没有水：不变
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland"
    level.water = set([(0, 4, 1, 4)])                           # 水平 4 格、高一层：算
    _tick("arris:rich_soil_farmland", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland_moist"
    assert level.nameAt((0, 1, 0)) == CABBAGE + "0"             # 干的不催熟，变湿也不催熟
    level.put((0, 0, 0), "arris:rich_soil_farmland")
    level.water = set([(0, 5, 0, 0)])                           # 5 格：太远
    _tick("arris:rich_soil_farmland", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland"


def testMoistRichFarmlandDriesWithoutWaterOrRain():
    level = _richFarmland(_fresh())
    _patchRandom(_rng(0.42), RichSoil, BoneMeal)                # 3/7 ≈ 0.4286
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland"
    level.put((0, 0, 0), "arris:rich_soil_farmland_moist")
    _patchRandom(_rng(0.43), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland_moist"
    # 下雨且头顶没有遮挡：湿润保持，并且可以催熟
    level.raining = True
    level.put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.0, ints=[3]), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland_moist" and level.nameAt((0, 1, 0)) == CABBAGE + "3"
    # 头顶有房顶：雨淋不到，干掉
    level.put((0, 4, 0), "minecraft:stone").put((0, 1, 0), CABBAGE + "0")
    _patchRandom(_rng(0.0), RichSoil, BoneMeal)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0))
    assert level.nameAt((0, 0, 0)) == "arris:rich_soil_farmland"
    # 别的维度下雨不算
    level = _richFarmland(_fresh())
    level.raining = True
    level.put((0, 0, 0), "arris:rich_soil_farmland_moist", 1).put((0, 1, 0), CABBAGE + "0", 1)
    _tick("arris:rich_soil_farmland_moist", (0, 0, 0), dim=1)
    assert level.nameAt((0, 0, 0), 1) == "arris:rich_soil_farmland"


def testRichSoilTurnsMushroomsIntoColonies():
    for mushroom, colony in (("minecraft:brown_mushroom", "arris:brown_mushroom_colony"),
                             ("minecraft:red_mushroom", "arris:red_mushroom_colony")):
        level = _fresh().put((0, 0, 0), "arris:rich_soil").put((0, 1, 0), mushroom)
        _patchRandom(_rng(0.99), RichSoil, BoneMeal)
        _tick("arris:rich_soil", (0, 0, 0))
        assert level.nameAt((0, 1, 0)) == colony
        assert level.statesAt((0, 1, 0))["arris:growth"] == 2        # 年龄 0 的外观
    # 非农田的沃土也 20% 催熟上面的稻苗之类
    level = _fresh().put((0, 0, 0), "arris:rich_soil").put((0, 1, 0), "arris:rice_stage0")
    _patchRandom(_rng(0.0, ints=[3]), RichSoil, BoneMeal)
    _tick("arris:rich_soil", (0, 0, 0))
    assert level.nameAt((0, 1, 0)) == "arris:rice_stage3"


# ---------------- 有机肥 / 蘑菇菌落 ----------------

def testOrganicCompostAdvancesWithTheJeChance():
    level = _fresh().put((0, 1, 0), "arris:organic_compost_stage0")
    _patchRandom(_rng(0.179), OrganicCompost)                    # 露天、只有自己一个催化剂：0.12 × 3 / 2 = 0.18
    _tick("arris:organic_compost_stage0", (0, 1, 0), light=0)    # 暗处也照长（没有光照条件）
    assert level.nameAt((0, 1, 0)) == "arris:organic_compost_stage1"     # 且只前进一格（没被通用作物处理再推一次）
    _patchRandom(_rng(0.181), OrganicCompost)
    _tick("arris:organic_compost_stage1", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == "arris:organic_compost_stage1"
    level.water.add((0, 1, 1, 0))                                # 旁边有水：0.22 × 3 / 2 = 0.33
    _patchRandom(_rng(0.329), OrganicCompost)
    _tick("arris:organic_compost_stage1", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == "arris:organic_compost_stage2"


def testOrganicCompostCountsActivatorsAndCover():
    level = _fresh().put((0, 1, 0), "arris:organic_compost_stage3")
    level.fill("minecraft:stone", (-1, 4, -1), (1, 4, 1))        # 3×3 都被盖住：0.05 + 0.02 = 0.07 → 0.105
    _patchRandom(_rng(0.104), OrganicCompost)
    _tick("arris:organic_compost_stage3", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == "arris:rich_soil"
    level.put((0, 1, 0), "arris:organic_compost_stage3")
    _patchRandom(_rng(0.106), OrganicCompost)
    _tick("arris:organic_compost_stage3", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == "arris:organic_compost_stage3"
    level.put((1, 1, 0), "minecraft:brown_mushroom").put((0, 0, 1), "minecraft:mycelium")      # 两个催化剂：0.11 → 0.165
    _patchRandom(_rng(0.164), OrganicCompost)
    _tick("arris:organic_compost_stage3", (0, 1, 0))
    assert level.nameAt((0, 1, 0)) == "arris:rich_soil"


def testMushroomColonyGrowsOnlyOnRichSoil():
    for ground, grows in (("arris:rich_soil", True), ("minecraft:dirt", False), ("arris:organic_compost_stage2", False)):
        level = _fresh().put((0, 0, 0), ground).put((0, 1, 0), "arris:brown_mushroom_colony", **{"arris:growth": 2})
        _patchRandom(_rng(0.74), MushroomColony)                # 25% × 3 = 0.75
        _tick("arris:brown_mushroom_colony", (0, 1, 0))
        assert level.statesAt((0, 1, 0))["arris:growth"] == (4 if grows else 2), ground
    level = _fresh().put((0, 0, 0), "arris:rich_soil").put((0, 1, 0), "arris:red_mushroom_colony", **{"arris:growth": 6})
    _patchRandom(_rng(0.76), MushroomColony)
    _tick("arris:red_mushroom_colony", (0, 1, 0))
    assert level.statesAt((0, 1, 0))["arris:growth"] == 6        # 没过 75%
    _patchRandom(_rng(0.1), MushroomColony)
    _tick("arris:red_mushroom_colony", (0, 1, 0))
    _tick("arris:red_mushroom_colony", (0, 1, 0))
    assert level.statesAt((0, 1, 0))["arris:growth"] == 7        # 满龄不再长


def _use(name, pos, player="p1"):
    args = {"blockName": name, "x": pos[0], "y": pos[1], "z": pos[2], "dimensionId": 0, "playerId": player, "face": 1}
    Registry.dispatch("ServerBlockUseEvent", args, name)
    return args


def testShearsAndKnifeHarvestAColony():
    level = _fresh().put((0, 1, 0), "arris:brown_mushroom_colony", **{"arris:growth": 7})
    _hold(level, "p1", "minecraft:shears")
    args = _use("arris:brown_mushroom_colony", (0, 1, 0))
    assert level.statesAt((0, 1, 0))["arris:growth"] == 6 and args["cancel"] is True
    assert [(e[0]["itemName"], e[0]["count"]) for e in level.entities] == [("minecraft:brown_mushroom", 1)]
    assert level.sounds[-1][2] == "mob.sheep.shear"
    level.entities[:] = []
    _hold(level, "p1", "arris:iron_knife")
    args = _use("arris:brown_mushroom_colony", (0, 1, 0))
    assert level.statesAt((0, 1, 0))["arris:growth"] == 2        # 刀割完年龄清零（外观回到年龄 0）
    assert [(e[0]["itemName"], e[0]["count"]) for e in level.entities] == [("minecraft:brown_mushroom", 2)]
    level.entities[:] = []
    args = _use("arris:brown_mushroom_colony", (0, 1, 0))        # 年龄 0 了：再割什么都没有
    assert level.entities == [] and "cancel" not in args
    _hold(level, "p1", "minecraft:iron_axe")
    level.put((0, 1, 0), "arris:brown_mushroom_colony", **{"arris:growth": 7})
    args = _use("arris:brown_mushroom_colony", (0, 1, 0))
    assert level.entities == [] and "cancel" not in args and level.statesAt((0, 1, 0))["arris:growth"] == 7


def testSproutColonyTurnsIntoAgeZeroLook():
    level = _fresh().put((0, 0, 0), "arris:rich_soil").put((0, 1, 0), "arris:brown_mushroom_colony", **{"arris:growth": 0})
    _patchRandom(_rng(0.9), MushroomColony)
    _tick("arris:brown_mushroom_colony", (0, 1, 0))
    assert level.statesAt((0, 1, 0))["arris:growth"] == 2


# ---------------- 刀收稻草 ----------------

def _destroy(name, pos=(0, 1, 0), aux=0, player="p1", drops=()):
    args = {"fullName": name, "blockName": name, "x": pos[0], "y": pos[1], "z": pos[2], "dimensionId": 0, "playerId": player,
            "auxData": aux, "dropEntityIds": list(drops)}
    Registry.dispatch("DestroyBlockEvent", args, name)


def _hold(level, player, itemName):
    level.hands[player] = {"newItemName": itemName, "newAuxValue": 0, "count": 1}


def _strawChances():
    seen = []
    Straw.probability = lambda percent: (seen.append(percent), percent > 0)[1]
    return seen


def testStrawOnlyWithAKnife():
    level = _fresh()
    seen = _strawChances()
    _hold(level, "p1", "arris:iron_knife")
    _destroy("minecraft:short_grass")
    _destroy("minecraft:tall_grass")
    _destroy("arris:sandy_shrub")
    _destroy("minecraft:wheat", aux=7)
    _destroy("arris:rich_soil_wheat7")
    _destroy("arris:rice_upper_crop_stage3")
    assert seen == [20, 20, 30, 100, 100, 100]
    assert [item[0]["itemName"] for item in level.entities].count("arris:straw") == 6
    assert LEVEL.entities[0][1] == 0
    # 没拿刀 / 拿的是别的东西 / 创造模式 / 麦子没熟 / 蕨：没有
    del seen[:]
    level.entities[:] = []
    _hold(level, "p1", "minecraft:iron_axe")
    _destroy("minecraft:short_grass")
    level.hands.pop("p1")
    _destroy("minecraft:short_grass")
    _hold(level, "p1", "arris:iron_knife")
    level.creative.add("p1")
    _destroy("minecraft:short_grass")
    level.creative.discard("p1")
    _destroy("minecraft:wheat", aux=6)
    _destroy("minecraft:fern")
    assert level.entities == [] and 20 not in seen


def testKnifeHarvestOfRipePanicleGivesRice():
    level = _fresh()
    _strawChances()
    _hold(level, "p1", "arris:iron_knife")
    _destroy("arris:rice_upper_crop_stage3", drops=["e1", "e2"])
    assert level.destroyed == ["e1", "e2"]                      # 战利品表掉的稻穗拦下
    names = sorted(item[0]["itemName"] for item in level.entities)
    assert names == ["arris:rice", "arris:straw"]
    level.destroyed[:] = []
    level.entities[:] = []
    _hold(level, "p1", "minecraft:iron_axe")
    _destroy("arris:rice_upper_crop_stage3", drops=["e3"])
    assert level.destroyed == [] and level.entities == []        # 不用刀：稻穗照战利品表掉，没有稻米也没有稻草


# ---------------- 采摘番茄 ----------------

def testTomatoHarvestAddsFivePercentRottenTomato():
    level = _fresh().put((0, 1, 0), "arris:tomatoes_vine_stage3")
    chances = []
    Crops.probability = lambda percent: (chances.append(percent), percent == 5)[1]
    Crops.random = ScriptRng(ints=[2])
    args = {"x": 0, "y": 1, "z": 0, "blockName": "arris:tomatoes_vine_stage3", "dimensionId": 0, "playerId": "p1"}
    Registry.dispatch("ServerBlockUseEvent", args, "arris:tomatoes_vine_stage3")
    assert chances == [5] and args["cancel"] is True
    names = [(item[0]["itemName"], item[0]["count"]) for item in level.entities]
    assert names == [("arris:tomato", 2), ("arris:rotten_tomato", 1)]
    assert level.nameAt((0, 1, 0)) == "arris:tomatoes_vine_stage0"


def testBoneMealOnARipeTomatoStillPicksIt():
    # JE TomatoBlock.use：熟了右键就是摘，拿着骨粉也一样（方块的 use 先于骨粉）；潜行拿着东西时 JE 不调方块的 use，才轮到骨粉
    ripe = "arris:budding_tomatoes_stage6"
    applied = []
    realApply = Crops.ApplyBoneMeal
    Crops.ApplyBoneMeal = lambda playerId, item, name, pos, dim: applied.append(name) or True
    Crops.probability = lambda percent: False
    try:
        for sneaking in (False, True):
            level = _fresh().put((0, 1, 0), ripe)
            if sneaking:
                level.sneaking.add("p1")
            _hold(level, "p1", "minecraft:bone_meal")
            useOn = {"itemDict": dict(level.hands["p1"]), "blockName": ripe, "x": 0, "y": 1, "z": 0, "face": 1,
                     "dimensionId": 0, "entityId": "p1", "ret": False}
            Registry.dispatch("ServerItemUseOnEvent", useOn, ripe)
            args = _use(ripe, (0, 1, 0))
            assert useOn["ret"] is True                             # 引擎自己的骨粉一律不要
            if sneaking:
                assert applied == [ripe] and level.nameAt((0, 1, 0)) == ripe and "cancel" not in args
            else:
                assert applied == [] and level.nameAt((0, 1, 0)) == "arris:budding_tomatoes_stage3" and args["cancel"] is True
                assert [item[0]["itemName"] for item in level.entities] == ["arris:tomato"]
            applied[:] = []
    finally:
        Crops.ApplyBoneMeal = realApply


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
