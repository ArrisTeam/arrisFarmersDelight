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
