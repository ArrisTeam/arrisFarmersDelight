# -*- coding: utf-8 -*-
# runner: both
"""放下的煎锅（经典玩法，没有站点）自己的嗞嗞声、蒸汽、火焰附加的星星（Shared/Rules/SkilletSteam.py + Client/SkilletSteam.py + 方块 / 实体 / 粒子 JSON），
对 FD 的两段客户端代码：

SkilletBlock.animateTick（java:157-169）：skillet.isCooking()（加热着而且锅里有东西）才放，每次 1/10 的概率在脚下放 block.skillet.sizzle（音量 0.4，音调 0.9 ~ 1.1）；
SkilletBlockEntity.animationTick（java:70-91）：加热着而且锅里有东西时，每刻 20% 放一颗蒸汽（x、z 方块中心 ±0.2，y + 0.1），带火焰附加的锅再每刻 level * 5% 放一颗 ENCHANTED_HIT。
原来实体定义里的嗞嗞动画只要在热源上就每 15 秒响一声（空锅也响、没有蒸汽、没有星星）。引擎是 panclient.py 里的假的。"""
from __future__ import print_function

import io
import json
import math
import os

import fdtest
import molangkit
import panclient as C

world = C.install()
Steam = fdtest.load("Shared.Rules.SkilletSteam")
SkilletRules = fdtest.load("Shared.Rules.SkilletRules")
SoundMix = fdtest.load("Shared.Rules.SoundMix")
BD = fdtest.load("Shared.Rules.BlockDisplay")
SkilletSteam = C.load("Client.SkilletSteam")
BlockItems = C.load("Client.BlockItems")
LISTENERS = dict((event, list(handlers)) for event, handlers in world.listeners.items())        # 导入时登记的；world.reset() 会清掉 world.listeners
RP = os.path.join(fdtest.ROOT, "rp")
POS = C.POS                                         # (10, 64, 10)
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}


