# -*- coding: utf-8 -*-
# runner: both
"""热源方块的状态条件（Shared/Rules/HeatStates）：

  1. 三种写法：一个值（相等，布尔照点燃状态的写法也认 1 / "true"）、一组值（其中之一）、{"min": n} / {"max": n}（数值范围，布尔不算数）；
     几条都满足才算；读不到状态、缺这个状态、条件是空的都不满足
  2. 登记时的写法（normalize）：规整（unicode → str、tuple → list），写错的拒绝并说哪里不对
  3. 按 aux 列出满足条件的 aux（auxSet）：照引擎按位拼 aux 的样子（炼药锅 fill_level 7 个值占 3 位，aux 7、15、23 是空号）不漏、
     不停在空号上；越界之后一直给 None、一直给 {}、一直给同一份状态、一直给新的状态，都停得下来；
     照 2026-11-26 3.10 实机量到的炼药锅返回原样答（空号和越界都给缺省状态），算出来正是熔岩 1–6 级 = aux 9–14
"""
from __future__ import print_function

import fdtest

States = fdtest.load("Shared.Rules.HeatStates")
Cooking = fdtest.load("Shared.Data.Cooking")

LAVA = {"cauldron_liquid": "lava", "fill_level": {"min": 1}}
LIQUIDS = ("water", "lava", "powder_snow")


def cauldron(aux):
    """照引擎的样子：fill_level（7 个值，0–6）占低 3 位，cauldron_liquid（3 个值）占上面 2 位，值的位组合越界的是空号（None）。"""
    level, liquid = aux & 7, aux >> 3
    if level > 6 or liquid >= len(LIQUIDS):
        return None
    return {"fill_level": level, "cauldron_liquid": LIQUIDS[liquid]}


def testOneValueAGroupOfValuesAndARange():
    assert States.matches({"cauldron_liquid": "lava", "fill_level": 6}, LAVA)
    assert States.matches({"cauldron_liquid": "lava", "fill_level": 1}, LAVA)
    assert not States.matches({"cauldron_liquid": "lava", "fill_level": 0}, LAVA), "舀空了的不算"
    assert not States.matches({"cauldron_liquid": "water", "fill_level": 6}, LAVA), "盛水的不算"
    group = {"mymod:fuel": ["coal", "charcoal"], "mymod:level": {"min": 2, "max": 4}}
    assert States.matches({"mymod:fuel": "charcoal", "mymod:level": 2}, group) and States.matches({"mymod:fuel": "coal", "mymod:level": 4}, group)
    assert not States.matches({"mymod:fuel": "wood", "mymod:level": 3}, group) and not States.matches({"mymod:fuel": "coal", "mymod:level": 5}, group)
    assert not States.matches({"mymod:fuel": "coal", "mymod:level": 1}, group), "范围含两端，1 在外面"
    assert States.matches({"mymod:level": 9}, {"mymod:level": {"max": 9}}) and not States.matches({"mymod:level": 10}, {"mymod:level": {"max": 9}})


def testBooleansReadLikeTheLitRule():
    assert States.matches({"mymod:lit": True}, {"mymod:lit": True}) and States.matches({"mymod:lit": 1}, {"mymod:lit": True})
    assert States.matches({"mymod:lit": "true"}, {"mymod:lit": True}) and States.matches({"extinguished": False}, {"extinguished": False})
    assert not States.matches({"mymod:lit": False}, {"mymod:lit": True}) and not States.matches({"mymod:lit": 0}, {"mymod:lit": True})
    assert not States.matches({"mymod:level": True}, {"mymod:level": 1}), "写成数的条件不认布尔（Python 里 True == 1）"
    assert not States.matches({"mymod:level": True}, {"mymod:level": {"min": 1}}), "布尔不算数"


def testMissingOrUnreadableStatesNeverMatch():
    for states in (None, {}, [], "lava", {"fill_level": 6}, {"cauldron_liquid": "lava"}):
        assert not States.matches(states, LAVA), states
    assert not States.matches({"cauldron_liquid": "lava", "fill_level": 6}, {}), "空条件不算满足"
    assert not States.matches({"cauldron_liquid": "lava", "fill_level": 6}, None)


def testUnicodeAndLongValuesFromThePyTwoEngine():
    big = fdtest.load("Shared.Rules.TableWire").INT_TYPES[-1]
    assert States.matches({u"cauldron_liquid": u"lava", u"fill_level": big(6)}, LAVA)
    assert States.matches({"mymod:kind": u"炙"}, {"mymod:kind": u"炙".encode("utf-8") if str is bytes else u"炙"})


def testNormalizeKeepsGoodWritingsAndTidiesThem():
    fixed, problem = States.normalize({u"mymod:fuel": (u"coal", "charcoal"), "mymod:level": {"min": 2}, "mymod:lit": True})
    assert problem is None and fixed == {"mymod:fuel": ["coal", "charcoal"], "mymod:level": {"min": 2}, "mymod:lit": True}, (fixed, problem)
    assert all(isinstance(key, str) for key in fixed) and isinstance(fixed["mymod:fuel"][0], str)
    assert States.normalize({"fill_level": {"min": 1, "max": 6}}) == ({"fill_level": {"min": 1, "max": 6}}, None)
    assert States.normalize(LAVA) == (LAVA, None)


