# -*- coding: utf-8 -*-
# runner: both
"""漏斗传热的刷新（Server/HeatConduct.py）：下面是漏斗的厨锅 / 煎锅，热源在两格以下，那一格变了没有邻居事件（BlockNeighborChangedServerEvent 只来自相邻的方块），
所以隔一会儿自己去看；变了就当成"正下方变了"交给原来的两个邻居事件处理函数（真的 CookingPot.OnCookingPotNeighborChanged、Skillet.OnSkilletNeighborChanged）。
下面不是漏斗的锅什么都不查。引擎是 fakeengine.py 里的假的，节拍用假的钟。"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest
import skilletkit

world = skilletkit.extend(fakeengine.install())
_qu = fdtest.SCRIPTS + ".QuModLibs"
_quPackage, _quServer = types.ModuleType(_qu), types.ModuleType(_qu + ".Server")
_quPackage.__path__ = []
_quServer.AllowCall = _quServer.InjectHttpPlayerId = lambda func: func                  # CookingPot 导入时要，离线不经 RPC
_quServer.Listen = lambda event: (lambda func: func)
_quServer.MultiClientsCall = lambda *args, **kwargs: None
sys.modules[_qu], sys.modules[_qu + ".Server"] = _quPackage, _quServer
Registry = fdtest.load("Server.EventRegistry")
Skillet = fdtest.load("Server.Skillet")
CookingPot = fdtest.load("Server.CookingPot")
HeatConduct = fdtest.load("Server.HeatConduct")
Ticks = fdtest.load("Shared.Rules.Ticks")

POT, SKILLET = "arris:cooking_pot", "arris:skillet"
BLOCK, BELOW, FURTHER = (10, 65, 10), (10, 64, 10), (10, 63, 10)
LIT, OUT = {"extinguished": False}, {"extinguished": True}


class _Clock(object):
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


clock = _Clock()


def _setUp(name, below="minecraft:hopper", further=("minecraft:campfire", LIT), heated=True):
    """name（锅或煎锅）放在 below 上，再下面一格是 further；方块实体数据里存的热不热是 heated。返回方块实体数据。"""
    world.reset()
    clock.now = 1000.0
    Registry.clearAll()
    for event, match, func in (("BlockNeighborChangedServerEvent", SKILLET, Skillet.OnSkilletNeighborChanged),
                               ("BlockNeighborChangedServerEvent", POT, CookingPot.OnCookingPotNeighborChanged),
                               ("ServerBlockEntityTickEvent", HeatConduct.HEATED_BLOCKS, HeatConduct.OnHeatedBlockTick),
                               ("BlockRemoveServerEvent", HeatConduct.HEATED_BLOCKS, HeatConduct.OnHeatedBlockRemove)):
        Registry.registerHandler(event, match=match)(func)
    HeatConduct.time = clock
    HeatConduct._pacer = Ticks.Pacer(HeatConduct.CHECK_SECONDS)
    data = skilletkit.EngineData(heatEnable=heated, cookTimer=3.0)
    world.setBlock(BLOCK[0], BLOCK[1], BLOCK[2], name, data=data)
    world.setBlock(BELOW[0], BELOW[1], BELOW[2], below)
    if further is not None:
        world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], further[0], states=dict(further[1]) if further[1] else None)
    _tick(name)                           # 第一次见到这个方块：只定相位，不查
    return data


def _tick(name, seconds=0.0):
    clock.now += seconds
    Registry.dispatch("ServerBlockEntityTickEvent", {"dimension": 0, "posX": BLOCK[0], "posY": BLOCK[1], "posZ": BLOCK[2], "blockName": name}, name)


def _sent():
    """发给全体客户端的方块实体 molang：{变量名: 值}（同一个变量发了几次取最后一次）。"""
    return dict((call[2]["name"], call[2]["molang"]) for call in world.calls if call[1] == "SetEntityBlockMolang")


def _due(name):
    _tick(name, HeatConduct.CHECK_SECONDS)


def testASkilletOnAHopperGoesColdWhenTheFireBelowTheHopperGoesOutAndHeatsAgainWhenRelit():
    data = _setUp(SKILLET)
    _due(SKILLET)
    assert data["heatEnable"] is True and data["cookTimer"] == 3.0 and _sent() == {}, "火还在：什么都不动，也不广播"
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "minecraft:campfire", states=OUT)
    _due(SKILLET)
    assert data["heatEnable"] is False and data["heatParticleEnable"] == 0.0, "漏斗下面的营火灭了：煎锅断热"
    assert data["cookTimer"] == Skillet._timerStart(data), "和正下方断热一样：煎锅的计时重置（Skillet.OnSkilletNeighborChanged 的反应，没有另抄）"
    assert _sent() == {"variable.mod_heat": 0.0, "variable.mod_shelf": 0.0}, _sent()
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "minecraft:campfire", states=LIT)
    _due(SKILLET)
    assert data["heatEnable"] is True and _sent()["variable.mod_heat"] == 1.0, "又点着了：热回来"


def testAPotOnAHopperNoticesTheFireBelowTheHopperToo():
    data = _setUp(POT, heated=False)
    _due(POT)
    assert data["heatEnable"] is True and data["shelfEnable"] == 0.0, "热源在漏斗下面：锅热了，漏斗上没有托盘"
    assert _sent() == {"variable.mod_heat": 1.0, "variable.mod_shelf": 0.0}, _sent()
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "minecraft:air")
    _due(POT)
    assert data["heatEnable"] is False and _sent()["variable.mod_heat"] == 0.0, "火被拆了：锅凉了"


def testAnythingBelowTheHopperThatHeatsIsNoticedAndAStoveGoingOutCoolsTheBlockAbove():
    data = _setUp(POT, further=("arris:stove", None))
    _due(POT)
    assert data["heatEnable"] is True, "存的是热：炉灶点着，没有变化"
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "arris:stove_extinguish")
    _due(POT)
    assert data["heatEnable"] is False, "炉灶灭了换成熄着的孪生方块：不热"
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "minecraft:cauldron", states={"cauldron_liquid": "lava", "fill_level": 6})
    _due(POT)
    assert data["heatEnable"] is True, "换成熔岩炼药锅：又热了"


def testTheCheckHappensTwiceASecondNotOnEveryEngineTick():
    _setUp(SKILLET)
    real, asked = HeatConduct.IsHeated, []
    HeatConduct.IsHeated = lambda *args: asked.append(args) or real(*args)
    try:
        for _ in range(200):                 # 10 秒，引擎每秒 20 刻
            _tick(SKILLET, 0.05)
    finally:
        HeatConduct.IsHeated = real
    assert 19 <= len(asked) <= 21, "每 0.5 秒一次，不是 200 次：%d" % len(asked)


def testBlocksNotOnAHopperAreNeverCheckedBecauseTheirOwnNeighbourEventCoversThem():
    for name in (POT, SKILLET):
        data = _setUp(name, below="minecraft:stone", further=("minecraft:campfire", LIT), heated=False)
        _due(name)
        assert data["heatEnable"] is False and _sent() == {}, name + "：石头不传热，也不是漏斗：这里不碰它存的状态（正下方变了有自己的事件）"
        data = _setUp(name, below="minecraft:campfire", further=None, heated=False)
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], "minecraft:campfire", states=LIT)
        _due(name)
        assert data["heatEnable"] is False and _sent() == {}, name + "：热源就在正下方，变了由邻居事件管，这里不重算"


def testAHopperThatWasNeverRefreshedStillGetsItsHeatFromTheCheck():
    """/setblock、旧存档里的锅：存的热是 None（从没算过）。"""
    data = _setUp(SKILLET, heated=None)
    data["heatEnable"] = None
    _due(SKILLET)
    assert data["heatEnable"] is True


def testTheEventHandedToTheNeighbourHandlersLooksLikeTheEnginesOneForTheBlockBelow():
    seen = []
    _setUp(POT, heated=False)
    Registry.clearAll()
    Registry.registerHandler("BlockNeighborChangedServerEvent", match=POT)(lambda args: seen.append(dict(args)))
    Registry.registerHandler("ServerBlockEntityTickEvent", match=HeatConduct.HEATED_BLOCKS)(HeatConduct.OnHeatedBlockTick)
    _due(POT)
    assert len(seen) == 1
    args = seen[0]
    assert (args["posX"], args["posY"], args["posZ"]) == BLOCK and (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"]) == BELOW
    assert args["dimensionId"] == 0 and args["toBlockName"] == "minecraft:hopper" and args["blockName"] == POT


def testABlockWithoutABlockEntityIsLeftAlone():
    _setUp(SKILLET)
    world.blocks[(0,) + BLOCK]["data"] = None
    world.setBlock(FURTHER[0], FURTHER[1], FURTHER[2], "minecraft:air")
    _due(SKILLET)
    assert _sent() == {}


def testARemovedBlockForgetsItsPace():
    _setUp(SKILLET)
    assert len(HeatConduct._pacer) == 1
    Registry.dispatch("BlockRemoveServerEvent", {"dimension": 0, "x": BLOCK[0], "y": BLOCK[1], "z": BLOCK[2], "fullName": SKILLET}, SKILLET)
    assert len(HeatConduct._pacer) == 0


def testOtherBlocksOnTheSameEventAreNotTouched():
    _setUp(SKILLET)
    seen = []
    Registry.registerHandler("BlockNeighborChangedServerEvent", match="minecraft:stone")(lambda args: seen.append(args))
    Registry.dispatch("ServerBlockEntityTickEvent", {"dimension": 0, "posX": 1, "posY": 2, "posZ": 3, "blockName": "arris:stove"}, "arris:stove")
    assert seen == [] and len(HeatConduct._pacer) == 1


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
