# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点的纯规则（Shared/Rules/GrillStation.py）：烤位、一面多久、该翻的那件、提示文字。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.GrillStation")
Cooking = fdtest.load("Shared.Data.Cooking")


def _slot(name="minecraft:beef", **extra):
    slot = {"item": {"newItemName": name, "newAuxValue": 0, "count": 1}, "byHand": True, "down": 0.0, "up": 0.0}
    slot.update(extra)
    return slot


def testWhatOpensTheGrill():
    """StoveStation.opens：空手、能烤的、食物、刀和工具、碗和瓶开站；盖着东西、炉灶自己用得上的、别的东西不开。"""
    assert Rules.opens(None, "", False) and Rules.opens("minecraft:beef", "food", False)
    assert Rules.opens("minecraft:bread", "food", False) and Rules.opens("minecraft:carrot", "food", False), "食物都开，哪怕不能烤"
    assert Rules.opens("arris:iron_knife", "sword", False) and Rules.opens("minecraft:iron_axe", "axe", False)
    assert Rules.opens("minecraft:bowl", "", False) and Rules.opens("minecraft:glass_bottle", "", False)
    for held, kind in (("arris:cooking_pot", "block"), ("arris:skillet", "block"), ("minecraft:flint_and_steel", ""),
                       ("minecraft:fire_charge", ""), ("minecraft:iron_shovel", "shovel"), ("minecraft:water_bucket", "bucket"),
                       ("minecraft:stick", ""), ("minecraft:iron_sword", "sword")):
        assert not Rules.opens(held, kind, False), held
    assert not Rules.opens(None, "", True) and not Rules.opens("minecraft:beef", "food", True), "上面摆着锅：烤架是它的"


def testSixPlacesAndTheSameTableAsTheSkillet():
    assert Rules.PLACES == 6 and Rules.slotCenter(0) == (0.25, 0.27)
    assert Rules.canGrill("minecraft:beef") and Rules.grilledOf("minecraft:beef") == "minecraft:cooked_beef"
    assert Rules.STOVE_BLOCKS is Cooking.StoveList, "附属包追加的炉灶也开站：用同一个列表对象"


def testASideIsAThirdOfTheStoveTime():
    assert abs(Rules.sideSeconds() - 10.0) < 1.0e-9, "30 / 1.5 / 2 = 10 秒（JE：营火 600 刻 / 1.5 / 2）"


def testOnlyAPieceDoneOnTheGrillSideWaitsToBeTurned():
    assert Rules.waitsToTurn(_slot(down=1.0))
    assert not Rules.waitsToTurn(_slot(down=0.5))
    assert not Rules.waitsToTurn(_slot(down=1.0, up=1.0))
    assert not Rules.waitsToTurn(_slot("minecraft:egg", down=1.0, oneSided=True)), "蛋不用翻"
    assert not Rules.waitsToTurn(_slot(down=1.0, byHand=False)), "FD 原样烤着的不等翻"


def testTheHintSaysWhatToDoNext():
    assert "摆上灶台" in Rules.statusText({"slots": [{}] * 6})
    assert "翻过来" in Rules.statusText({"slots": [_slot(down=1.0)] + [{}] * 5})
    assert "取下" in Rules.statusText({"slots": [_slot(done=True), _slot(down=1.0)]})
    assert "自己" in Rules.statusText({"slots": [_slot(byHand=False)]})
    assert "翻面" in Rules.statusText({"slots": [_slot(down=0.4)]})


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