def testNormalizeRefusesWrongWritingsAndSaysWhy():
    bad = [None, {}, [], "lava", {"": 1}, {" x": 1}, {3: 1}, {"x": None}, {"x": 1.5}, {"x": []}, {"x": [1, None]}, {"x": [[1]]},
           {"x": {}}, {"x": {"least": 1}}, {"x": {"min": "1"}}, {"x": {"min": True}}, {"x": {"min": 3, "max": 2}},
           {"x": {"min": float("inf")}}, {"x": {"min": float("nan")}}, {"x": object()}, {"x": {"min": 1}, "y": set([1])}]
    for conditions in bad:
        fixed, problem = States.normalize(conditions)
        assert fixed is None and problem, (conditions, fixed, problem)


def testAuxSetFindsTheLavaCauldronPastTheHoles():
    found = States.auxSet(cauldron, LAVA)
    assert found["aux"] == [9, 10, 11, 12, 13, 14], found
    assert found["aux"] == Cooking.HeatSourceAuxDict["minecraft:cauldron"], "静态的初值就是照这个样子算的"
    assert found["top"] == 22 and found["asked"] == 2 * (22 + 1), "粉雪 6 级是最大的有效 aux；问到 46 停"
    water = States.auxSet(cauldron, {"cauldron_liquid": "water"})["aux"]
    assert water == [0, 1, 2, 3, 4, 5, 6]
    assert States.auxSet(cauldron, {"cauldron_liquid": "powder_snow", "fill_level": [3, 6]})["aux"] == [19, 22]


def testAuxSetStopsHoweverTheEngineAnswersBeyondTheEnd():
    def emptyAfter(aux):
        return cauldron(aux) if aux < 23 else {}

    def sameForever(aux):
        return cauldron(aux) if aux < 23 else cauldron(22)

    def clampAll(aux):
        return {"fill_level": 0, "cauldron_liquid": "water"}

    for read in (cauldron, emptyAfter, sameForever):
        found = States.auxSet(read, LAVA)
        assert found["aux"] == [9, 10, 11, 12, 13, 14] and found["asked"] == 46, (read.__name__, found)
    found = States.auxSet(clampAll, LAVA)
    assert found == {"aux": [], "top": 0, "asked": States.MIN_SCAN}, found
    found = States.auxSet(lambda aux: None, LAVA)
    assert found == {"aux": [], "top": -1, "asked": States.MIN_SCAN}, "一个状态都问不出来：问一小段就停（Server/HeatAux 据此不改表）"
    found = States.auxSet(lambda aux: {"mymod:n": aux}, {"mymod:n": {"min": 3, "max": 5}}, limit=100)
    assert found["aux"] == [3, 4, 5] and found["asked"] == 100, "引擎一直给新的状态：问到上限为止"
    assert States.auxSet(lambda aux: {"mymod:n": aux}, {"mymod:n": 2})["asked"] == States.LIMIT


def testAuxSetOnTheCauldronAsTheEngineReallyAnswers():
    """2026-11-26 3.10 实机（单机）量到的 GetBlockStatesFromAuxValue("minecraft:cauldron", aux)：aux 0–6 是水 0–6 级、8–14 熔岩 0–6 级、
    16–22 细雪 0–6 级；空号 7、15 和 23 以上（实机问到 40 都一样，这里问到多少都一样）返回缺省状态 {"cauldron_liquid": "water", "fill_level": 0}，
    不是 None、不是空、不抛异常。auxSet 把和前面重复的状态当"这个 aux 没有方块"：算出来正是 [9..14]，问到 46 就停（实机也是问了 46 次）。"""
    default = {"cauldron_liquid": "water", "fill_level": 0}
    asked = []

    def measured(aux):
        asked.append(aux)
        level, liquid = aux & 7, aux >> 3
        if level > 6 or liquid >= len(LIQUIDS):
            return dict(default)
        return {"fill_level": level, "cauldron_liquid": LIQUIDS[liquid]}

    assert measured(7) == measured(15) == measured(23) == measured(40) == measured(4000) == default and measured(0) == default
    del asked[:]
    found = States.auxSet(measured, LAVA)
    assert found["aux"] == [9, 10, 11, 12, 13, 14] == Cooking.HeatSourceAuxDict["minecraft:cauldron"], found
    assert found["top"] == 22 and found["asked"] == 46 and asked == list(range(46)), "停得下来：问到 2 × (22 + 1) = 46 就停"
    assert found["asked"] < States.LIMIT
    assert States.auxSet(measured, {"cauldron_liquid": "water"})["aux"] == [0, 1, 2, 3, 4, 5, 6], "缺省状态只算 aux 0 那一次，空号不混进来"


def testAuxSetOnABitPackedBlockWithSeveralHoleRuns():
    """三个状态 a（3 个值，占 2 位）、b（5 个值，占 3 位）、c（3 个值，占 2 位）：空号一段比一段长，满足条件的一个都不漏。"""
    def packed(aux):
        a, b, c = aux & 3, (aux >> 2) & 7, aux >> 5
        if a > 2 or b > 4 or c > 2:
            return None
        return {"a": a, "b": b, "c": c}

    every = [aux for aux in range(128) if packed(aux) is not None]
    found = States.auxSet(packed, {"c": 2, "b": {"min": 3}})
    assert found["aux"] == [aux for aux in every if (aux >> 5) == 2 and ((aux >> 2) & 7) >= 3], found
    assert found["top"] == max(every)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