def _json(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8-sig") as handle:
        return json.load(handle)


class _Dice(object):
    """顶替模块里的 random：按给定的次序一个一个吐（吐完再要就是用例写少了）。"""

    def __init__(self, *values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)


def _reset(heat=1.0, scene=0.0, food=True, level=0, dice=()):
    """一座放在 POS 的煎锅：热源 heat（服务端推的 mod_heat）、场景接管 scene、锅里有没有东西（BlockItems 记着的最后一份内容）、火焰附加 level 级（方块实体数据里记着的那件煎锅）。"""
    world.reset()
    world.blocks[POS] = (Steam.BLOCK, 0)
    world.foot = (10.5, 64.0, 7.5)
    BlockItems._hidden.clear()
    BlockItems._last.clear()
    SkilletSteam._levels.clear()
    world.molang[(POS, "variable.mod_heat")] = heat
    if scene:
        world.molang[(POS, "variable.mod_scene")] = scene
    BlockItems.show(0, POS, BD.KIND_SKILLET, {"0": dict(BEEF) if food else {}})
    if level:
        stored = {"newItemName": "arris:skillet_item", "count": 1, "enchantData": [[SkilletRules.FIRE_ASPECT, level]]}
        world.exData[POS] = {Steam.STORED_KEY: {"__type__": 10, "__value__": {
            "newItemName": {"__type__": 8, "__value__": stored["newItemName"]}, "count": {"__type__": 3, "__value__": 1},
            "enchantData": {"__type__": 9, "__value__": [{"__type__": 9, "__value__": [{"__type__": 3, "__value__": SkilletRules.FIRE_ASPECT},
                                                                                       {"__type__": 3, "__value__": level}]}]}}}}
    SkilletSteam.random = _Dice(*dice)


def _animate(blockName=Steam.BLOCK):
    del world.sounds[:]
    for handler in LISTENERS["BlockAnimateRandomTickEvent"]:
        handler({"blockPos": POS, "blockName": blockName, "auxData": 0})
    return list(world.sounds)


def _tick(blockName=Steam.BLOCK):
    del world.particles[:]
    for handler in LISTENERS["ModBlockEntityTickClientEvent"]:
        handler({"posX": POS[0], "posY": POS[1], "posZ": POS[2], "blockName": blockName, "dimensionId": 0})
    return [(particle["id"], particle["pos"]) for particle in world.particles]


def near(a, b):
    return all(abs(a[axis] - b[axis]) < 1.0e-9 for axis in range(3))


# ---------------------------------------------------------------- 什么时候放、放在哪（纯规则）

def testTheJavaConstants():
    assert (Steam.SIZZLE_CHANCE, Steam.SIZZLE_VOLUME, Steam.SIZZLE_PITCH) == (0.1, 0.4, (0.9, 0.2))
    assert (Steam.STEAM_CHANCE, Steam.SPARK_CHANCE_PER_LEVEL, Steam.SPREAD, Steam.HEIGHT) == (0.2, 0.05, 0.4, 0.1)
    assert Steam.BLOCK == SkilletRules.SKILLET_BLOCK == "arris:skillet" and Steam.SIZZLE == "ambient.skillet.sizzle"
    assert Steam.STORED_KEY == "skilletItem" and Steam.FOOD_SLOT == "0"


def testItIsCookingOnlyWhenHeatedAndHoldingFood():
    """SkilletBlockEntity.isCooking = isHeated && hasStoredStack：空锅在热源上、有东西没热源，都不算。"""
    assert Steam.cooking(True, {"0": dict(BEEF)}) is True
    assert not Steam.cooking(True, {"0": {}}) and not Steam.cooking(True, {}) and not Steam.cooking(True, {"0": None})
    assert not Steam.cooking(True, {"0": dict(BEEF, count=0)}) and not Steam.cooking(True, {"0": 0}), "没有东西 / 数量 0 / 占位的整数"
    assert not Steam.cooking(False, {"0": dict(BEEF)}) and not Steam.cooking(None, {"0": dict(BEEF)})


def testTheSpotIsWhereJavaPutsIt():
    """animationTick 里 addParticle 的位置：x = pos.x + 0.5 + (nextDouble * 0.4 - 0.2)，y = pos.y + 0.1，z 同 x。"""
    for blockPos in ((3, 64, -2), (-5, 0, 7)):
        for rollX in (0.0, 0.25, 0.5, 0.999999):
            for rollZ in (0.0, 0.75, 0.999999):
                want = (blockPos[0] + 0.5 + (rollX * 0.4 - 0.2), blockPos[1] + 0.1, blockPos[2] + 0.5 + (rollZ * 0.4 - 0.2))
                assert near(Steam.surfaceSpot(blockPos, rollX, rollZ), want), (blockPos, rollX, rollZ)
    assert Steam.sizzleSpot((3, 64, -2)) == (3.5, 64.0, -1.5), "嗞嗞声放在方块底面的中心"
    assert abs(Steam.sizzlePitch(0.0) - 0.9) < 1e-12 and abs(Steam.sizzlePitch(0.5) - 1.0) < 1e-12 and abs(Steam.sizzlePitch(0.999999) - 1.1) < 1e-5


def testTheSparkChanceIsFivePercentPerLevelPerTickAndZeroWithoutTheEnchantment():
    assert [round(Steam.sparkChance(level), 9) for level in (0, 1, 2, 3)] == [0.0, 0.05, 0.1, 0.15]
    assert Steam.sparkChance(-1) == 0.0


# ---------------------------------------------------------------- 嗞嗞声（BlockAnimateRandomTickEvent）

def testTheClientListensToTheTwoEvents():
    assert SkilletSteam.OnSkilletAnimateTick in LISTENERS["BlockAnimateRandomTickEvent"]
    assert SkilletSteam.OnSkilletClientTick in LISTENERS["ModBlockEntityTickClientEvent"]


def testItSizzlesOneInTenWhileCookingAtFortyPercentVolumeAndAboutTheJavaPitch():
    _reset(dice=(0.0999, 0.5))                                    # 1/10 的骰子中、音调骰子 0.5
    sounds = _animate()
    volume, pitch = SoundMix.engineArgs("ambient.skillet.sizzle", 0.4, 1.0)
    assert sounds == [{"name": "ambient.skillet.sizzle", "pos": (10.5, 64.0, 10.5), "volume": volume, "pitch": pitch}]
    assert abs(volume * 20.0 - 0.4) < 1e-9, "定义里的每个采样自带 20 倍音量：交给引擎的是 0.4 / 20，听到的是 JE 的 0.4"
    _reset(dice=(0.1, ))
    assert _animate() == [], "random.nextInt(10) == 0 的概率是 0.1：骰子 0.1 不算中"
    _reset(dice=(0.0, 0.0))
    assert abs(_animate()[0]["pitch"] - 0.9) < 1e-12, "音调 0.9 起"


def testAnEmptyPanOnTheHeatDoesNotSizzleAndNeitherDoesAColdOneWithFood():
    for heat, food in ((1.0, False), (0.0, True), (0.0, False)):
        _reset(heat=heat, food=food, dice=(0.0, 0.5))
        assert _animate() == [], (heat, food)
        assert SkilletSteam.random.values == [0.0, 0.5], "不是在煎：连骰子都不掷"
    _reset(heat=None, dice=(0.0, 0.5))
    world.molang.pop((POS, "variable.mod_heat"))
    assert _animate() == [], "方块实体模型上没有 mod_heat（还没建好）：当作没有热源"


def testTheSceneTakesOverTheSoundAndTheSteam():
    """装了前置包又开着煎锅站点时，煎锅场景（Compat/Diegesis/PanFx）画声音和烟，方块实体的 mod_scene 为 1：这里不再放第二份。"""
    _reset(scene=1.0, dice=(0.0, 0.5, 0.0, 0.0, 0.0, 0.0))
    assert _animate() == [] and _tick() == []
    assert SkilletSteam.random.values == [0.0, 0.5, 0.0, 0.0, 0.0, 0.0]


def testOnlyTheSkilletIsOursOtherBlocksGetNothing():
    for name in ("arris:stove", "arris:cooking_pot", "arris:gleaming_salad_block_stage0", "othermod:skillet"):
        _reset(dice=(0.0, 0.5))
        assert _animate(blockName=name) == [] and _tick(blockName=name) == [], name
        assert SkilletSteam.random.values == [0.0, 0.5], "不认的方块连骰子都不掷"


# ---------------------------------------------------------------- 蒸汽、星星（ModBlockEntityTickClientEvent）

def testTheSteamIsOneInFivePerTickAtTheJavaSpot():
    _reset(dice=(0.19999, 0.25, 0.75))                            # 概率骰子中（nextFloat() < 0.2F）、x、z
    made = _tick()
    assert [identifier for identifier, _ in made] == ["arris:skillet_steam"] and near(made[0][1], Steam.surfaceSpot(POS, 0.25, 0.75))
    assert SkilletSteam.random.values == []
    _reset(dice=(0.2, ))
    assert _tick() == [] and SkilletSteam.random.values == [], "0.2 不算中；没中就不掷位置"


def testNothingIsMadeWhileNotCooking():
    for heat, food in ((1.0, False), (0.0, True)):
        _reset(heat=heat, food=food, level=3, dice=(0.0, 0.0, 0.0))
        assert _tick() == [] and SkilletSteam.random.values == [0.0, 0.0, 0.0], (heat, food)


def testAFireAspectSkilletSometimesPutsOutAnEnchantedSparkleAtTheSameSpot():
    _reset(level=2, dice=(0.5, 0.099999, 0.4, 0.6))               # 蒸汽没中；星星：level 2 = 每刻 10%，中了；x、z
    made = _tick()
    assert [identifier for identifier, _ in made] == ["arris:skillet_spark"] and near(made[0][1], Steam.surfaceSpot(POS, 0.4, 0.6))
    _reset(level=2, dice=(0.5, 0.1))
    assert _tick() == [], "0.1 不算中"
    _reset(level=1, dice=(0.0, 0.1, 0.2, 0.3, 0.049999, 0.5, 0.5))                  # 蒸汽中；level 1 = 5%：0.1 不中（上面那颗蒸汽之后）
    made = _tick()
    assert [identifier for identifier, _ in made] == ["arris:skillet_steam"], "没有附魔的蒸汽照冒、1 级的星星这一刻没中"
    _reset(level=0, dice=(0.5, ))
    assert _tick() == [] and SkilletSteam.random.values == [], "没有火焰附加连星星的骰子都不掷"


def testTheSteamAndTheSparkleCanBothComeOnTheSameTick():
    _reset(level=3, dice=(0.0, 0.1, 0.2, 0.14999, 0.3, 0.4))
    made = _tick()
    assert [identifier for identifier, _ in made] == ["arris:skillet_steam", "arris:skillet_spark"]
    assert near(made[0][1], Steam.surfaceSpot(POS, 0.1, 0.2)) and near(made[1][1], Steam.surfaceSpot(POS, 0.3, 0.4))


def testTheFireAspectLevelComesFromTheStoredSkilletAndIsReadOnlyOnceInAWhile():
    _reset(level=2)
    assert SkilletSteam._fireAspect(0, POS) == 2
    world.exData[POS] = {}                                        # 之后数据变了也要等一阵才重读（每刻读方块实体数据太重）
    assert all(SkilletSteam._fireAspect(0, POS) == 2 for _ in range(SkilletSteam.REREAD_TICKS - 1))
    assert SkilletSteam._fireAspect(0, POS) == 0, "到点重读：没有存着的煎锅（旧存档、命令放的）是 0 级"
    for bad in (None, 5, "x", [1]):
        world.exData[POS] = {Steam.STORED_KEY: bad}
        SkilletSteam._levels.clear()
        assert SkilletSteam._fireAspect(0, POS) == 0, bad


def testParticlesFartherThanThirtyTwoBlocksFromTheViewerAreNotMade():
    _reset(dice=(0.0, 0.5, 0.5))
    world.foot = (10.5, 64.0, 10.5 + 40.0)
    assert _tick() == []
    _reset(dice=(0.0, 0.5, 0.5))
    world.foot = (10.5, 64.0, 10.5 + 30.0)
    assert len(_tick()) == 1


def testARemovedSkilletForgetsItsLevel():
    _reset(level=2)
    SkilletSteam._fireAspect(0, POS)
    assert (0, POS) in SkilletSteam._levels
    SkilletSteam.OnSkilletRemoved({"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert (0, POS) not in SkilletSteam._levels


# ---------------------------------------------------------------- JSON（实机要完整重启才生效，离线核对写法）

def testTheBlockAsksTheEngineForTheAnimateTickAndTheClientTick():
    components = _json(fdtest.BP, "netease_blocks", "arris_skillet.json")["minecraft:block"]["components"]
    assert components["netease:block_animate_random_tick"] == {"send_event": True, "trigger_rate": 1.0}, "JE 的 animateTick 每次轮到都放（只有声音是 1/10）"
    assert components["netease:block_entity"] == {"client_tick": True, "movable": False, "tick": True}, "每刻一次的蒸汽 / 星星要客户端 tick"


def testTheEntityNoLongerSizzlesOnItsOwnJustForSittingOnTheHeat():
    entity = _json(RP, "entity", "skillet.json")["minecraft:client_entity"]["description"]
    assert "sizzle_sound" not in entity["animations"] and "sound_effects" not in entity
    assert not any("sizzle_sound" in step for step in entity["scripts"]["animate"] if isinstance(step, dict))
    assert "variable.mod_heat = 0.0;" in entity["scripts"]["initialize"], "mod_heat 还由服务端推、客户端读（Client/SkilletSteam），初值要有"
    animations = _json(RP, "animations", "skillet.animation.json")["animations"]
    assert "animation.skillet.sizzle" not in animations and "animation.skillet.scene" in animations


def _evaluate(expression, low=True, **variables):
    return molangkit.value(expression, _random=(lambda a, b: a) if low else (lambda a, b: b), **variables)


def testTheSteamParticleIsFarmersDelightsSteamAtItsSpeedLifetimeSizeAndFade():
    """SteamParticle：缩放 2（半边长 0.2 ~ 0.4 格）、活 80 + nextInt(50) 刻、向上 0.015 或 0.005 格每刻 + nextFloat / 500、Factory 里 y + 0.3、alpha 0.6，
    最后 60 刻起每刻 -0.02（30 刻 = 1.5 秒减到 0 就消失）：能看见的寿命是 4 ~ 6.45 秒 - 1.5 秒。"""
    effect = _json(RP, "particles", "arris_skillet_steam.json")["particle_effect"]
    assert effect["description"]["identifier"] == Steam.STEAM
    parts = effect["components"]
    assert parts["minecraft:emitter_shape_point"]["offset"] == [0, 0.3, 0] and parts["minecraft:emitter_shape_point"]["direction"] == [0, 1, 0]
    speeds = (_evaluate(parts["minecraft:particle_initial_speed"], True), _evaluate(parts["minecraft:particle_initial_speed"], False))
    assert abs(speeds[0] - 0.1) < 1e-9 and abs(speeds[1] - 0.34) < 1e-9, "最慢 0.005 格每刻 = 0.1 格每秒，最快 0.015 + 0.002 = 0.34"
    life = parts["minecraft:particle_lifetime_expression"]["max_lifetime"]
    assert abs(_evaluate(life, True) - 2.5) < 1e-9 and abs(_evaluate(life, False) - 4.95) < 1e-9
    size = parts["minecraft:particle_appearance_billboard"]["size"]
    assert size[0] == size[1] and abs(_evaluate(size[0], particle_random_1=0.0) - 0.2) < 1e-9 and abs(_evaluate(size[0], particle_random_1=1.0) - 0.4) < 1e-9
    alpha = parts["minecraft:particle_appearance_tinting"]["color"][3]
    for age, want in ((0.0, 0.6), (1.0, 0.6), (3.45, 0.6), (4.2, 0.3), (4.95, 0.0)):                     # 寿命 4.95：最后 1.5 秒（3.45 起）从 0.6 线性减到 0
        assert abs(_evaluate(alpha, particle_age=age, particle_lifetime=4.95) - want) < 1e-9, age
    assert parts["minecraft:particle_motion_dynamic"]["linear_acceleration"] == [0, 0, 0], "gravity 3e-6 实际不动"


def testTheSparkParticleIsTheEnchantedHitOfJava():
    """CritParticle（MagicProvider）：每个方向 0.4 倍的传入速度（x、z ±0.5，y 0.2 ~ 0.7）、摩擦 0.7 每刻、重力 0.5（0.02 格每二次方刻）、活 4 ~ 10 刻、
    半边长 0.075 ~ 0.15；颜色 r * 0.3、g * 0.8（基色 0.6 ~ 0.9）。"""
    effect = _json(RP, "particles", "arris_skillet_spark.json")["particle_effect"]
    assert effect["description"]["identifier"] == Steam.SPARK
    parts = effect["components"]
    assert parts["minecraft:emitter_rate_instant"]["num_particles"] == 1
    assert parts["minecraft:emitter_shape_point"]["direction"] == ["math.random(-0.5, 0.5)", "math.random(0.2, 0.7)", "math.random(-0.5, 0.5)"]
    motion = parts["minecraft:particle_motion_dynamic"]
    assert motion["linear_acceleration"] == [0, -8, 0], "0.5 * 0.04 格每刻 = 0.02 * 20 * 20"
    assert abs(motion["linear_drag_coefficient"] - (-20.0 * math.log(0.7))) < 0.01, "摩擦 0.7 每刻 = 每秒 e^-7.13"
    life = parts["minecraft:particle_lifetime_expression"]["max_lifetime"]
    assert abs(_evaluate(life, True) - 0.2) < 1e-9 and abs(_evaluate(life, False) - 0.5) < 1e-9
    size = parts["minecraft:particle_appearance_billboard"]["size"]
    assert abs(_evaluate(size[0], particle_random_1=0.0) - 0.075) < 1e-9 and abs(_evaluate(size[0], particle_random_1=1.0) - 0.15) < 1e-9


def testTheTwoParticleFilesAreInTheRightPlaceAndTheSteamTextureExists():
    steam = _json(RP, "particles", "arris_skillet_steam.json")["particle_effect"]["description"]["basic_render_parameters"]
    assert steam["texture"] == "textures/particle/steam_0" and os.path.isfile(os.path.join(RP, "textures", "particle", "steam_0.png"))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
