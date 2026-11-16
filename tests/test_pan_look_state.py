# -*- coding: utf-8 -*-
# runner: both
"""一口煎锅看上去的状态（Shared/Rules/PanLookState.py）：解广播的载荷、两面熟度按速度外推并取成 1/32 一档、区块晚加载时按方块实体数据补。"""
from __future__ import print_function

import fdtest

Look = fdtest.load("Shared.Rules.PanLookState")
Frying = fdtest.load("Shared.Rules.HandsOn.Frying")


def item(name="minecraft:beef", count=2):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def near(a, b, eps=1e-9):
    return abs(a - b) < eps


def testADecodedPayloadHasEverythingTheSceneNeeds():
    look = Look.decode({"item": item(), "batch": 2, "byHand": True, "heated": True, "down": 0.25, "up": 0.0, "rate": 0.5, "both": False}, 10.0)
    assert look.item == item() and look.batch == 2 and look.byHand and look.heated and not look.both
    assert look.down == 0.25 and look.rate == 0.5 and look.stamp == 10.0


def testKeysMissingFromAPayloadKeepWhatWasThere():
    first = Look.decode({"item": item(), "byHand": True, "heated": True, "down": 0.5, "rate": 0.25}, 1.0)
    second = Look.decode({"heated": False}, 2.0, first)
    assert second.item == item() and second.byHand and not second.heated and second.down == 0.5 and second.stamp == 1.0


def testGarbageFromTheNetworkIsIgnored():
    look = Look.decode({"item": {"newItemName": "x", "count": "many"}, "down": "fast", "rate": float("nan"), "heated": "yes"}, 1.0)
    assert look.item is None and look.down == 0.0 and look.rate == 0.0 and not look.heated
    assert Look.decode("nope", 1.0).item is None and Look.decode(None, 1.0).item is None
    huge = Look.decode({"item": item(count=5), "batch": 10 ** 9, "down": 9.0, "rate": 1e9}, 1.0)
    assert huge.batch == 64 and huge.down == 1.0 and huge.rate == 10.0, "夹进范围"


def testAnEmptyPanHasNoProgress():
    look = Look.decode({"item": {}, "down": 0.7, "up": 0.3, "rate": 1.0}, 1.0)
    assert look.item is None and (look.down, look.up, look.rate) == (0.0, 0.0, 0.0)


def testTheDownSideAdvancesAtTheRateInThirtySecondsSteps():
    look = Look.decode({"item": item(), "byHand": True, "down": 0.0, "up": 0.0, "rate": 0.25}, 10.0)
    assert Look.progressAt(look, 10.0) == (0.0, 0.0)
    assert Look.progressAt(look, 12.0) == (0.5, 0.0), "两秒走了 0.5，朝上面不动"
    down, _ = Look.progressAt(look, 10.1)
    assert near(down, Frying.syncStep(0.025)) and down == 0.0, "0.025 还不够 1/32"
    down, _ = Look.progressAt(look, 10.4)
    assert near(down, 3.0 / 32.0), "走了 0.1 = 3.2 档，向下取成 3 档"
    assert Look.progressAt(look, 99.0) == (1.0, 0.0), "熟了就是 1，不再走"


def testAnEggCooksThroughSoBothSidesAdvanceTogether():
    look = Look.decode({"item": item("minecraft:egg", 1), "byHand": True, "down": 0.0, "up": 0.0, "rate": 0.125, "both": True}, 0.0)
    down, up = Look.progressAt(look, 4.0)
    assert down == up == 0.5


def testAWaitingPanDoesNotAdvance():
    look = Look.decode({"item": item(), "byHand": True, "down": 1.0, "up": 0.0, "rate": 0.0}, 0.0)
    assert Look.progressAt(look, 50.0) == (1.0, 0.0)


def testTheStaticKeyChangesWithWhatLiesInThePan():
    a = Look.decode({"item": item(count=2), "byHand": True, "heated": True}, 0.0)
    assert a.key() == Look.decode({"item": item(count=2), "byHand": True, "heated": True, "down": 0.3}, 1.0).key(), "熟度不算静态的"
    assert a.key() != Look.decode({"item": item(count=3), "byHand": True, "heated": True}, 0.0).key()
    assert a.key() != Look.decode({"item": item(count=2), "byHand": False, "heated": True}, 0.0).key()
    assert Look.Look().key() == (None, False, False)


def testALateLoadingClientBuildsTheLookFromTheBlockEntityData():
    data = {"cookingDict": item(count=3), "heatEnable": True, "panFrying": {"byHand": True, "down": 1.0, "up": 0.25, "batch": 3}}
    look = Look.fromBlockData(data)
    assert look.item == item(count=3) and look.heated and look.byHand and look.down == 1.0 and look.up == 0.25 and look.batch == 3
    assert look.rate == 0.0, "不知道走多快：等服务端下一条"
    bare = Look.fromBlockData({"cookingDict": item(), "heatEnable": False})
    assert bare.item is not None and not bare.byHand and not bare.heated and bare.down == 0.0, "/setblock 放的、旧存档：缺键当空"
    assert Look.fromBlockData({"panFrying": {"byHand": True, "down": 1.0}}).item is None, "锅是空的，存着的进度不算"
    assert Look.fromBlockData(None).item is None and Look.fromBlockData({"cookingDict": 7}).item is None


def testAnEventPayloadIsCleanedBeforeTheSceneSeesIt():
    clean = Look.eventData({"event": "taken", "stack": {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3, "evil": 1}, "strength": 7.0,
                            "in_pan": True, "pos": [1, 2, 3]})
    assert clean == {"stack": {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3}, "strength": 1.0, "in_pan": True, "to_cook": False}
    junk = Look.eventData({"stack": "beef", "strength": "hard", "in_pan": "yes"})
    assert junk == {"stack": None, "strength": 0.5, "in_pan": False, "to_cook": False}
    assert Look.eventData(None)["stack"] is None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
