# -*- coding: utf-8 -*-
# runner: both
"""煎锅规则对 JE（Shared/Rules/SkilletRules.py）：烹饪时间换算、手持热源范围、按住状态、攻击冷却音效、耐久磨损、存取煎锅物品。

期望值抄自 FD 1.3.4 的 SkilletBlock.getSkilletCookingTime（float 运算 + Mth.clamp）手算的结果，不依赖 .refs：
    600 刻：30 秒 × 0.2 = 6 秒（120 刻）；火焰附加 I：30 × 0.15 = 4.5 -> 4 秒（80 刻）；II：30 × 0.1 = 3 秒（60 刻，到下限）
"""
from __future__ import print_function, unicode_literals

import fdtest

Rules = fdtest.load("Shared.Rules.SkilletRules")

# (配方时间, 火焰附加等级) -> 刻；手算见模块说明，后面几行是边界：下限 60 比配方原时间还大时取下限、配方时间 0 夹到 0
COOKING_TICKS = {
    (600, 0): 120, (600, 1): 80, (600, 2): 60, (600, 3): 60, (600, 4): 60, (600, 5): 60,
    (1200, 0): 240, (1200, 1): 180, (100, 0): 60, (40, 0): 60, (0, 0): 0,
}


def testCookingTicksMatchJe():
    for (original, level), expected in sorted(COOKING_TICKS.items()):
        assert Rules.cookingTicks(original, level) == expected, (original, level, Rules.cookingTicks(original, level))


def testDefaultCampfireRecipeCooksSixFourThreeSeconds():
    assert [Rules.cookingSeconds(Rules.CAMPFIRE_TICKS, level) for level in (0, 1, 2, 3)] == [6.0, 4.0, 3.0, 3.0]


def testFireAspectLevelReadsEnchantData():
    skillet = {"newItemName": "arris:skillet_item", "enchantData": [(9, 3), (13, 2)]}
    assert Rules.fireAspectLevel(skillet) == 2
    assert Rules.fireAspectLevel({"newItemName": "arris:skillet_item", "enchantData": [[9, 1]]}) == 0
    assert Rules.fireAspectLevel({"newItemName": "arris:skillet_item"}) == 0
    assert Rules.fireAspectLevel(None) == 0


def testHeatNeighbourhoodIsTheThreeByThreeByThreeAroundTheFeetBlock():
    cells = Rules.heatNeighbourhood((10.5, 64.0, -3.5))
    assert len(cells) == 27 and len(set(cells)) == 27
    assert (9, 63, -5) in cells and (11, 65, -3) in cells and (10, 64, -4) in cells
    assert (8, 64, -4) not in cells and (10, 66, -4) not in cells
    # 站在方块顶上脚的 y 可能是 63.9995：仍然算 64 那一层
    assert (10, 65, -4) in Rules.heatNeighbourhood((10.5, 63.9995, -3.5))


def testNearHeatLooksAtBlockNamesOnlyAndFireCounts():
    heat = ["minecraft:campfire", "arris:stove"]
    names = {(1, 64, 1): "arris:stove"}
    near = lambda pos: names.get(pos, "minecraft:air")  # noqa: E731
    assert Rules.nearHeat((1.5, 64.0, 2.5), near, heat) is True
    assert Rules.nearHeat((1.5, 64.0, 3.5), near, heat) is False          # z 差 2 格
    assert Rules.nearHeat((9.5, 64.0, 9.5), near, heat) is False
    assert Rules.nearHeat((9.5, 64.0, 9.5), near, heat, onFire=True) is True
    # 熄灭的营火名字不变：JE 只看标签，所以照样算（这里不读状态）
    assert Rules.nearHeat((1.5, 64.0, 2.5), lambda pos: "minecraft:campfire", heat) is True


def testHoldTrackerExpiresWhenTheClientGoesQuiet():
    holds = Rules.HoldTracker()
    assert holds.held("p", 0.0) is False
    holds.beat("p", 10.0)
    assert holds.held("p", 10.5) is True and holds.held("p", 10.0 + Rules.HOLD_TIMEOUT - 0.01) is True
    assert holds.held("p", 10.0 + Rules.HOLD_TIMEOUT + 0.01) is False
    holds.beat("p", 20.0)
    holds.release("p")
    assert holds.held("p", 20.1) is False
    assert Rules.HOLD_BEAT < Rules.HOLD_TIMEOUT


def testHandCookFinishesAfterItsSeconds():
    cook = Rules.HandCook("minecraft:beef", "minecraft:cooked_beef", 6.0, 100.0)
    assert not cook.finished(105.9) and cook.finished(106.0)


def testSizzleChanceAccumulatesTheJePerTickChance():
    assert abs(Rules.sizzleChance(1.0 / 20) - 0.02) < 1e-9
    assert abs(Rules.sizzleChance(0.25) - (1 - 0.98 ** 5)) < 1e-9


