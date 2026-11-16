# -*- coding: utf-8 -*-
# runner: both
"""炉灶"看上去是什么样"的状态（Shared/Rules/StoveLookState.py）：广播来的载荷逐项查类型、方块实体数据里存的那份（"0".."5" 六个烤位 + handGrill 手放的进度）
解成同一个样子、一次性事件的负载清洗。载荷来自网络，不对的当作没有。"""
from __future__ import print_function

import fdtest

State = fdtest.load("Shared.Rules.StoveLookState")


def item(name="minecraft:beef", count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def testABroadcastIsDecodedPlaceByPlace():
    look = State.decode({"slots": [{"item": item(), "hand": True, "down": 1.0, "up": 0.5}, {}, {"item": item("minecraft:cod"), "hand": False}]})
    assert look.items[0] == item() and look.hand[0] is True and look.down[0] == 1.0 and look.up[0] == 0.5
    assert look.items[1] is None and look.items[2]["newItemName"] == "minecraft:cod" and look.hand[2] is False
    assert look.items[3:] == [None] * 3 and look.data() == {"down": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0], "up": [0.5, 0.0, 0.0, 0.0, 0.0, 0.0],
                                                           "hand": [True, False, False, False, False, False]}
    assert look.getItem(("grill", 0)) == item() and look.getItem(("grill", 1)) is None and look.getItem(("grill", 9)) is None
    assert look.getItem(("grill", -1)) is None and look.getItem(None) is None and look.getItem(("grill", True)) is None


def testGarbageFromTheNetworkIsTreatedAsNothing():
    for bad in (None, 5, "x", [], {}, {"slots": None}, {"slots": "abc"}, {"slots": [1, None, "x", []]}):
        look = State.decode(bad)
        assert look.items == [None] * 6 and look.hand == [False] * 6, bad
    look = State.decode({"slots": [{"item": {"newItemName": "", "count": 1}}, {"item": {"newItemName": "a", "count": 0}},
                                   {"item": {"newItemName": "a", "count": True}}, {"item": {"newItemName": "a", "count": "2"}},
                                   {"item": item(), "hand": "yes", "down": "high", "up": float("nan")},
                                   {"item": item(), "hand": True, "down": 7, "up": -3}] + [{}] * 5})
    assert look.items[:4] == [None] * 4, "名字空、数量不对的不算物品"
    assert look.items[4] == item() and look.hand[4] is False and look.down[4] == 0.0 and look.up[4] == 0.0, "只有 True 才算手放的，坏数当 0"
    assert look.hand[5] is True and look.down[5] == 1.0 and look.up[5] == 0.0, "夹进 0..1"


def testWhatTheBlockEntitySavedIsTheSameLook():
    saved = {"byHand": [1, 0, 1, 0, 0, 0], "down": [1.0, 0.0, 0.3, 0.0, 0.0, 0.0], "up": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    look = State.fromBlockData({"0": {"itemDict": item(), "cookTimer": 30}, "1": {"itemDict": None, "cookTimer": 30}, "2": {"itemDict": item("minecraft:cod"), "cookTimer": 5},
                                "handGrill": saved})
    assert look.items[0] == item() and look.items[1] is None and look.items[2]["newItemName"] == "minecraft:cod"
    assert look.hand[:3] == [True, False, True] and look.down[0] == 1.0 and abs(look.down[2] - 0.28125) < 1e-9, "取 1/32 一档，和广播一样"
    plain = State.fromBlockData({"3": {"itemDict": item(), "cookTimer": 30}})
    assert plain.items[3] == item() and plain.hand[3] is False and plain.down[3] == 0.0, "没手放过：FD 原样的"


def testTheSavedDataMayBeMissingOrBroken():
    for bad in (None, 3, [], {}, {"handGrill": 7}, {"0": 5}, {"0": {"itemDict": item()}, "handGrill": {"byHand": "x", "down": [None], "up": 5}}):
        look = State.fromBlockData(bad)
        assert len(look.items) == 6 and all(value is False for value in look.hand), bad


def testAnEventPayloadIsCleaned():
    clean = State.eventData({"place": 2, "places": [0, 1, 9, -1, True, "x", 3], "stack": item(), "up": 1.5})
    assert clean == {"place": 2, "places": [0, 1, 3], "stack": item(), "up": 1.0}
    nothing = State.eventData(None)
    assert nothing == {"place": None, "places": [], "stack": None, "up": None}
    odd = State.eventData({"place": 6, "places": "all", "stack": {"newItemName": "x"}, "up": "no"})
    assert odd == {"place": None, "places": [], "stack": None, "up": None}
    assert State.eventData({"place": True})["place"] is None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
