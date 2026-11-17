# -*- coding: utf-8 -*-
# runner: both
"""有人开着厨锅的经典界面时，站点里厨师放的料也按 FD 原样自己煮（Server/HandCooking.setMenuViewers + Server/CookingPotHost.onViewers）。

HoD PotCooking.beforeCooking（201-203）：!stirred && (!byHand || !attended() || !stirringRequired || pot.handson$isInMenu())，
handson$isInMenu（CookingPotStirringMixin:114-125）是任何玩家的 containerMenu 是这口锅的 CookingPotMenu。基岩版的经典界面是 dolorContainer
的界面，谁开着由库的方块宿主的 onViewers 告诉厨锅宿主（CookingPotHost），再由它交给 HandCooking。引擎是 potfake.py 里的假的。
"""
from __future__ import print_function

import sys
import types

import dgtest
import fdtest
import potfake
import potkit as K
from potkit import POT, TOMATO, fake

HandCooking = K.HandCooking
PotCooking = HandCooking.PotCooking


# ---------------------------------------------------------------- 烹饪

def testFoodTheCookPutInCooksItsOwnWayWhileSomeoneHasTheClassicScreenOpen():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 8)
    K.run(manager, 3.0)
    hand = HandCooking.handOf(0, POT)
    assert hand.mode == PotCooking.WAITING and hand.clock.cookTime == 0.0 and K.preview() == {}, "没人搅：手放的料等勺子"
    HandCooking.setMenuViewers(0, POT, ["b"])                 # b 开着这口锅的经典界面
    K.run(manager, 6.0)
    assert hand.mode == PotCooking.FD_WAY and K.preview()["count"] == 1, "FD 原样每 5 秒一份：不用搅"
    assert hand.clock.byHand is True, "料还是记着是手放的"
    HandCooking.setMenuViewers(0, POT, [])                    # b 关了界面
    waited = hand.clock.cookTime
    assert waited > 0.5, "第二份煮了一阵"
    K.run(manager, 3.0)
    assert hand.mode == PotCooking.WAITING and hand.clock.cookTime <= waited, "没人开着了：又等勺子，进度不再涨（换煮法时只按速度折算）"


def testTheScreenOfAnotherPotChangesNothing():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 8)
    HandCooking.setMenuViewers(0, (1, 2, 3), ["b"])
    K.run(manager, 6.0)
    assert HandCooking.handOf(0, POT).mode == PotCooking.WAITING and K.preview() == {}


def testSeveralViewersCountAsOneOpenScreenAndTheLastOneToLeaveEndsIt():
    manager, data = K.setup()
    HandCooking.setMenuViewers(0, POT, ["b", "c"])
    HandCooking.setMenuViewers(0, POT, ["c"])
    assert (0, POT) in HandCooking._menus
    HandCooking.setMenuViewers(0, POT, [])
    assert (0, POT) not in HandCooking._menus


# ---------------------------------------------------------------- 宿主：库说谁在看，告诉锅

class _Type(object):
    def __init__(self, typeId, title, menu, host=None):
        self.typeId, self.host = typeId, host


def _host():
    """Server/CookingPotHost 用库的方块宿主（真的）和一个替身 Api（库的 Server.Api 要引擎）导入，返回它登记的宿主和方块宿主模块。"""
    apiName = fdtest.SCRIPTS + ".dolorContainer.Server.Api"
    registered = []
    api = types.ModuleType(apiName)
    api.ContainerType, api.registerContainerType = _Type, registered.append
    sys.modules[apiName] = api
    fdtest.load("dolorContainer.Server").Api = api        # py2 的 from 包 import 子模块 要包上有这个属性
    Block = fdtest.load("dolorContainer.Std.Block.Server")
    Block._installed[0] = True                         # 不真的去监听引擎事件（库的说明：离线测试预先设为真）
    potfake.load("Server.CookingPotHost")
    assert len(registered) == 1
    return registered[0].host, Block


def testTheHostTellsThePotWhoHasItsClassicScreenOpen():
    host, Block = _host()
    manager, data = K.setup()
    key = Block.blockKey(0, POT)
    host.onViewers(key, ["b"])
    assert HandCooking._menus == set([(0, POT)]), "库说 b 开着这口锅的界面"
    host.onViewers(key, [])
    assert HandCooking._menus == set(), "没人开着了"
    host.onViewers("not a block key", ["b"])
    assert HandCooking._menus == set(), "不是方块的实例键：不理"


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
