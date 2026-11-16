# -*- coding: utf-8 -*-
# runner: both
"""放下的煎锅（Server/Skillet.py）对 JE 的 SkilletBlockEntity：火焰附加缩短煎一件的时间、含水的煎锅不能煎、提示文字，用假引擎驱动。

JE：cookingTimeTotal = SkilletBlock.getSkilletCookingTime(配方时间 600, 火焰附加) -> 6 / 4 / 3 秒；
cookingTick：含水就把锅里的东西全掉出来；addItemToCook：没有营火配方提示 invalid_item，含水提示 underwater。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Registry = fdtest.load("Server.EventRegistry")
Skillet = fdtest.load("Server.Skillet")
Ticks = fdtest.load("Shared.Rules.Ticks")

POS = (7, 64, 7)
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}


class _EveryStep(object):
    """每次都放行的节拍器（测试不靠真实时间）。"""

    def due(self, key, now):
        return True

    def forget(self, key):
        pass


def _setUp(fireAspect=0, hand=None, creative=False):
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match="arris:skillet")(Skillet.OnServerSkilletBlockUse)
    Registry.registerHandler("ServerBlockEntityTickEvent", match="arris:skillet")(Skillet.OnSkilletTick)
    world.reset()
    Skillet._pacer = _EveryStep()
    data = skilletkit.EngineData(heatEnable=True)
    if fireAspect:
        data["skilletItem"] = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1, "enchantData": [[13, fireAspect]]}
    world.setBlock(POS[0], POS[1], POS[2], "arris:skillet", data=data)
    world.setBlock(POS[0], POS[1] - 1, POS[2], "minecraft:campfire")
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    return data


def _use(args=None):
    world.runTimers()
    args = args or {}
    args.update({"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False})
    Registry.dispatch("ServerBlockUseEvent", args, "arris:skillet")
    return args


def _tick():
    Registry.dispatch("ServerBlockEntityTickEvent", {"dimension": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]}, "arris:skillet")


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _ticksUntilFirstCooked(limit=200):
    for count in range(1, limit):
        _tick()
        if world.spawned:
            return count
    return None


def testStartingTimerFollowsTheFireAspectOfTheStoredSkillet():
    # 倒计时起点 = 煎一件的秒数 + 1：6 / 4 / 3 秒 -> 7 / 5 / 4
    for level, start in ((0, 7.0), (1, 5.0), (2, 4.0), (3, 4.0)):
        data = _setUp(fireAspect=level)
        assert Skillet._timerStart(data) == start, level
    assert Skillet.COOK_TIMER == 7


def testPlainSkilletCooksOneItemPerSixSeconds():
    data = _setUp(hand=BEEF)
    _use()
    assert data["cookingDict"]["count"] == 2 and data["cookTimer"] == 7.0
    assert _ticksUntilFirstCooked() == 24                  # 6 秒 / 0.25
    assert world.spawnedNames() == [("minecraft:cooked_beef", 1)] and data["cookingDict"]["count"] == 1 and data["cookTimer"] == 7.0


def testFireAspectShortensTheCookingTime():
    for level, ticks in ((1, 16), (2, 12), (5, 12)):       # 4 秒 / 3 秒 / 下限 3 秒
        data = _setUp(fireAspect=level, hand=BEEF)
        _use()
        assert data["cookTimer"] == ticks * 0.25 + 1.0, level
        assert _ticksUntilFirstCooked() == ticks, level


def testFoodInTheWaterIsRefusedWithTheUnderwaterTip():
    data = _setUp(hand=BEEF)
    world.water.add((0,) + POS)
    _use()
    assert _tips() == ["被水泡着可没法烹饪啊……"]
    assert data["cookingDict"] is None and world.players["p1"]["hand"]["count"] == 2


def testNonCookableItemGetsTheInvalidItemTipEvenInWaterOrWhenOccupied():
    stick = {"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1}
    for water, occupied in ((False, False), (True, False), (False, True)):
        data = _setUp(hand=stick)
        if water:
            world.water.add((0,) + POS)
        if occupied:
            data["cookingDict"] = dict(BEEF)
        del world.calls[:]
        _use()
        assert _tips() == ["这东西可不能被烹饪……"], (water, occupied)


def testOccupiedPanTakesNoMoreFoodAndSaysNothing():
    data = _setUp(hand={"newItemName": "minecraft:chicken", "newAuxValue": 0, "count": 1})
    data["cookingDict"] = dict(BEEF)
    _use()
    assert _tips() == [] and data["cookingDict"]["newItemName"] == "minecraft:beef"


def testFloodedSkilletFloatsItsFoodOut():
    data = _setUp()
    data["cookingDict"] = dict(BEEF)
    _tick()
    assert world.spawned == []
    world.water.add((0,) + POS)
    _tick()
    assert world.spawnedNames() == [("minecraft:beef", 2)] and data["cookingDict"] is None
    _tick()
    assert len(world.spawned) == 1                          # 之后锅是空的，不会再掉


def testNothingCooksInTheWaterEvenOnAHeatSource():
    data = _setUp(hand=BEEF)
    _use()
    for _ in range(10):
        _tick()                                              # 煎了一阵（还没到 6 秒）
    world.water.add((0,) + POS)
    for _ in range(60):
        _tick()
    assert world.spawnedNames() == [("minecraft:beef", 2)]   # 浮出来的是生肉，一件熟的都没有


def testBlockedItemsAreStillCancelled():
    for name in ("arris:cutting_board", "arris:skillet_item", "arris:cooking_pot"):
        _setUp(hand={"newItemName": name, "newAuxValue": 0, "count": 1})
        assert _use()["cancel"] is True, name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
