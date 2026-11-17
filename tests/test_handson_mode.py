# -*- coding: utf-8 -*-
# runner: both
"""联动状态（Shared/Rules/HandsOnMode）：每端一个运行模式，判定之前一律没联动；linked() 问的是这个进程；whenDecided 判定好了才调、
已经判定了马上调、之后模式变了再调一次。判定在 Compat/Diegesis/Presence，这里只管状态本身。只用本仓库的东西。"""
from __future__ import print_function

import linkkit as L
import fdtest

Mode = L.Mode
PENDING, LINKED, OUTDATED, STANDALONE = Mode.PENDING, Mode.LINKED, Mode.OUTDATED, Mode.STANDALONE


def _fresh():
    L.unlink()


def testEverySideStartsPendingAndNothingIsLinkedBeforeTheDecision():
    _fresh()
    assert Mode.mode("server") == PENDING and Mode.mode("client") == PENDING
    assert Mode.linked() is False, "判定之前一律当没联动"
    assert (PENDING, LINKED, OUTDATED, STANDALONE) == ("pending", "linked", "outdated", "standalone")
    assert Mode.SIDES == ("server", "client")


def testEachSideIsDecidedOnItsOwn():
    _fresh()
    Mode.decide("server", LINKED)
    assert (Mode.mode("server"), Mode.mode("client")) == (LINKED, PENDING)
    Mode.decide("client", OUTDATED)
    assert (Mode.mode("server"), Mode.mode("client")) == (LINKED, OUTDATED)
    Mode.decide("server", STANDALONE)
    assert (Mode.mode("server"), Mode.mode("client")) == (STANDALONE, OUTDATED)


def testLinkedIsTrueWhenEitherSideOfThisProcessIsLinkedAndOnlyThen():
    # 服务端的代码和 Shared 的规则不知道自己在哪一端：一个进程只联动它跑的那一端，所以任何一端联动了就是联动了
    for server in (PENDING, OUTDATED, STANDALONE):
        for client in (PENDING, OUTDATED, STANDALONE):
            with L.Modes(server=server, client=client):
                assert Mode.linked() is False, (server, client)
    with L.Modes(server=LINKED):
        assert Mode.linked() is True, "只有服务端的进程（专用服务器）"
    with L.Modes(client=LINKED):
        assert Mode.linked() is True, "只有客户端的进程（联机的客户端）"
    with L.Modes(LINKED):
        assert Mode.linked() is True, "单机：两端同进程"
    with L.Modes(server=LINKED, client=OUTDATED):
        assert Mode.linked() is True
    assert Mode.linked() is False, "with 块出来放回原样"


def testAnUnknownModeIsRefusedAndTheStateIsUntouched():
    _fresh()
    for bad in ("Linked", "ready", None, 1, ""):
        try:
            Mode.decide("server", bad)
        except ValueError:
            pass
        else:
            raise AssertionError("不认识的模式要报错：%r" % (bad,))
    assert Mode.mode("server") == PENDING
    try:
        Mode.mode("both")
    except KeyError:
        pass
    else:
        raise AssertionError("只有 server / client 两端")


def testWhenDecidedWaitsForTheDecision():
    _fresh()
    seen = []
    Mode.whenDecided("server", seen.append)
    assert seen == [], "还没判定：不调"
    Mode.decide("client", LINKED)
    assert seen == [], "别的端判定了不算"
    Mode.decide("server", STANDALONE)
    assert seen == [STANDALONE], "判定出结果马上调一次，带着模式"
    Mode.decide("server", STANDALONE)
    assert seen == [STANDALONE], "模式没变不再调"


def testWhenDecidedCallsAtOnceWhenTheSideIsAlreadyDecided():
    _fresh()
    Mode.decide("client", OUTDATED)
    seen = []
    Mode.whenDecided("client", seen.append)
    assert seen == [OUTDATED]
    Mode.whenDecided("client", lambda mode: seen.append("second:" + mode))
    assert seen == [OUTDATED, "second:outdated"], "每个回调各调一次"


def testAChangeAfterTheDecisionCallsEveryCallbackAgainWithTheNewMode():
    # 先判了 STANDALONE，后来找到了前置包（开发时热重载）：回调带着新模式再调一次，所以它们要能重复执行
    _fresh()
    first, second = [], []
    Mode.whenDecided("server", first.append)
    Mode.decide("server", STANDALONE)
    Mode.whenDecided("server", second.append)
    assert first == [STANDALONE] and second == [STANDALONE]
    Mode.decide("server", LINKED)
    assert first == [STANDALONE, LINKED] and second == [STANDALONE, LINKED]
    Mode.decide("server", PENDING)
    assert first == [STANDALONE, LINKED] and second == [STANDALONE, LINKED], "回到还没判定不算判定"
    Mode.decide("server", LINKED)
    assert first[-1] == LINKED and len(first) == 3, "再判定出来又调"


def testCallbacksAreKeptPerSide():
    _fresh()
    server, client = [], []
    Mode.whenDecided("server", server.append)
    Mode.whenDecided("client", client.append)
    Mode.decide("client", LINKED)
    assert server == [] and client == [LINKED]


def testACallbackThatRaisesDoesNotStopTheOthersNorTheDecision():
    _fresh()
    seen = []

    def broken(mode):
        raise RuntimeError("回调出错")
    Mode.whenDecided("server", broken)
    Mode.whenDecided("server", seen.append)
    Mode.decide("server", LINKED)      # 回调出错只打印 traceback
    assert seen == [LINKED] and Mode.mode("server") == LINKED
    Mode.whenDecided("server", broken)  # 已经判定了、登记时就调也一样
    assert Mode.linked() is True


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
