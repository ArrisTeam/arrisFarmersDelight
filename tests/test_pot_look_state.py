# -*- coding: utf-8 -*-
# runner: both
"""厨锅"看上去是什么样"的状态（Shared/Rules/PotLookState.py）：解读广播、浮着哪几格、新放进哪几格、进度外推。"""
from __future__ import print_function

import fdtest

State = fdtest.load("Shared.Rules.PotLookState")


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def _payload(**changes):
    payload = {"items": [_item("arris:tomato", 4), {}, _item("minecraft:milk_bucket"), {}, {}, {}], "served": {}, "meal": {},
               "dish": _item("arris:tomato_sauce"), "sunk": [2], "heated": True, "stirring": False, "spoon": [0.5, -0.25],
               "progress": 0.25, "rate": 0.1, "cooking": False}
    payload.update(changes)
    return payload


def testDecodeReadsEveryField():
    look = State.decode(_payload(), 10.0)
    assert look.items[0] == _item("arris:tomato", 4) and look.items[1] is None and len(look.items) == 6
    assert look.dish["newItemName"] == "arris:tomato_sauce" and look.meal is None and look.served is None
    assert look.sunk == frozenset([2]) and look.heated and not look.stirring and look.spoon == (0.5, -0.25)
    assert look.progress == 0.25 and look.rate == 0.1 and look.stamp == 10.0


def testGarbageFromTheNetworkIsIgnored():
    look = State.decode({"items": "nope", "sunk": [9, "x", True, 1], "spoon": [5, None], "progress": float("nan"), "heated": 1,
                         "meal": {"newItemName": "arris:x", "count": -3}}, 1.0)
    assert look.items == [None] * 6 and look.sunk == frozenset([1]) and look.spoon == (1.0, 0.0)
    assert look.progress == 0.0 and look.heated is False and look.meal is None
    assert State.decode(None, 1.0).items == [None] * 6 and State.decode([1, 2], 1.0).heated is False


def testPartialPayloadsKeepTheRest():
    first = State.decode(_payload(), 10.0)
    second = State.decode({"stirring": True, "spoon": [0.0, 1.0]}, 12.0, first)
    assert second.items == first.items and second.dish == first.dish and second.heated
    assert second.stirring and second.spoon == (0.0, 1.0)
    assert second.progress == 0.25 and second.stamp == 10.0, "没带进度的载荷不动进度的时间戳"
    assert first.stirring is False, "旧的那份不被改"


def testFloatingSlotsLeaveOutSunkOnes():
    look = State.decode(_payload(), 0.0)
    assert State.presentOf(look) == [True, False, False, False, False, False], "牛奶桶是倒进去的，不漂"
    assert State.filledOf(look) == 2, "水位按非空的格数算，倒进去的也占一格"
    assert State.servingsOf(look) == 0 and State.servingsOf(State.decode(_payload(meal=_item("arris:tomato_sauce", 3)), 0.0)) == 3


def testArrivalsAndRemovalsBetweenTwoLooks():
    old = State.decode(_payload(), 0.0)
    new = State.decode(_payload(items=[{}, _item("minecraft:cod"), _item("minecraft:milk_bucket"), _item("arris:onion"), {}, {}]), 1.0)
    assert State.arrivedBetween(old, new) == [1, 3] and State.emptiedBetween(old, new) == [0]
    assert State.arrivedBetween(None, new) == [] and State.emptiedBetween(None, new) == [], "刚看到的锅：料本来就在里面"


def testProgressIsExtrapolatedBetweenUpdates():
    look = State.decode(_payload(), 10.0)
    assert abs(State.progressAt(look, 12.0) - 0.45) < 1.0e-9
    assert State.progressAt(look, 100.0) == 1.0 and State.progressAt(look, 5.0) == 0.25


def testFoodForTheColourFollowsJava():
    look = State.decode(_payload(served=_item("arris:tomato_sauce", 2)), 0.0)
    assert [item["newItemName"] for item in State.foodOf(look)] == ["arris:tomato", "minecraft:milk_bucket", "arris:tomato_sauce"]
    done = State.decode(_payload(meal=_item("arris:tomato_sauce", 3)), 0.0)
    assert [item["newItemName"] for item in State.foodOf(done)] == ["arris:tomato_sauce"], "有成品时只看成品"


def testTheStaticKeyChangesOnlyWithStaticParts():
    a = State.decode(_payload(), 0.0)
    b = State.decode(_payload(stirring=True, spoon=[0.1, 0.2], progress=0.9), 5.0)
    c = State.decode(_payload(heated=False), 0.0)
    assert a.staticKey() == b.staticKey() and a.staticKey() != c.staticKey()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
