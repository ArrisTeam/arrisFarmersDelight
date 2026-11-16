# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点的纯规则（Shared/Rules/PanStation.py）：能煎什么、一面多久、徽章与提示。"""
from __future__ import print_function

import dgtest
import fdtest

Rules = fdtest.load("Shared.Rules.PanStation")
Kit = dgtest.load("Shared.Schema")


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


def testTheSchemaHasOneKeptPanSlotThatTakesABatchOfWhatFries():
    schema = Rules.buildSchema(Kit)
    group = schema.slotGroup("pan")
    assert schema.groupNames == ["pan"] and group.size == 1 and group.rules.maxStack == 16, "一格、最多一批 16 件"
    assert not group.rules.returnOnClose, "kept：关站不退，东西留在锅里接着煎"
    assert group.rules.canAccept(_item("minecraft:beef")) and group.rules.canAccept(_item("minecraft:egg"))
    assert not group.rules.canAccept(_item("minecraft:cooked_beef")) and not group.rules.canAccept(_item("minecraft:stick"))
    assert group.rules.limitFor(_item("minecraft:egg"), lambda item: 16) == 16
    assert group.rules.limitFor(_item("minecraft:egg"), lambda item: 8) == 8, "堆叠上限比一批小的取小的（SkilletCooking.place）"


def testOnlyTheSameFoodGoesInOnTopOfWhatLies():
    beef = _item("minecraft:beef", 3)
    assert Rules.mayPlace(None, beef) and Rules.mayPlace({}, beef), "空锅什么煎得了的都收"
    assert Rules.mayPlace(_item("minecraft:beef", 5), beef), "同一种"
    assert not Rules.mayPlace(_item("minecraft:porkchop", 5), beef), "锅里是别的：一种一种来"
    assert not Rules.mayPlace(_item("minecraft:cooked_beef", 2), beef), "锅里是煎好的：不能再放生的"
    assert not Rules.mayPlace(None, _item("minecraft:cooked_beef")) and not Rules.mayPlace(None, _item("minecraft:stick")) and not Rules.mayPlace(None, None)
    assert not Rules.mayPlace(_item("minecraft:beef", 1), dict(beef, newAuxValue=3)), "名字和 aux 都要一样"


def testFireAspectOnThePlacedSkilletShortensASide():
    assert abs(Rules.sideSeconds(1, 0) - 2.0) < 1e-9
    assert abs(Rules.sideSeconds(1, 1) - 1.35) < 1e-9, "火焰附加 I：4 秒一件，一面 80 * 1 / 1.5 / 2 = 26.67 刻取整 27 刻"
    assert abs(Rules.sideSeconds(1, 2) - 1.0) < 1e-9 and abs(Rules.sideSeconds(1, 3) - 1.0) < 1e-9, "II 起 3 秒一件（下限 60 刻）"
    assert abs(Rules.sideSeconds(16, 2) - 4.0) < 1e-9


def testTheTrayLightsWhatTheCampfireCooks():
    assert Rules.usable("minecraft:beef") and Rules.usable("minecraft:egg") and not Rules.usable("minecraft:cooked_beef") and not Rules.usable("minecraft:bowl")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
