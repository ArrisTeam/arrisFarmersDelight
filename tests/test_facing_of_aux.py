# -*- coding: utf-8 -*-
# runner: both
"""方块的 aux 怎么读成朝向：Placement.directionOfAux 是唯一一处，炉灶 / 厨锅 / 煎锅 / 砧板的各个读朝向的地方都走它（见 facingkit.py 的期望表）。
普通世界 aux 就是 direction 状态 0..3；假日创造者实验玩法下 direction 1 / 2 / 3 的 aux 是 4 / 8 / 12（Shared/Rules/Placement.py 的 _HOLIDAY_AUX，
Server/Helpers/Placement 查玩法开没开的那条路径知道这件事）。原来 PotModelMath.facingOf 只取低两位（& 3）：4 / 8 / 12 全读成朝南，
这种世界里炉灶站点的镜头、六件的位置、世界里的展示在朝西 / 北 / 东的炉灶上全是错的，厨锅 / 煎锅 / 砧板的模型转得也不对。
这里是客户端一侧：站点朝向钩子（GrillView.facingOf 读 GetBlock 的 aux）、场景、世界里的展示；服务端一侧（真的 GetBlockAux）在 test_block_aux_helper.py。"""
from __future__ import print_function

import facingkit as T
import panclient as C

world = C.install()
Placement = C.load("Shared.Rules.Placement")
PotMath = C.load("Shared.Rules.PotModelMath")
PanMath = C.load("Shared.Rules.PanModelMath")
StoveFacing = C.load("Shared.Rules.StoveFacing")
GrillView = C.load("Compat.Diegesis.GrillView")
StoveScenes = C.load("Compat.Diegesis.StoveScenes")
BlockItems = C.load("Client.BlockItems")
PanScenes = C.load("Compat.Diegesis.PanScenes")
PotScenes = C.load("Compat.Diegesis.PotScenes")
POS = C.POS
STOVES = ("arris:stove", "arris:stove_extinguish")


def _block(name, aux):
    world.reset()
    world.blocks[POS] = (name, aux)


# ---------------------------------------------------------------- 纯规则

def testTheOneDecodeReadsPlainHolidayAndUnreadableAux():
    for aux, direction in sorted(T.DIRECTION.items()):
        assert Placement.directionOfAux(aux) == direction, aux
    for aux in T.UNKNOWN:
        assert Placement.directionOfAux(aux) == T.UNKNOWN_DIRECTION, aux
    assert Placement.directionOfAux(3.0) == 3 and Placement.directionOfAux(8.0) == 2, "引擎给的整数有时是浮点"
    assert Placement.directionOfAux(True) == 1 and Placement.directionOfAux(0) == 0, "0 两种写法一样"
    assert all(Placement.directionOfAux(aux) in (0, 1, 2, 3) for aux in range(-20, 200)), "永远是四个朝向之一，不返回 None"


def testTheTwoWritingsNeverCollide():
    """0..3 和 0 / 4 / 8 / 12 只在 0 上重叠，且 0 两边都是朝南：所以不用先查假日创造者实验玩法开没开。"""
    plain, holiday = Placement.holidayAuxMap(False), Placement.holidayAuxMap(True)
    overlap = set(plain) & set(holiday)
    assert overlap == set([0]) and plain[0] == holiday[0] == 0
    for aux, direction in list(plain.items()) + list(holiday.items()):
        assert Placement.directionOfAux(aux) == direction, aux


def testPotPanAndStoveShareTheDecode():
    for aux, name in sorted(T.FACING.items()):
        assert PotMath.facingOf(aux) == name and PanMath.facingOf(aux) == name, aux
        assert StoveFacing.yawOfAux(aux) == T.YAW[aux], aux
    for aux in T.UNKNOWN:
        assert PotMath.facingOf(aux) == PanMath.facingOf(aux) == T.UNKNOWN_FACING, aux
        assert StoveFacing.yawOfAux(aux) == T.UNKNOWN_YAW, aux
    assert StoveFacing.yawOfAux(3.0) == 90 and StoveFacing.yawOfAux(12.0) == 90


