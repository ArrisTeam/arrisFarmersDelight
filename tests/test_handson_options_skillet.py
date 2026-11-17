# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里的煎锅（skillet / skillet_time）落在放下的煎锅自己的一步上（Server/Skillet.py 的真处理函数 + Server/HandFrying.py，假引擎照 test_skillet_block）：
农夫乐事自己的右键放进去的照旧 6 秒一件，不乘 skillet_time（SkilletBook 以外的"站点里手放的才乘"）；
站点关了，存档里留下的手放的一锅交给农夫乐事原样煎：6 秒一件、煎好弹出来（SkilletTests.aStationTurnedOffHandsThePanToFarmersDelight：
cooked in its own time and out of the pan, never tossed）；站点开着的同一锅一直等着颠。"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit
from optkit import Config

world = fakeengine.install()
skilletkit.extend(world)
Registry = fdtest.load("Server.EventRegistry")
Skillet = fdtest.load("Server.Skillet")
HandFrying = fdtest.load("Server.HandFrying")

POS = (7, 64, 7)
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}


class _EveryStep(object):
    """每次都放行的节拍器（测试不靠真实时间）。"""

    def due(self, key, now):
        return True

    def forget(self, key):
        pass


def _setUp():
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match="arris:skillet")(Skillet.OnServerSkilletBlockUse)
    Registry.registerHandler("ServerBlockEntityTickEvent", match="arris:skillet")(Skillet.OnSkilletTick)
    world.reset()
    HandFrying._hands.clear()
    Skillet._pacer = _EveryStep()
    data = skilletkit.EngineData(heatEnable=True)
    world.setBlock(POS[0], POS[1], POS[2], "arris:skillet", data=data)
    world.setBlock(POS[0], POS[1] - 1, POS[2], "minecraft:campfire")
    world.addPlayer("p1", hand=dict(BEEF))
    return data


def _tick():
    Registry.dispatch("ServerBlockEntityTickEvent", {"dimension": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]}, "arris:skillet")


def _ticksUntilCooked(limit=400):
    for count in range(1, limit):
        _tick()
        if world.spawned:
            return count
    return None


def _handFried(data):
    """锅里是生牛肉、站点里手放的（两面分开煎、等人颠）。"""
    data["cookingDict"] = dict(BEEF)
    data["cookTimer"] = Skillet._timerStart(data)
    hand = HandFrying.handOf(0, POS, data)
    hand.frying.layByHand()
    HandFrying.save(hand, data)
    return hand


def testFarmersDelightsOwnRightClickKeepsItsSixSecondsWhateverTheConfigSays():
    for times in (3.0, 0.5):
        data = _setUp()
        with Config(skillet_time=times):
            args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False}
            Registry.dispatch("ServerBlockUseEvent", args, "arris:skillet")
            assert data["cookingDict"]["count"] == 1 and data["cookTimer"] == 7.0
            assert _ticksUntilCooked() == 24, times              # 6 秒 / 0.25，和 test_skillet_block 一样


def testAStationTurnedOffHandsAHandFriedPanToFarmersDelightWhichCooksItInItsOwnTime():
    data = _setUp()
    hand = _handFried(data)
    with Config(skillet=False, skillet_time=5.0):
        assert _ticksUntilCooked() == 24, "FD 原样 6 秒一件（站点关了倍率算 1）"
    assert world.spawnedNames() == [("minecraft:cooked_beef", 1)], "煎好了弹出来，没有等人颠"
    assert not hand.frying.byHand and data["cookingDict"] is None and data["panFrying"] is None


def testWithTheStationOnTheSameHandFriedPanWaitsForTheTossAndNothingJumpsOut():
    data = _setUp()
    hand = _handFried(data)
    for _ in range(48):                                           # 12 秒
        _tick()
    assert world.spawned == [] and data["cookingDict"]["newItemName"] == "minecraft:beef", "没人颠，等着"
    assert hand.frying.byHand and hand.frying.waits()


def testAHandFriedPanDoneOnBothSidesStaysInThePanWhenTheStationIsOff():
    # 煎好的（熟的留在锅里等人取）：FD 的煎锅对熟的什么也不做，留着等右键取走
    data = _setUp()
    hand = _handFried(data)
    data["cookingDict"] = {"newItemName": "minecraft:cooked_beef", "newAuxValue": 0, "count": 1}
    with Config(skillet=False):
        for _ in range(60):
            _tick()
    assert world.spawned == [] and data["cookingDict"]["newItemName"] == "minecraft:cooked_beef"
    assert not hand.frying.byHand


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
