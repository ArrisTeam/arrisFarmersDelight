# -*- coding: utf-8 -*-
# runner: both
"""手持煎锅按住右键煎的时候点一下左键 = 翻面（客户端 Client/Input.OnLeftClickDown，对 FD 的 KeybindEvents.preClientTick）：

JE：玩家正用着煎锅（player.isUsingItem() 且用的是 SkilletItem）、煎锅的 FlipTimeStamp 还是 0 时，每点一下攻击键发一个 FlipSkilletMessage 给服务端。
这里只在"右键按住着（HoldReporter.down）而且手里（主手或副手）拿着煎锅"时报一个 SkilletFlip；是不是真在煎、在不在翻由服务端核对（Server/SkilletHand.onFlip）。"""
from __future__ import print_function

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Input = fdtest.load("Client.Input")
SKILLET = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1}


def _run(steps):
    """按顺序做几件事：("hold", 手里拿的物品或 None) 右键按下、("release",) 右键松开、("left",) 左键按下；返回客户端发出的调用。"""
    calls = []
    original = Input.Call
    Input.Call = lambda name, data=None: calls.append((name, data))
    Input._skilletHold.down = False
    try:
        for step in steps:
            if step[0] == "hold":
                C.engine.GetCarriedItem = lambda getUserData=False, item=step[1]: item
                Input.OnRightClickDown({})
            elif step[0] == "release":
                Input.OnRightClickUp({})
            else:
                Input.OnLeftClickDown({})
    finally:
        Input.Call = original
        if "GetCarriedItem" in C.engine.__dict__:
            del C.engine.GetCarriedItem
        C.engine.reset()
    return calls


def _flips(calls):
    return [call for call in calls if call[0] == "SkilletFlip"]


def testLeftClickWhileHoldingTheSkilletWithTheRightButtonReportsAFlip():
    calls = _run([("hold", SKILLET), ("left",)])
    assert _flips(calls) == [("SkilletFlip", {})]
    assert [call[0] for call in calls] == ["SkilletUseHeld", "SkilletFlip"], "先报按着，再报翻"
    assert len(_flips(_run([("hold", SKILLET), ("left",), ("left",)]))) == 2, "每点一下报一次（挡重复由服务端：翻的过程中再点不算）"


def testItIsAlsoWorkingWithTheSkilletInTheOffHandWhichIsTheCommonWayOnBedrock():
    C.engine.offhand = SKILLET
    calls = _run([("hold", {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}), ("left",)])
    assert len(_flips(calls)) == 1


def testNoFlipWithoutHoldingTheRightButtonOrWithoutASkillet():
    assert _flips(_run([("left",)])) == [], "没按住右键：左键就是普通的攻击 / 挖"
    assert _flips(_run([("hold", SKILLET), ("release",), ("left",)])) == [], "右键松开了"
    assert _flips(_run([("hold", {"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1}), ("left",)])) == [], "手里不是煎锅：根本没开始报按着"
    assert _flips(_run([("hold", None), ("left",)])) == []


def testTheFlipRidesTheSameWayAsTheHoldReportAndNeedsNoPlayerIdFromTheClient():
    """服务端的 SkilletFlip 端点用 @InjectHttpPlayerId 注入玩家，不信客户端传的：客户端只发一个空载荷。"""
    assert _flips(_run([("hold", SKILLET), ("left",)]))[0][1] == {}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
