# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点的纯规则（Shared/Rules/PanStation.py）：能煎什么、一面多久、站点声明、放得进吗。"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

Rules = fdtest.load("Shared.Rules.PanStation")
Grill = fdtest.load("Shared.Rules.GrillStation")
Cooking = fdtest.load("Shared.Data.Cooking")
Kit = dgtest.load("Shared.Schema")


def _item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testWhatFriesAndWhatItBecomes():
    assert Rules.canFry("minecraft:beef") and Rules.friedOf("minecraft:beef") == "minecraft:cooked_beef"
    assert not Rules.canFry("minecraft:cooked_beef"), "煎好的不再煎"
    assert Rules.isOneSided("minecraft:egg") and not Rules.isOneSided("minecraft:beef")


def testOnlyTheEggIsCrackedAndOneSidedIsAnotherList():
    """HoD 的两个标签：cracked（蛋：打开了躺着、画成煎蛋、在锅沿磕开，KitchenLooks.isCracked / opened）和 one_sided（只煎一面、不翻，
    SkilletCooking.isOneSided，缺省是 #cracked）。这边一个是 PotSunk.CRACKED，一个是联动契约的 OneSidedList，缺省两样都只有蛋；
    下游往 OneSidedList 里加的只煎一面，不因此变成蛋。炉灶和煎锅同一张表。"""
    assert Rules.isCracked("minecraft:egg") and not Rules.isCracked("minecraft:beef") and not Rules.isCracked("arris:fried_egg")
    assert Cooking.OneSidedList == ["minecraft:egg"] and Rules.CRACKED == frozenset(["minecraft:egg"]), "缺省：两样都只有蛋"
    assert Grill.isCracked is Rules.isCracked and Grill.isOneSided is Rules.isOneSided
    Cooking.OneSidedList.append("minecraft:potato")
    try:
        assert Rules.isOneSided("minecraft:potato") and not Rules.isCracked("minecraft:potato"), "只煎一面的马铃薯不是蛋"
        assert Rules.isCracked("minecraft:egg") and Rules.isOneSided("minecraft:egg"), "蛋照旧"
    finally:
        Cooking.OneSidedList.remove("minecraft:potato")
    assert Cooking.OneSidedList == ["minecraft:egg"]


def testASideTakesLongerForABiggerBatch():
    assert abs(Rules.sideSeconds(1) - 2.0) < 1.0e-9, "一件：6 / 1.5 / 2 = 2 秒一面"
    assert abs(Rules.sideSeconds(16) - 8.0) < 1.0e-9, "16 件：乘 sqrt(16)"


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
