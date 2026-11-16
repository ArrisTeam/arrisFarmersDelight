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


def testOtherFoodsHaveNoExtraActions():
    for itemName in ("minecraft:apple", "arris:cooked_rice", "arris:cake_slice"):
        assert Rules.eatActions(itemName, ["poison"], random) == [], itemName


def testHandledListsTheItemsWithRules():
    assert "arris:milk_bottle" in Rules.HANDLED and "arris:hot_cocoa" in Rules.HANDLED
    for itemName in Rules.HANDLED:
        # 每个登记的食物在"身上有各种效果"时都应该产生动作（否则就不该登记）
        assert Rules.eatActions(itemName, ["poison", "speed"], random), itemName


def testHarmfulListStaysTheLinkedContract():
    # negativeEffect 同时是联动契约（linkage.md）里公开的表，热可可也靠它判断"有害"
    assert "poison" in Effects.negativeEffect and "speed" not in Effects.negativeEffect


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
