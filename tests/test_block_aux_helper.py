# -*- coding: utf-8 -*-
# runner: both
"""服务端读方块 aux 的真辅助函数（Server/Helpers/Engine.GetBlockAux / GetBlockName）和用它的朝向钩子（Compat/Diegesis/GrillOpen.facingOf）。
别的服务端测试用的假引擎（tests/potfake.py、fakeengine.py）把 Engine 整个换成了假的，GetBlockAux 是一个 lambda，真函数没有被任何离线测试执行过：
这里只把 QuModLibs.Server 换成假的（引擎的入口 serverApi），导入真的 Engine.py，让它对着一个假的 compFactory 跑——方块字典有 aux、没有 aux 这个键、aux 是 None、
方块不在（GetBlockNew 回 None），再接上真的朝向钩子，按 facingkit 的表（普通世界 0..3、假日创造者实验玩法 4 / 8 / 12、读不到的）给出站点朝向。
GetBlockNew 的问法按官方文档：(pos 三个整数的元组, 维度)。"""
from __future__ import print_function

import importlib
import os
import sys
import types

import facingkit as T
import fdtest

PACKAGE = fdtest.SCRIPTS
POS = (4, 70, -9)
STOVES = ("arris:stove", "arris:stove_extinguish")


class Blocks(object):
    """假的 compFactory.CreateBlockInfo(levelId)：GetBlockNew 回方块信息字典（没有的位置回 None），记下每一次的问法。"""

    def __init__(self):
        self.blocks, self.asked = {}, []

    def GetBlockNew(self, pos, dimensionId):
        assert isinstance(pos, tuple) and len(pos) == 3 and all(isinstance(value, int) for value in pos), "要三个整数的元组：%r" % (pos,)
        assert isinstance(dimensionId, int), "维度是整数：%r" % (dimensionId,)
        self.asked.append((pos, dimensionId))
        return self.blocks.get((dimensionId, pos))


class States(object):
    """假的 compFactory.CreateBlockState(levelId)：GetBlockStates 回状态字典（没有回 None）。"""

    def __init__(self):
        self.states = {}

    def GetBlockStates(self, pos, dimensionId):
        return self.states.get((dimensionId, tuple(pos)))


blocks, states = Blocks(), States()


class Factory(object):
    def CreateBlockInfo(self, owner):
        return blocks

    def CreateBlockState(self, owner):
        return states

    def __getattr__(self, name):
        raise AttributeError("假的 compFactory 没有 %s：真的 Engine / 钩子多用了别的引擎接口（要补就在这里补）" % name)


class ItemPosType(object):
    INVENTORY, CARRIED = 0, 1


class EntityType(object):
    Mob = 1


class Api(object):
    """假的 serverApi：Engine.py 导入时只取这两样。"""

    @staticmethod
    def GetEngineCompFactory():
        return Factory()

    @staticmethod
    def GetMinecraftEnum():
        return types.SimpleNamespace(ItemPosType=ItemPosType, EntityType=EntityType) if hasattr(types, "SimpleNamespace") \
            else type("Enum", (), {"ItemPosType": ItemPosType, "EntityType": EntityType})()


def _loadRealEngine():
    qu = PACKAGE + ".QuModLibs"
    package = types.ModuleType(qu)
    package.__path__ = []
    server = types.ModuleType(qu + ".Server")
    server.serverApi, server.levelId, server.System = Api, "level", object()
    server.Call, server.DestroyEntity = (lambda *args: None), (lambda entityId: None)
    sys.modules[qu], sys.modules[qu + ".Server"] = package, server
    importlib.import_module(PACKAGE + ".Server.Helpers")
    return importlib.import_module(PACKAGE + ".Server.Helpers.Engine")


Engine = _loadRealEngine()
GrillOpen = importlib.import_module(PACKAGE + ".Compat.Diegesis.GrillOpen")
StoveSwap = importlib.import_module(PACKAGE + ".Server.StoveSwap")


def _reset():
    del blocks.asked[:]
    blocks.blocks.clear()
    states.states.clear()


def testThisIsTheRealHelperNotTheOneTheOtherFakesPutInItsPlace():
    assert os.path.basename(Engine.__file__).startswith("Engine.py") and "Server" in Engine.__file__.replace("\\", "/")
    assert Engine.compFactory.CreateBlockInfo(Engine.levelId) is blocks and Engine.GetBlockAux.__module__ == Engine.__name__


