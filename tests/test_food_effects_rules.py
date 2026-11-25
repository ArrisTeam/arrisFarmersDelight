# -*- coding: utf-8 -*-
# runner: both
"""吃喝之后的追加结算（Shared/Rules/FoodEffects.py）：牛奶瓶随机清一个效果、热可可随机清一个有害效果。"""
from __future__ import print_function

import random

import fdtest

Rules = fdtest.load("Shared.Rules.FoodEffects")
Effects = fdtest.load("Shared.Data.Effects")

REMOVE = Rules.REMOVE


def _picks(itemName, active, seeds=400):
    """同一个状态下用不同种子吃很多次，返回每次动作列表。"""
    return [Rules.eatActions(itemName, active, random.Random(seed)) for seed in range(seeds)]


def testHotCocoaRemovesExactlyOneRandomHarmfulEffect():
    active = ["speed", "poison", "arris:nourishment", "weakness", "hunger"]
    removed = set()
    for actions in _picks("arris:hot_cocoa", active):
        assert len(actions) == 1 and actions[0][0] == REMOVE, actions
        assert actions[0][1] in ("poison", "weakness", "hunger"), "只会清有害效果: %r" % (actions,)
        removed.add(actions[0][1])
    assert removed == set(["poison", "weakness", "hunger"]), "三个有害效果都该有机会被清掉（不再总是第一个）: %r" % removed


def testHotCocoaLeavesBeneficialEffectsAlone():
    for actions in _picks("arris:hot_cocoa", ["speed", "arris:nourishment", "regeneration"], 50):
        assert actions == []
    assert Rules.eatActions("arris:hot_cocoa", [], random) == []


def testHotCocoaPicksTheOnlyHarmfulEffect():
    for actions in _picks("arris:hot_cocoa", ["speed", "nausea"], 30):
        assert actions == [(REMOVE, "nausea")]


def testMilkBottleRemovesOneRandomEffectOfAnyKind():
    active = ["speed", "poison", "arris:nourishment"]
    removed = set()
    for actions in _picks("arris:milk_bottle", active):
        assert len(actions) == 1 and actions[0][0] == REMOVE and actions[0][1] in active
        removed.add(actions[0][1])
    assert removed == set(active)
    assert Rules.eatActions("arris:milk_bottle", [], random) == []


def testNourishmentTiersMatchJeFoodValues():
    # FoodValues.java：BRIEF 600 刻 / SHORT 1200 / MEDIUM 3600 / LONG 6000
    assert (Effects.BRIEF_DURATION, Effects.SHORT_DURATION, Effects.MEDIUM_DURATION, Effects.LONG_DURATION) == (30, 60, 180, 300)
    assert Effects.NOURISHMENT == "arris:nourishment" and Effects.COMFORT == "arris:comfort"


def testVanillaSoupsGiveNourishmentLikeJe():
    # 默认配置：蘑菇煲、甜菜汤滋养 3 分钟；兔肉煲滋养 5 分钟，另加跳跃提升 II 10 秒（CommonEvents.handleVanillaSoupEffects）
    nourishment = lambda seconds: (Rules.ADD, "arris:nourishment", seconds, 0, False)
    assert Rules.eatActions("minecraft:mushroom_stew", [], random) == [nourishment(180)]
    assert Rules.eatActions("minecraft:beetroot_soup", ["speed", "poison"], random) == [nourishment(180)]
    rabbit = Rules.eatActions("minecraft:rabbit_stew", [], random)
    assert sorted(rabbit) == sorted([nourishment(300), (Rules.ADD, "jump_boost", 10, 1, True)]), rabbit


def testSoupBuffsDoNotDependOnWhatThePlayerAlreadyHas():
    for state in ([], ["arris:nourishment"], ["poison", "speed"]):
        assert len(Rules.eatActions("minecraft:rabbit_stew", state, random)) == 2


def testMelonJuiceHealsTwoAndPopsicleExtinguishes():
    assert Rules.eatActions("arris:melon_juice", [], random) == [(Rules.HEAL, 2.0)]
    assert Rules.eatActions("arris:melon_popsicle", ["poison"], random) == [(Rules.EXTINGUISH,)]
    assert Effects.MELON_JUICE_HEAL == 2.0


def testHealedValue():
    assert Rules.healedValue(10.0, 20.0, 2.0) == 12.0
    assert Rules.healedValue(19.0, 20.0, 2.0) == 20.0
    assert Rules.healedValue(20.0, 20.0, 2.0) is None, "满血"
    assert Rules.healedValue(0.0, 20.0, 2.0) is None, "已经倒下"
    assert Rules.healedValue(25.0, 30.0, 2.0) == 27.0


def testOtherFoodsHaveNoExtraActions():
    for itemName in ("minecraft:apple", "arris:cooked_rice", "arris:cake_slice"):
        assert Rules.eatActions(itemName, ["poison"], random) == [], itemName


def testHandledListsTheItemsWithRules():
    assert "arris:milk_bottle" in Rules.HANDLED and "arris:hot_cocoa" in Rules.HANDLED
    assert set(["minecraft:mushroom_stew", "minecraft:beetroot_soup", "minecraft:rabbit_stew"]) <= Rules.HANDLED
    for itemName in Rules.HANDLED:
        # 每个登记的食物在"身上有各种效果"时都应该产生动作（否则就不该登记）
        assert Rules.eatActions(itemName, ["poison", "speed"], random), itemName


def testHarmfulListStaysTheLinkedContract():
    # negativeEffect 同时是联动契约（linkage.md）里公开的表，热可可也靠它判断"有害"
    assert "poison" in Effects.negativeEffect and "speed" not in Effects.negativeEffect


def _effectColor(name):
    import io
    import json
    import os
    with io.open(os.path.join(fdtest.BP, "netease_effects", name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)["minecraft:effect"]["components"]["minecraft:particle_color"]


def testEffectColorsAreJavas():
    # JE NourishmentEffect：0xF3B300；ComfortEffect：10939391 = 0xA6EBFF
    assert _effectColor("nourishment") == [0xF3, 0xB3, 0x00]
    assert _effectColor("comfort") == [0xA6, 0xEB, 0xFF] and 10939391 == 0xA6EBFF


def testComfortHealsLikeJava():
    # JE 1.3.4 ComfortEffect.applyEffectTick：有生命恢复不管；玩家还有饱和度不管；没满血回 1；每 80 刻一次
    assert Rules.COMFORT_SECONDS == 80 / 20.0 and Rules.COMFORT_HEAL == 1.0
    assert Rules.comfortHeals(False, 0.0, 10.0, 20.0)
    assert not Rules.comfortHeals(True, 0.0, 10.0, 20.0)
    assert not Rules.comfortHeals(False, 0.5, 10.0, 20.0)
    assert not Rules.comfortHeals(False, 0.0, 20.0, 20.0)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
