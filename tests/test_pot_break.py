# -*- coding: utf-8 -*-
# runner: both
"""拆厨锅（Server/CookingPot.OnCookingPotRemove，引擎是 potfake.py 里的假的）：煮过几份还没领的经验在锅心弹出来。

FD：CookingPotBlock.onRemove 先 dropContents、再 getUsedRecipesAndPopExperience(level, Vec3.atCenterOf(pos))，不看是谁拆的（创造模式拆也弹）。
"""
from __future__ import print_function

import random as realRandom
import time

import dgtest
import potkit as K
from potkit import POT, SAUCE, fake

ARGS = {"x": POT[0], "y": POT[1], "z": POT[2], "dimension": 0}
CENTRE = (POT[0] + 0.5, POT[1] + 0.5, POT[2] + 0.5)


def _broken(roll=0.0):
    """引擎报这口锅没了（方块实体数据这一刻还读得到）；经验的零头掷出 roll。"""
    K.PotContainer.random = K.FixedRandom(roll)
    try:
        K.CookingPot.OnCookingPotRemove(dict(ARGS))
    finally:
        K.PotContainer.random = realRandom


def testBreakingThePotPopsTheExperienceNobodyCollectedAtTheBlockCentre():
    manager, data = K.setup()
    K.PotContainer.addUsed(data, SAUCE, 8)                   # 煮了 8 份番茄酱，没人盛
    _broken()
    assert K.orbs() == [3], "8 份 x 0.35 = 2.8：整数部分 2，零头 0.8 掷到 0.0 进一"
    orb = list(fake.orbs.values())[0]
    assert orb["pos"] == CENTRE and orb["dim"] == 0, "在方块中心（Vec3.atCenterOf），不是脚下也不是锅口上方"
    assert data["potUsed"] is None, "记着的份数清掉了"


def testTheFractionIsRolledJustLikeWhenServing():
    manager, data = K.setup()
    K.PotContainer.addUsed(data, SAUCE, 8)
    _broken(roll=0.99)
    assert K.orbs() == [2], "零头 0.8 没掷中（0.99）就不进一"


def testACreativeBreakPopsItTooButDropsNoPot():
    manager, data = K.setup(creative=True)
    K.PotContainer.addUsed(data, SAUCE, 8)
    K.CookingPotItem._creativeBreaks.put((0, POT[0], POT[1], POT[2]), time.time())     # 引擎先报玩家要拆，方块没了才报移除
    _broken()
    assert K.orbs() == [3], "JE 的 onRemove 不看创造"
    assert fake.spawned == [], "创造模式拆不出厨锅（战利品表只在非创造时结算）"


def testAPotNobodyCookedInPopsNothingAndStillDropsThePot():
    manager, data = K.setup()
    _broken()
    assert K.orbs() == [] and [item["newItemName"] for item, _dim, _pos in fake.spawned] == ["arris:cooking_pot"]


def testAPotPushedAwayByAPistonIsNotBrokenSoItKeepsItsExperience():
    manager, data = K.setup()
    K.PotContainer.addUsed(data, SAUCE, 8)
    fake.world.blocks[(0, POT)] = "minecraft:moving_block"
    _broken()
    assert K.orbs() == [] and data["potUsed"] == {SAUCE: 8} and fake.spawned == []


def testAPotWhoseDataCannotBeReadStillDropsThePot():
    manager, data = K.setup()
    del fake.blockEntities[(0, POT)]                         # /setblock 放的旧锅读不到方块实体数据
    _broken()
    assert K.orbs() == [] and len(fake.spawned) == 1


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
