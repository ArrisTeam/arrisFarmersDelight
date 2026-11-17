# -*- coding: utf-8 -*-
# runner: both
"""潜行右键厨锅不开站点（HoD 的 CookingPotStation.opens：潜行时不开，"Sneaking keeps the pot's handle toggle"）：站点登记时没有关掉前置包的
sneakFallback，所以潜行的右键不被客户端取消、到服务端的方块宿主那里切吊把手（Server/CookingPotHost.use）。
真的入口、真的站点模块、真的前置包客户端 Registry，引擎是 bootkit 里的无害替身。
"""
from __future__ import print_function

import bootkit as B
import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgflow as F
from optkit import Config


def testThePotStationKeepsTheSneakFallbackSoASneakingClickNeverOpensIt():
    B.bootClient()
    entry = B.ClientRegistry.behaviorOf(B.POT_BLOCK)
    assert entry is not None and entry.stationId == B.POT
    assert entry.sneakFallback is True, "潜行右键走方块原本的玩法：切吊把手；不取消、不开站"


def testASneakingClickIsNotTheStationsSoItGoesOnToTheServerAndASneakFreeOneIs():
    """内核（Client/Controller.tryOpen）：登记时没关 sneakFallback 的站点，潜行右键不认（返回假：不取消、不开站，请求到服务端的方块宿主那里切把手），不潜行才开。"""
    controller = F.setup()
    F.world.sneaking = True
    assert F.click(controller) is False and controller.view is None
    F.world.sneaking = False
    assert F.click(controller) is True and controller.view is not None


def testTheOtherStationsKeepItToo():
    B.bootClient()
    for block in (B.BOARD_BLOCK, B.SKILLET_BLOCK, B.STOVE_BLOCK):
        assert B.ClientRegistry.behaviorOf(block).sneakFallback is True, block


def testWithTheStationSwitchedOffTheClassicClickIsAllThereIs():
    with Config(cooking_pot=False):
        B.bootClient()
    assert B.ClientRegistry.behaviorOf(B.POT_BLOCK) is None, "HoD 配置里关了 cooking_pot：不登记，普通右键不再被取消，到方块宿主那里开经典界面"


if __name__ == "__main__":
    raise SystemExit(B.dgtest.run(globals()))
