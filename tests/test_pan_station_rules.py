# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点的纯规则（Shared/Rules/PanStation.py）：能煎什么、一面多久、徽章与提示。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.PanStation")


def _item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testWhatFriesAndWhatItBecomes():
    assert Rules.canFry("minecraft:beef") and Rules.friedOf("minecraft:beef") == "minecraft:cooked_beef"
    assert not Rules.canFry("minecraft:cooked_beef"), "煎好的不再煎"
    assert Rules.isOneSided("minecraft:egg") and not Rules.isOneSided("minecraft:beef")


def testASideTakesLongerForABiggerBatch():
    assert abs(Rules.sideSeconds(1) - 2.0) < 1.0e-9, "一件：6 / 1.5 / 2 = 2 秒一面"
    assert abs(Rules.sideSeconds(16) - 8.0) < 1.0e-9, "16 件：乘 sqrt(16)"


def testTheBadgeFollowsTheSideOnThePan():
    assert Rules.badgeOf({}) is None
    frying = {"item": _item("minecraft:beef", 4), "byHand": True, "down": 0.5, "up": 0.0}
    assert Rules.badgeOf(frying) == {"item": frying["item"], "stars": None, "progress": 0.5}
    assert Rules.badgeOf(dict(frying, byHand=False))["progress"] is None, "FD 原样煎时不显示两面进度"
    assert Rules.badgeOf(dict(frying, done=True))["progress"] is None


def testTheHintSaysWhatToDoNext():
    assert "放进锅里" in Rules.statusText({})
    beef = {"item": _item("minecraft:beef", 4), "heated": True, "byHand": True, "batch": 4, "down": 0.3, "up": 0.0}
    assert "第一面" in Rules.statusText(beef) and "4 个" in Rules.statusText(beef)
    assert "翻面" in Rules.statusText(dict(beef, down=1.0))
    assert "第二面" in Rules.statusText(dict(beef, down=0.2, up=1.0))
    assert "取出" in Rules.statusText(dict(beef, done=True))
    assert "热源" in Rules.statusText(dict(beef, heated=False))
    assert "自己" in Rules.statusText(dict(beef, byHand=False))
    assert "不用翻" in Rules.statusText(dict(beef, item=_item("minecraft:egg"), oneSided=True))
    assert all("%" not in Rules.statusText(d) for d in (beef, dict(beef, down=1.0))), "标签会吞掉 %"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
