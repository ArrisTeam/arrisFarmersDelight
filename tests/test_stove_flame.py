# -*- coding: utf-8 -*-
# runner: both
"""点着的炉灶自己的火（Shared/Rules/StoveFlame.py + Client/StoveFlame.py + rp/particles 的两个粒子）对 FD 的两段客户端代码：

StoveBlock.animateTick（java:38-55）：点着时每次 1/10 的概率在脚下放 block.stove.crackle（= 原版营火噼啪声，音量音调 1），每次都在正面（FACING 那一侧 0.52 处）
  随机高度 0 ~ 6/16、另一个水平方向 ±0.3 放一颗 SMOKE 一颗 FLAME；
StoveBlockEntity.particleTick / addSmokeParticles（java:19-46）：灶上不空时每件东西每刻 20% 的概率在它头上（y + 1）放 3 颗 SMOKE；HoD 的 StoveSmokeMixin 在炉灶站点显示时
  取消这一个方法。
下面把 Java 的公式照抄成代码（javaFlameSpot / javaSmoke），四个朝向逐一对；引擎是 panclient.py 里的假的。"""
from __future__ import print_function

import io
import json
import os

import fdtest
import panclient as C

world = C.install()
Flame = fdtest.load("Shared.Rules.StoveFlame")
Placement = fdtest.load("Shared.Rules.Placement")
BD = fdtest.load("Shared.Rules.BlockDisplay")
StoveFacing = fdtest.load("Shared.Rules.StoveFacing")
StoveFlame = C.load("Client.StoveFlame")
BlockItems = C.load("Client.BlockItems")
LISTENERS = dict((event, list(handlers)) for event, handlers in world.listeners.items())        # 导入时登记的；world.reset() 会清掉 world.listeners
RP = os.path.join(fdtest.ROOT, "rp")
POS = C.POS                                         # (10, 64, 10)
AUX_NAME = {0: "SOUTH", 1: "WEST", 2: "NORTH", 3: "EAST"}       # direction 状态 -> JE 的 FACING（写在 north 的贴图，也就是火口，出现在世界的那一面）
JAVA_STEP = {"SOUTH": (0, 1), "WEST": (-1, 0), "NORTH": (0, -1), "EAST": (1, 0)}                   # Direction.getStepX / getStepZ
JAVA_OFFSETS = ((0.3, 0.2), (0.0, 0.2), (-0.3, 0.2), (0.3, -0.2), (0.0, -0.2), (-0.3, -0.2))      # StoveBlockEntity.getStoveItemOffset
JAVA_DATA2D = {"SOUTH": 0, "WEST": 1, "NORTH": 2, "EAST": 3}                                       # Direction.get2DDataValue
JAVA_CLOCKWISE = {"NORTH": "EAST", "EAST": "SOUTH", "SOUTH": "WEST", "WEST": "NORTH"}              # Direction.getClockWise
STOVE = "arris:stove"
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}


def javaFlameSpot(blockPos, facing, horizontalRoll, heightRoll):
    """StoveBlock.animateTick 里 addParticle 的位置（java:40-54）。"""
    x, y, z = blockPos[0] + 0.5, float(blockPos[1]), blockPos[2] + 0.5
    stepX, stepZ = JAVA_STEP[facing]
    horizontalOffset = horizontalRoll * 0.6 - 0.3
    xOffset = stepX * 0.52 if stepX != 0 else horizontalOffset              # direction$axis == Axis.X
    yOffset = heightRoll * 6.0 / 16.0
    zOffset = stepZ * 0.52 if stepZ != 0 else horizontalOffset              # direction$axis == Axis.Z
    return (x + xOffset, y + yOffset, z + zOffset)


def javaSmoke(blockPos, facing, index):
    """StoveBlockEntity.addSmokeParticles 里 addParticle 的位置（java:31-40）：FACING 的 get2DDataValue 是奇数就把 offset 的 x、y 对调。"""
    ox, oy = JAVA_OFFSETS[index]
    if JAVA_DATA2D[facing] % 2 != 0:
        ox, oy = oy, ox
    (sx, sz), (cx, cz) = JAVA_STEP[facing], JAVA_STEP[JAVA_CLOCKWISE[facing]]
    return (blockPos[0] + 0.5 - sx * ox + cx * ox, blockPos[1] + 1.0, blockPos[2] + 0.5 - sz * oy + cz * oy)


def near(a, b):
    return all(abs(a[axis] - b[axis]) < 1.0e-9 for axis in range(3))


class _Dice(object):
    """顶替模块里的 random：按给定的次序一个一个吐（吐完再要就是用例写少了）。"""

    def __init__(self, *values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)