def testTheStoveYawAlwaysComesOutAsOneOfTheFourSidesTheKernelAccepts():
    protocol = C.dgtest.load("Shared.Protocol")
    for aux in sorted(T.YAW) + list(T.UNKNOWN):
        assert StoveFacing.yawOfAux(aux) in protocol.YAWS, aux


# ---------------------------------------------------------------- 客户端的站点朝向钩子

def testTheClientHookFacesTheFrontOfBothStoveBlocksForEveryAux():
    for name in STOVES:
        for aux, yaw in sorted(T.YAW.items()):
            _block(name, aux)
            assert GrillView.facingOf(POS, 0) == yaw, (name, aux)
        for aux in T.UNKNOWN:
            _block(name, aux)
            assert GrillView.facingOf(POS, 0) == T.UNKNOWN_YAW, (name, aux)


def testTheClientHookReadsSouthWhenTheBlockCannotBeRead():
    world.reset()
    assert GrillView.facingOf(POS, 0) == 180, "那里读不到方块（没加载）：和 aux 读不到一样朝南，不返回 None"
    world.blocks[POS] = ("arris:stove", None)
    assert GrillView.facingOf(POS, 0) == 180


# ---------------------------------------------------------------- 场景和世界里的展示

def testTheStoveSceneAndTheWorldDisplayTurnWithTheSameTable():
    for name in STOVES:
        for aux, yaw in sorted(T.YAW.items()):
            _block(name, aux)
            StoveScenes._scenes.clear()
            StoveScenes.enable()
            assert StoveScenes.ensure(0, POS).yaw == yaw, (name, aux)
            assert BlockItems._stoveYaw(POS) == yaw, (name, aux)
        for aux in T.UNKNOWN:
            _block(name, aux)
            StoveScenes._scenes.clear()
            assert StoveScenes.ensure(0, POS).yaw == T.UNKNOWN_YAW and BlockItems._stoveYaw(POS) == T.UNKNOWN_YAW, (name, aux)


def testAReloadedStoveBlockEntityIsTurnedByTheSameTable():
    """区块里的方块实体重建时读到的朝向变了（StoveScenes.OnBlockEntityLoaded 里 scene.turn）：假日创造者实验玩法的 8 也是朝北。"""
    _block("arris:stove", 0)
    StoveScenes._scenes.clear()
    StoveScenes.enable()
    scene = StoveScenes.ensure(0, POS)
    assert scene.yaw == 180
    world.blocks[POS] = ("arris:stove", 8)
    StoveScenes.OnBlockEntityLoaded({"blockName": "arris:stove", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert scene.yaw == 0


def testTheCuttingBoardsDisplayOffsetTurnsWithTheSameTable():
    """砧板底座在方块里偏一点，偏的方向随朝向转（BlockItems._boardOffset）：4 / 8 / 12 要和 1 / 2 / 3 一样转，朝向不同偏的方向不同。"""
    offsets = {}
    for aux in (0, 1, 2, 3, 4, 8, 12):
        _block("arris:cutting_board", aux)
        offsets[aux] = BlockItems._boardOffset(POS)
    assert offsets[4] == offsets[1] and offsets[8] == offsets[2] and offsets[12] == offsets[3]
    assert len(set(offsets[aux] for aux in (0, 1, 2, 3))) == 4, "四个朝向偏的方向各不相同"
    _block("arris:cutting_board", 5)
    assert BlockItems._boardOffset(POS) == offsets[0], "别的值按 0 朝南"


def testTheSkilletAndPotScenesAreBuiltFacingTheSameWay():
    for aux, name in sorted(T.FACING.items()):
        _block("arris:skillet", aux)
        PanScenes._scenes.clear()
        assert PanScenes.ensure(0, POS).facing == name, aux
        _block("arris:cooking_pot", aux)
        PotScenes._scenes.clear()
        assert PotScenes.ensure(0, POS).facing == name, aux
    for aux in T.UNKNOWN:
        _block("arris:skillet", aux)
        PanScenes._scenes.clear()
        assert PanScenes.ensure(0, POS).facing == T.UNKNOWN_FACING, aux


if __name__ == "__main__":
    raise SystemExit(C.dgtest.run(globals()))
