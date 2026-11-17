# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的煎锅（Server/Skillet.py 的右键放食物 / 空手取回，没装场景交互前置 / 站点关了时走的）对 FD 的 SkilletBlock.use 和 SkilletBlockEntity.addItemToCook，用假引擎驱动。

JE：addItemToCook 把手里的食物 insertItem 进锅里那一格（ItemStackHandler）：空着、或是同一种（isSameItemSameTags）就放进去，叠到一叠的最大数量为止，剩下的留在手里；
放进去了（数量变了）才算成功，成功一次这一件的进度从头算（cookingTime = 0）；放不进去什么也不发生；含水的提示 underwater，没有营火配方的提示 invalid_item。
成功放进去响一声 LANTERN_PLACE 0.7 / 1.0（SkilletBlock.java:83），锅原本是空的又在热源上再响一声 add_food 0.8 / 1.0（SkilletBlockEntity.java:188-190）；
空手取回没有声音，创造模式取下来的东西不给玩家（SkilletBlock.java:71-77，东西直接没了）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Skillet = fdtest.load("Server.Skillet")

POS = (7, 64, 7)
CENTER = (POS[0] + 0.5, POS[1] + 0.5, POS[2] + 0.5)
UNDERWATER, INVALID = "被水泡着可没法烹饪啊……", "这东西可不能被烹饪……"


def _item(name, count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def _setUp(hand=None, creative=False, pan=None, heated=True, below="minecraft:campfire"):
    world.reset()
    data = skilletkit.EngineData(heatEnable=heated)
    if pan is not None:
        data["cookingDict"] = dict(pan)
    world.setBlock(POS[0], POS[1], POS[2], "arris:skillet", data=data)
    world.setBlock(POS[0], POS[1] - 1, POS[2], below)
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    return data


def _use():
    world.runTimers()
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False}
    Skillet.OnServerSkilletBlockUse(args)
    return args


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _hand():
    return world.players["p1"]["hand"]


def _published():
    """方块上东西变了的广播里这口锅的内容。"""
    return [call[2]["items"]["0"] for call in world.calls if call[1] == "OnBlockItems"]


# ---------------------------------------------------------------- 放进占着的锅：同种合并

def testMoreOfTheSameFoodMergesIntoAnOccupiedPan():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2))
    data["cookTimer"] = 2.5
    _use()
    assert data["cookingDict"]["count"] == 5 and data["cookingDict"]["newItemName"] == "minecraft:beef"
    assert _hand() is None and _tips() == []
    assert data["cookTimer"] == 7.0, "放进去一次，这一件的进度从头算（JE 的 cookingTime = 0）"
    assert _published() == [{"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 5}], "客户端按新的数量重画"


def testMergingStopsAtTheMaxStackAndTheRestStaysInTheHand():
    data = _setUp(hand=_item("minecraft:beef", 10), pan=_item("minecraft:beef", 60))
    _use()
    assert data["cookingDict"]["count"] == 64 and _hand()["count"] == 6
    world.maxStack["minecraft:chicken"] = 16
    data = _setUp(hand=_item("minecraft:chicken", 20))
    _use()
    assert data["cookingDict"]["count"] == 16 and _hand()["count"] == 4, "空锅也不超过物品的最大堆叠"


def testAFullPanTakesNothingMoreAndNothingHappens():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 64))
    data["cookTimer"] = 2.5
    _use()
    assert data["cookingDict"]["count"] == 64 and _hand()["count"] == 3 and data["cookTimer"] == 2.5
    assert _tips() == [] and world.soundArgs == [] and _published() == [], "放不进去：没有提示、没有声音、进度不动"


def testADifferentKindOrDifferentDataDoesNotMerge():
    data = _setUp(hand=_item("minecraft:chicken", 3), pan=_item("minecraft:beef", 2))
    _use()
    assert data["cookingDict"]["newItemName"] == "minecraft:beef" and data["cookingDict"]["count"] == 2 and _hand()["count"] == 3 and _tips() == []
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2, extraId="marked"))
    _use()
    assert data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "JE 的 isSameItemSameTags：数据不一样不叠"
    data = _setUp(hand=_item("minecraft:beef", 3, newAuxValue=5), pan=_item("minecraft:beef", 2))
    _use()
    assert data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "aux 不一样也不叠"


def testCreativeMergesWithoutUsingUpTheStack():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2), creative=True)
    _use()
    assert data["cookingDict"]["count"] == 5 and _hand()["count"] == 3


def testAnOccupiedPanInTheWaterStillSaysUnderwater():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2))
    world.water.add((0,) + POS)
    _use()
    assert _tips() == [UNDERWATER] and data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "JE 先看含水（addItemToCook），再看放不放得进去"


def testAnEmptyPanStillTakesTheWholeStack():
    data = _setUp(hand=_item("minecraft:beef", 5))
    _use()
    assert data["cookingDict"]["count"] == 5 and _hand() is None and data["cookTimer"] == 7.0


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
