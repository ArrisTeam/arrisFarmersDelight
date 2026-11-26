# -*- coding: utf-8 -*-
# runner: both
"""客户端"身边有没有热源"（Client/Input._nearHeat：副手煎锅、主手能煎的东西时，这一下右键是煎不是吃）和服务端（Server/SkilletHand）同一条规则：
名单、热源标签，加上 JE 标签里的熔岩炼药锅——基岩版（3.10 实机）它是炼药锅 minecraft:cauldron 的状态 cauldron_liquid = lava，
客户端读不到方块状态，按 aux 认（aux = fill_level + 8 × cauldron_liquid；熔岩、6 级是 14）。
QuModLibs 和引擎换成假的：只给脚的位置、方块（名字, aux）、副手。"""
from __future__ import print_function

import sys
import types

import fdtest

PACKAGE = fdtest.SCRIPTS
FEET = (0.5, 64.0, 0.5)                      # 站在格 (0, 64, 0)：3x3x3 是 x、z -1..1，y 63..65
blocks = {}
offhand = [None]


class _Comp(object):
    def __init__(self, **methods):
        self.__dict__.update(methods)


class _Factory(object):
    def CreatePos(self, target=None):
        return _Comp(GetFootPos=lambda: FEET)

    def CreateBlockInfo(self, target=None):
        return _Comp(GetBlock=lambda pos: blocks.get(tuple(pos), ("minecraft:air", 0)))

    def CreateItem(self, target=None):
        return _Comp(GetOffhandItem=lambda getUserData=False: offhand[0])


class _ClientApi(object):
    @staticmethod
    def GetEngineCompFactory():
        return _Factory()


def _install():
    quPackage = types.ModuleType(PACKAGE + ".QuModLibs")
    quPackage.__path__ = []
    quClient = types.ModuleType(PACKAGE + ".QuModLibs.Client")
    quClient.clientApi, quClient.levelId, quClient.playerId = _ClientApi(), "level", "me"
    quClient.Call = lambda *args: None
    quClient.Listen = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules[PACKAGE + ".QuModLibs"], sys.modules[PACKAGE + ".QuModLibs.Client"] = quPackage, quClient


_install()
Input = fdtest.load("Client.Input")
SKILLET = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1}
BEEF = {"itemDict": {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3}}


def _near(block, pos=(1, 63, 0)):
    blocks.clear()
    blocks[pos] = block
    return Input._nearHeat()


def testALavaCauldronIsReadFromItsAux():
    assert _near(("minecraft:cauldron", 14)) is True, "熔岩、6 级"
    assert _near(("minecraft:cauldron", 6)) is False, "盛水 6 级"
    assert _near(("minecraft:cauldron", 8)) is False, "熔岩、0 级：舀空了"
    assert _near(("minecraft:cauldron", 0)) is False
    assert _near(("minecraft:cauldron", 14), pos=(2, 63, 0)) is False, "x 差 2 格：在 3x3x3 外面"


def testTheOtherHeatSourcesAreStillReadByName():
    assert _near(("minecraft:campfire", 0)) is True and _near(("arris:stove", 2)) is True and _near(("minecraft:magma", 0)) is True
    assert _near(("arris:stove_extinguish", 2)) is False and _near(("minecraft:stone", 0)) is False


def testNextToALavaCauldronTheRightClickCooksInsteadOfEating():
    """副手煎锅、主手生牛肉：身边有熔岩炼药锅时取消"吃"（服务端那边开始手持煎），盛水的不取消。"""
    offhand[0] = SKILLET
    try:
        for aux, cancelled in ((14, True), (6, False)):
            blocks.clear()
            blocks[(0, 63, -1)] = ("minecraft:cauldron", aux)
            args = dict(BEEF)
            Input.OnClientItemTryUse(args)
            assert bool(args.get("cancel")) is cancelled, aux
    finally:
        offhand[0] = None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
