# -*- coding: utf-8 -*-
# runner: both
"""服务端事件注册表（Server/EventRegistry.py）：匹配、优先级、短路、异常隔离、热重载去重。"""
from __future__ import print_function

import fdtest

Registry = fdtest.load("Server.EventRegistry")


def _fresh():
    Registry.clearAll()
    return []


def testOrderByPriorityThenRegistration():
    calls = _fresh()

    @Registry.registerHandler("E", priority=10)
    def b(args):
        calls.append("b")

    @Registry.registerHandler("E", priority=50)
    def a(args):
        calls.append("a")

    @Registry.registerHandler("E", priority=10)
    def c(args):
        calls.append("c")

    assert Registry.dispatch("E", {}) is False
    assert calls == ["a", "b", "c"]


def testMatchKinds():
    calls = _fresh()
    liveList = ["arris:stove"]

    @Registry.registerHandler("Use", match="arris:skillet")
    def single(args):
        calls.append("single")

    @Registry.registerHandler("Use", match=("arris:pie_a", "arris:pie_b"))
    def fixed(args):
        calls.append("fixed")

    @Registry.registerHandler("Use", match=liveList)
    def live(args):
        calls.append("live")

    @Registry.registerHandler("Use", match=lambda key: key.endswith("_crop"))
    def predicate(args):
        calls.append("predicate")

    Registry.dispatch("Use", {}, "arris:skillet")
    Registry.dispatch("Use", {}, "arris:pie_b")
    Registry.dispatch("Use", {}, "test:end_stove")
    liveList.append("test:end_stove")  # 下游往活容器里追加后立即生效
    Registry.dispatch("Use", {}, "test:end_stove")
    Registry.dispatch("Use", {}, "arris:rice_crop")
    Registry.dispatch("Use", {}, "minecraft:stone")
    assert calls == ["single", "fixed", "live", "predicate"], calls


def testKeyOfReadsFromArgs():
    calls = _fresh()

    @Registry.registerHandler("ItemUseOn", match="arris:rice", keyOf=lambda args: args["itemDict"]["newItemName"])
    def rice(args):
        calls.append(args["blockName"])

    Registry.dispatch("ItemUseOn", {"blockName": "minecraft:dirt", "itemDict": {"newItemName": "arris:rice"}}, "minecraft:dirt")
    Registry.dispatch("ItemUseOn", {"blockName": "minecraft:dirt", "itemDict": {"newItemName": "minecraft:stick"}}, "minecraft:dirt")
    assert calls == ["minecraft:dirt"]


def testReturningTrueStopsLaterHandlers():
    calls = _fresh()

    @Registry.registerHandler("E", priority=2)
    def first(args):
        calls.append("first")
        return True

    @Registry.registerHandler("E", priority=1)
    def second(args):
        calls.append("second")

    assert Registry.dispatch("E", {}) is True
    assert calls == ["first"]


def testExceptionIsIsolated():
    calls = _fresh()

    @Registry.registerHandler("E", priority=2)
    def broken(args):
        raise ValueError("boom")

    @Registry.registerHandler("E", priority=1)
    def healthy(args):
        calls.append("healthy")

    assert Registry.dispatch("E", {}) is False
    assert calls == ["healthy"]


def testReRegistrationReplacesInsteadOfDuplicating():
    calls = _fresh()

    def handler(args):
        calls.append("old")

    Registry.registerHandler("E")(handler)

    def handler(args):  # noqa: F811 - 模拟热重载后同名函数重新登记
        calls.append("new")

    Registry.registerHandler("E")(handler)
    Registry.dispatch("E", {})
    assert calls == ["new"]
    assert len(Registry.handlerNames("E")) == 1


def testUnknownEventAndBadMatch():
    _fresh()
    assert Registry.dispatch("Nothing", {}) is False
    assert Registry.hasHandlers("Nothing") is False
    try:
        Registry.registerHandler("E", match=42)
    except TypeError:
        pass
    else:
        raise AssertionError("不认识的 match 类型应当在登记时报错")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