def testAttackClockPicksStrongOrWeakByTheSkilletAttackDelay():
    # 攻击速度 4.0 - 3.1 = 0.9 次 / 秒：一次间隔 22.2 刻，够 80%（17.8 刻，约 0.889 秒）才算重击
    assert abs(0.8 / Rules.ATTACK_SPEED - 0.8889) < 1e-3
    clock = Rules.AttackClock()
    assert clock.sound("p", 100.0) == Rules.SOUND_STRONG              # 没有记录的第一次
    assert clock.sound("p", 100.5) == Rules.SOUND_WEAK                # 连点
    assert clock.sound("p", 101.4) == Rules.SOUND_STRONG              # 离上一次（100.5）0.9 秒，够了


def testAttackClockBoundaryAndPerPlayer():
    clock = Rules.AttackClock()
    clock.sound("p", 0.0)
    assert clock.sound("p", 0.88) == Rules.SOUND_WEAK                 # 0.88 秒 = 17.6 刻 < 17.8
    clock.sound("p", 10.0)
    assert clock.sound("p", 10.9) == Rules.SOUND_STRONG
    assert clock.sound("q", 10.1) == Rules.SOUND_STRONG               # 各玩家各记各的


def testWearIsCappedAtOnePointPerHit():
    assert Rules.wearAfter(250, 248) == 249          # 引擎磨损 2 点 -> 按 1 点
    assert Rules.wearAfter(250, 249) == 249
    assert Rules.wearAfter(250, 250) == 250
    assert Rules.wearAfter(100, 200) == 200          # 修复不动
    assert Rules.wearAfter(1, -1) == 0               # 用到头：基岩版损伤 > 最大耐久才坏，这一下还剩 0
    assert Rules.wearAfter(0, -2) == -1              # 再打一下才坏


def testStoreAndRestoreKeepDamageEnchantsAndName():
    held = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1, "durability": 137,
            "enchantData": [(13, 2), (9, 1)], "customTips": "", "extraId": "x", "showInHand": True,
            "userData": {"display": {"Name": "煎锅"}, "RepairCost": 1}, "itemName": "arris:skillet_item"}
    stored = Rules.storeItem(held)
    assert stored["durability"] == 137 and stored["count"] == 1 and "showInHand" not in stored and "itemName" not in stored
    assert stored["enchantData"] == [[13, 2], [9, 1]]                  # 元组换成列表（方块实体数据只收同类元素的列表）
    assert stored["userData"] == {"display": {"Name": "煎锅".encode("utf-8") if str is bytes else "煎锅"}, "RepairCost": 1}
    again = Rules.restoreItem(stored)
    assert again["enchantData"] == [(13, 2), (9, 1)] and again["durability"] == 137 and again["count"] == 1
    assert Rules.fireAspectLevel(again) == 2


def testStoreNeverAcceptsAnotherItemName():
    stored = Rules.storeItem({"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 3})
    assert stored["newItemName"] == "arris:skillet_item" and stored["count"] == 1


def testRestoreWithoutRecordIsAFreshSkillet():
    for nothing in (None, {}):
        fresh = Rules.restoreItem(nothing)
        assert fresh == {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1}


def testStoredValuesAreEngineSafe():
    """方块实体数据：键是 str、没有元组、py2 下没有 unicode 值。"""
    held = {"newItemName": "arris:skillet_item", "enchantData": [(13, 1)], "userData": {"display": {"Name": u"煎锅"}}}
    stored = Rules.storeItem(held)

    def walk(value):
        assert not isinstance(value, tuple)
        if isinstance(value, dict):
            for key, item in value.items():
                assert isinstance(key, str), key
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif str is bytes:
            assert not isinstance(value, type(u"")), value
    walk(stored)


def testBreakMarksExpireAndAreTakenOnce():
    marks = Rules.BreakMarks()
    marks.put((0, 1, 2, 3), 100.0)
    assert marks.take((0, 1, 2, 3), 101.0) is True
    assert marks.take((0, 1, 2, 3), 101.0) is False
    marks.put((0, 1, 2, 3), 100.0)
    assert marks.take((0, 1, 2, 3), 100.0 + Rules.BreakMarks.SECONDS + 1) is False
    assert marks.take((0, 9, 9, 9), 100.0) is False


def _text(value):
    """py2 下模块里的中文是 UTF-8 的 str，和本文件的 unicode 字面量比之前先解码。"""
    return value.decode("utf-8") if isinstance(value, bytes) else value


def testTipsAreTheJeZhCnTexts():
    # JE lang zh_cn：item.farmersdelight.skillet.how_to_cook / .underwater，block.farmersdelight.skillet.invalid_item / .underwater
    assert _text(Rules.TIP_HOW_TO_COOK) == "用另一只手拿着原料！"
    assert _text(Rules.TIP_UNDERWATER_HAND) == "在水里可没法煎啊……"
    assert _text(Rules.TIP_INVALID_ITEM) == "这东西可不能被烹饪……"
    assert _text(Rules.TIP_UNDERWATER_BLOCK) == "被水泡着可没法烹饪啊……"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