def _reset(aux=2, dice=()):
    world.reset()
    world.blocks[POS] = (STOVE, aux)
    BlockItems._hidden.clear()
    BlockItems._last.clear()
    StoveFlame._state["muted"] = False
    StoveFlame.random = _Dice(*dice)


def _animate(blockName=STOVE, blockPos=POS, aux=2):
    world.particles[:] = []
    del world.sounds[:]
    for handler in LISTENERS["BlockAnimateRandomTickEvent"]:
        handler({"blockPos": blockPos, "blockName": blockName, "auxData": aux})
    return [(p["id"], p["pos"]) for p in world.particles]


def _clientTick(blockName=STOVE, blockPos=POS):
    del world.particles[:]
    for handler in LISTENERS["ModBlockEntityTickClientEvent"]:
        handler({"posX": blockPos[0], "posY": blockPos[1], "posZ": blockPos[2], "blockName": blockName, "dimensionId": 0})
    return [(p["id"], p["pos"]) for p in world.particles]


def _lay(slots):
    """灶上这几格有东西（BlockItems 记着的最后一份内容，服务端广播或方块实体加载时写的）。"""
    BlockItems.show(0, POS, BD.KIND_STOVE, dict((str(slot), dict(BEEF)) for slot in slots))


# ---------------------------------------------------------------- 概率和位置（纯规则）

def testTheFrontOfTheStoveIsTheSideItsNorthTextureIsOn():
    assert dict((aux, Flame.frontOf(aux)) for aux in range(4)) == {0: (0, 1), 1: (-1, 0), 2: (0, -1), 3: (1, 0)}
    for aux, name in AUX_NAME.items():
        assert Flame.frontOf(aux) == JAVA_STEP[name], name
    assert [Flame.frontOf(aux) for aux in (4, 8, 12)] == [Flame.frontOf(1), Flame.frontOf(2), Flame.frontOf(3)], "假日创造者实验玩法下 1 / 2 / 3 的 aux 是 4 / 8 / 12"
    assert Flame.frontOf(None) == Flame.frontOf(6) == Flame.frontOf(0), "读不到、越界的按 0 朝南（Placement.directionOfAux 唯一一处读 aux）"
    for aux in (0, 1, 2, 3, 4, 8, 12, None, 6):
        assert Flame.frontOf(aux) == Placement.FACING_VECTORS[Placement.directionOfAux(aux)][::2], aux


def testTheFlameIsPutWhereJavaPutsItOnEveryFacing():
    for blockPos in ((3, 64, -2), (-5, 0, 7)):
        for aux, name in sorted(AUX_NAME.items()):
            for side in (0.0, 0.25, 0.5, 0.999999):
                for height in (0.0, 0.5, 0.999999):
                    assert near(Flame.flameSpot(blockPos, aux, side, height), javaFlameSpot(blockPos, name, side, height)), (blockPos, name, side, height)


def testTheFlameSitsOnTheFrontFaceWithinTheLowerSixSixteenthsAndPlusMinusThreeTenthsSideways():
    for aux in range(4):
        front = Flame.frontOf(aux)
        for side in (0.0, 0.5, 0.999999):
            x, y, z = Flame.flameSpot((0, 10, 0), aux, side, 0.5)
            assert abs((x - 0.5) * front[0] + (z - 0.5) * front[1] - 0.52) < 1.0e-9, "正面那一轴固定在 0.52"
            across = abs(z - 0.5) if front[0] else abs(x - 0.5)
            assert across <= 0.3, "另一个水平方向在 ±0.3 里"
        assert Flame.flameSpot((0, 10, 0), aux, 0.5, 0.0)[1] == 10.0 and abs(Flame.flameSpot((0, 10, 0), aux, 0.5, 0.999999)[1] - 10.375) < 1.0e-5


def testTheCrackleIsPlayedAtTheFootOfTheBlockCentre():
    assert Flame.crackleSpot((3, 64, -2)) == (3.5, 64.0, -1.5)


def testSmokeOverEachPieceIsWhereJavaPutsItOnEveryFacing():
    for blockPos in ((3, 64, -2), (10, 5, 20)):
        for aux, name in sorted(AUX_NAME.items()):
            for index in range(6):
                assert near(Flame.itemSmokeSpot(blockPos, aux, index), javaSmoke(blockPos, name, index)), (blockPos, name, index)


def testOnlyRealItemsMakeSmoke():
    items = {"0": dict(BEEF), "1": {}, "2": None, "3": {"newItemName": "minecraft:beef", "count": 0}, "4": dict(BEEF, count=64), "5": 0}
    assert Flame.occupiedSlots(items) == [0, 4]
    assert Flame.occupiedSlots({}) == []