def testTheRealHelperAsksGetBlockNewWithThePositionThenTheDimensionAndReturnsTheAux():
    _reset()
    blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": 2}
    blocks.blocks[(1, POS)] = {"name": "arris:stove", "aux": 3}
    assert Engine.GetBlockAux(POS, 0) == 2 and Engine.GetBlockAux(POS, 1) == 3
    assert blocks.asked == [(POS, 0), (POS, 1)], "先坐标后维度"
    assert Engine.GetBlockName(POS, 1) == "arris:stove"
    blocks.blocks[(0, POS)] = {"name": "arris:stove_extinguish", "aux": 12}
    assert Engine.GetBlockAux(POS, 0) == 12, "辅助函数只读、不解码（解码是 Placement.directionOfAux 的事）"


def testTheRealHelperReadsZeroWhenTheAuxIsMissingNoneOrTheBlockIsNotThere():
    _reset()
    blocks.blocks[(0, POS)] = {"name": "arris:stove"}
    assert Engine.GetBlockAux(POS, 0) == 0, "没有 aux 这个键"
    blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": None}
    assert Engine.GetBlockAux(POS, 0) == 0, "aux 是 None"
    blocks.blocks[(0, POS)] = {}
    assert Engine.GetBlockAux(POS, 0) == 0, "空字典"
    blocks.blocks[(0, POS)] = None
    assert Engine.GetBlockAux(POS, 0) == 0, "GetBlockNew 回 None"
    assert Engine.GetBlockAux((9, 9, 9), 0) == 0, "方块不在（区块没加载）"
    blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": 0}
    assert Engine.GetBlockAux(POS, 0) == 0


def testTheServerHookRunsTheRealHelperAndFacesEveryAuxTheWayTheTableSays():
    for name in STOVES:
        for aux, yaw in sorted(T.YAW.items()):
            _reset()
            blocks.blocks[(0, POS)] = {"name": name, "aux": aux}
            assert GrillOpen.facingOf(0, POS) == yaw, (name, aux)
            assert blocks.asked == [(POS, 0)], "钩子只问了一次引擎"
        for aux in T.UNKNOWN:
            _reset()
            blocks.blocks[(0, POS)] = {"name": name, "aux": aux}
            assert GrillOpen.facingOf(0, POS) == T.UNKNOWN_YAW, (name, aux)


def testTheServerHookNeverReturnsNoneWhateverTheEngineAnswers():
    """返回 None 站点就朝着玩家（PLAYER），和炉灶自己空间里写的六件对不上：读不到 aux、方块不在时也给朝南。"""
    for answer in ({"name": "arris:stove"}, {"name": "arris:stove", "aux": None}, {}, None):
        _reset()
        blocks.blocks[(0, POS)] = answer
        assert GrillOpen.facingOf(0, POS) == T.UNKNOWN_YAW == 180, answer
    _reset()
    assert GrillOpen.facingOf(0, (1, 2, 3)) == 180


def testTheSwapFallbackReadsTheDirectionStateFirstThenTheAuxWithTheSameDecode():
    """点火 / 灭火换方块要把朝向带过去：优先读 direction 状态；读不到状态再按 aux 读（0..3、4 / 8 / 12），别的按 0。"""
    for aux, direction in sorted(T.DIRECTION.items()):
        _reset()
        blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": aux}
        assert StoveSwap._directionOf(POS, 0) == direction, aux
        states.states[(0, POS)] = {"other": 1}
        assert StoveSwap._directionOf(POS, 0) == direction, "有状态字典但没有 direction：照样按 aux"
    _reset()
    blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": 0}
    states.states[(0, POS)] = {"direction": 3}
    assert StoveSwap._directionOf(POS, 0) == 3, "状态说了算"
    for aux in T.UNKNOWN:
        _reset()
        blocks.blocks[(0, POS)] = {"name": "arris:stove", "aux": aux}
        assert StoveSwap._directionOf(POS, 0) == T.UNKNOWN_DIRECTION, aux
    _reset()
    assert StoveSwap._directionOf(POS, 0) == 0, "方块读不到：朝南"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
