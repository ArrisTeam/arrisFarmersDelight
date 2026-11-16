# -*- coding: utf-8 -*-
# runner: both
"""炉灶上面那格算不算盖住了烤架（Shared/Rules/StoveCover.py）：FD 的 isStoveTopCovered 看形状，基岩版只认名字——
除了空气和液体都算；站点开不开（GrillStation.opens 的 covered）、站点收不收、经典玩法丢不丢用的是同一个函数。"""
from __future__ import print_function

import fdtest

Cover = fdtest.load("Shared.Rules.StoveCover")
Rules = fdtest.load("Shared.Rules.GrillStation")


def testPotsSkilletsBoardsAndEveryOtherBlockCoverTheGrill():
    for name in ("arris:cooking_pot", "arris:skillet", "arris:cutting_board", "minecraft:stone", "minecraft:oak_slab", "minecraft:carpet",
                 "minecraft:torch", "minecraft:red_flower", "minecraft:snow_layer"):
        assert Cover.covers(name), name


def testAirLiquidsAndUnknownAboveDoNotCover():
    for name in ("minecraft:air", "minecraft:cave_air", "minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava",
                 "minecraft:light_block", "", None):
        assert not Cover.covers(name), name


def testACoveredStoveDoesNotOpenTheStationWhateverIsInHand():
    """上面摆着锅（FD 的锅 / 煎锅形状都碰得到烤架区）：烤架是它们的，站点不开，和"盖住了就丢东西"是同一个判断。"""
    assert not Rules.opens(None, "", Cover.covers("arris:cooking_pot")) and not Rules.opens("minecraft:beef", "food", Cover.covers("arris:skillet"))
    assert Rules.opens(None, "", Cover.covers("minecraft:air")) and Rules.opens("minecraft:beef", "food", Cover.covers("minecraft:water"))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