def testTheJavaConstants():
    assert (Flame.CRACKLE_CHANCE, Flame.ITEM_SMOKE_CHANCE, Flame.ITEM_SMOKE_PUFFS, Flame.ITEM_SMOKE_HEIGHT) == (0.1, 0.2, 3, 1.0)
    assert (Flame.FRONT_REACH, Flame.SIDE_SPREAD, Flame.FRONT_HEIGHT, Flame.PARTICLE_RANGE) == (0.52, 0.6, 6.0 / 16.0, 32.0)
    assert Flame.CRACKLE == "block.campfire.crackle" and Flame.BLOCK == STOVE


def testParticlesFartherThanThirtyTwoBlocksFromTheViewerAreNotMade():
    assert Flame.inRange((0.0, 0.0, 0.0), (32.0, 0.0, 0.0)) and not Flame.inRange((0.0, 0.0, 0.0), (32.01, 0.0, 0.0))
    assert Flame.inRange((0.0, 0.0, 0.0), (19.0, 19.0, 19.0)) is False and Flame.inRange((0.0, 0.0, 0.0), (18.0, 18.0, 18.0)) is True, "按距离算，不是按各轴"


# ---------------------------------------------------------------- 火口（BlockAnimateRandomTickEvent）

def testTheClientListensToTheTwoEvents():
    assert StoveFlame.OnStoveAnimateTick in LISTENERS["BlockAnimateRandomTickEvent"]
    assert StoveFlame.OnStoveClientTick in LISTENERS["ModBlockEntityTickClientEvent"]


def testEveryAnimateTickMakesOneSmokeAndOneFlameAtTheSameSpotOnTheFront():
    for aux, name in sorted(AUX_NAME.items()):
        _reset(dice=(0.5, 0.25, 0.75))                       # 噼啪的骰子没中，水平 0.25，高度 0.75
        made = _animate(aux=aux)
        spot = javaFlameSpot(POS, name, 0.25, 0.75)
        assert [identifier for identifier, _ in made] == [Flame.SMOKE, Flame.FLAME], name
        assert all(near(at, spot) for _, at in made), (name, made, spot)
        assert world.sounds == [], "没中 1/10：不响"
        assert StoveFlame.random.values == [], "三个随机数：噼啪、水平、高度"


def testTheCrackleIsOneInTenAndNeverMoreThanOneParticlePair():
    _reset(dice=(0.0999, 0.5, 0.5))
    made = _animate()
    assert len(made) == 2
    assert world.sounds == [{"name": "block.campfire.crackle", "pos": (10.5, 64.0, 10.5), "volume": 1.0, "pitch": 1.0}]
    _reset(dice=(0.1, 0.5, 0.5))
    _animate()
    assert world.sounds == [], "random.nextInt(10) == 0 的概率是 0.1：骰子 0.1 不算中"


def testOnlyTheLitStoveIsOursTheUnlitOneAndOtherBlocksGetNothing():
    for name in ("arris:stove_extinguish", "arris:gleaming_salad_block_stage0", "othermod:stove", "minecraft:campfire"):
        _reset(dice=(0.0, 0.5, 0.5))
        assert _animate(blockName=name) == [], name
        assert world.sounds == [] and StoveFlame.random.values == [0.0, 0.5, 0.5], "不认的方块连骰子都不掷"


# ---------------------------------------------------------------- 灶上东西的烟（ModBlockEntityTickClientEvent）

def testAPieceMakesThreeSmokesWithAFifthOfTheChancePerTickAtThePlaceJavaPutsThem():
    for aux, name in sorted(AUX_NAME.items()):
        _reset(aux=aux, dice=(0.0, 0.19999))                 # 两件：第一件的骰子中、第二件刚好中（nextFloat() >= 0.2F 才跳过）
        _lay([0, 4])
        made = _clientTick()
        assert [identifier for identifier, _ in made] == [Flame.SMOKE] * 6, name
        assert all(near(at, javaSmoke(POS, name, 0)) for _, at in made[:3]), name
        assert all(near(at, javaSmoke(POS, name, 4)) for _, at in made[3:]), name
        assert StoveFlame.random.values == []


def testAPieceWhoseDiceMissesMakesNoSmokeAndEmptySlotsRollNothing():
    _reset(dice=(0.2, 0.9))
    _lay([1, 2])
    assert _clientTick() == [] and StoveFlame.random.values == [], "刚好 0.2 也跳过；空格不掷骰子"
    _reset(dice=())
    assert _clientTick() == [], "灶上什么都没有（JE 的 isEmpty 就返回）：不掷骰子、不放"


def testNoSmokeFartherThanThirtyTwoBlocksFromTheViewer():
    _reset(dice=(0.0,))
    _lay([0])
    world.foot = (100.0, 64.0, 100.0)
    assert _clientTick() == []
    world.foot = (10.5, 64.0, 7.5)
    _reset(dice=(0.0,))
    _lay([0])
    assert len(_clientTick()) == 3


def testTheStationTakesTheSmokeOverLikeHandsOnDelightsStoveSmokeMixin():
    _reset(dice=(0.0,))
    _lay([0])
    assert StoveFlame.muted() is False
    StoveFlame.muteItemSmoke()
    assert StoveFlame.muted() is True
    assert _clientTick() == [] and StoveFlame.random.values == [0.0], "站点在场：灶上东西的烟取消"
    StoveFlame.random = _Dice(0.5, 0.5, 0.5)
    assert len(_animate()) == 2, "火口的火星照旧（animateTick HoD 不碰）"


def testNobodyElsesBlockEntityTicksMakeSmoke():
    for name in ("arris:stove_extinguish", "arris:skillet", "othermod:stove"):
        _reset(dice=(0.0,))
        _lay([0])
        assert _clientTick(blockName=name) == [], name


# ---------------------------------------------------------------- 方块 JSON 和粒子文件

def _read(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _effect(name):
    return _read(os.path.join(RP, "particles", name + ".json"))["particle_effect"]


def testTheFlameIsOneShortLivedStillSpriteOfTheVanillaParticleSheet():
    effect = _effect("arris_stove_flame")
    assert effect["description"]["identifier"] == Flame.FLAME
    assert effect["description"]["basic_render_parameters"] == {"material": "particles_alpha", "texture": "textures/particle/particles"}
    components = effect["components"]
    assert components["minecraft:emitter_rate_instant"]["num_particles"] == 1 and "minecraft:emitter_lifetime_once" in components, \
        "放一次出一颗、发射器自己结束（原版的 basic_flame_particle 是 emitter_rate_manual，要 EmitManually）"
    assert "minecraft:emitter_rate_manual" not in components and "minecraft:emitter_lifetime_expression" not in components
    assert components["minecraft:particle_initial_speed"] == 0 and "minecraft:particle_motion_dynamic" not in components, "JE 的火焰粒子不动"
    assert components["minecraft:particle_lifetime_expression"]["max_lifetime"] == "math.random(0.6, 2.0)", "JE：(int)(8 / (random * 0.8 + 0.2)) + 4 刻 = 0.6 ~ 2.2 秒"
    billboard = components["minecraft:particle_appearance_billboard"]
    assert billboard["uv"] == {"texture_width": 128, "texture_height": 128, "uv": [0, 24], "uv_size": [8, 8]}, "原版 particles.png 里火焰那一格"
    assert "minecraft:particle_appearance_lighting" not in components, "火焰满亮度（JE 的 FlameParticle.getLightColor）"


def testTheSmokeIsOneRisingPuffOfTheVanillaParticleSheet():
    effect = _effect("arris_stove_smoke")
    assert effect["description"]["identifier"] == Flame.SMOKE
    assert effect["description"]["basic_render_parameters"] == {"material": "particles_alpha", "texture": "textures/particle/particles"}
    components = effect["components"]
    assert components["minecraft:emitter_rate_instant"]["num_particles"] == 1 and "minecraft:emitter_lifetime_once" in components
    assert "minecraft:emitter_rate_manual" not in components and "minecraft:emitter_lifetime_expression" not in components
    assert components["minecraft:particle_motion_dynamic"]["linear_acceleration"][1] > 0, "烟往上飘"
    assert components["minecraft:particle_lifetime_expression"]["max_lifetime"] == "math.random(0.4, 1.4)"
    flipbook = components["minecraft:particle_appearance_billboard"]["uv"]["flipbook"]
    assert flipbook["base_UV"] == [56, 0] and flipbook["max_frame"] == 8 and flipbook["size_UV"] == [8, 8], "原版 particles.png 里烟的八帧"
    assert "minecraft:particle_appearance_lighting" in components, "烟受光照（JE 的 SmokeParticle 是普通亮度）"


def testTheLitStovesComponentsAreWhatTheClientModuleListensTo():
    stove = _read(os.path.join(fdtest.BP, "netease_blocks", "arris_stove.json"))["minecraft:block"]
    assert stove["description"]["identifier"] == Flame.BLOCK
    components = stove["components"]
    assert components["netease:block_animate_random_tick"]["send_event"] is True, "BlockAnimateRandomTickEvent"
    assert components["netease:block_entity"]["client_tick"] is True, "ModBlockEntityTickClientEvent"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
