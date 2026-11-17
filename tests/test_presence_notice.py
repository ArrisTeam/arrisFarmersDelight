# -*- coding: utf-8 -*-
# runner: both
"""前置包太旧（接口比本包要的老）时客户端提醒玩家更新：本地玩家进了世界才提醒、左上角、str 不是 unicode、共三次每次隔 8 秒；
没装前置包（STANDALONE）、联动了（LINKED）、还没判定时什么也不提醒。真的 ClientBoot，引擎是 linkkit 里的假环境。只用本仓库的东西。"""
from __future__ import print_function

import fdtest
import linkkit as L

env = L.install()
Mode = L.Mode


def bootClient(api):
    env.reset()
    env.apis["client"] = api
    env.boot("client")
    env.fire("client")


def playerLoaded():
    """本地玩家进了世界（OnLocalPlayerStopLoading）：挂在这个事件上的函数都调一遍。"""
    for event, func in list(env.listened["client"]):
        if event == "OnLocalPlayerStopLoading":
            func({"playerId": "player"})


def runTimers():
    """把已经排好的计时器按顺序触发（每个触发时可能又排新的）；返回每个计时器等了几秒。"""
    waited = []
    while env.timers:
        seconds, func, args = env.timers.pop(0)
        waited.append(seconds)
        func(*args)
    return waited


def apiOf(version):
    return type("Api", (object,), {"API_VERSION": version})


def testAnOutdatedPrerequisiteIsReportedWhenThePlayerHasLoadedThreeTimesEightSecondsApart():
    bootClient(apiOf(2))
    assert Mode.mode("client") == Mode.OUTDATED
    assert env.notices == [] and env.timers == [], "进世界之前不提醒"
    playerLoaded()
    assert len(env.notices) == 1, "进了世界马上提醒一次"
    assert [seconds for seconds, _, _ in env.timers] == [8.0], "隔 8 秒再提醒"
    waited = runTimers()
    assert waited == [8.0, 8.0] and len(env.notices) == 3, "共三次、每次隔 8 秒"
    assert env.timers == [], "第三次之后不再排"


def testTheNoticeIsAStrWithTheCornerTextSayingWhatToDo():
    bootClient(apiOf(1))
    playerLoaded()
    text = env.notices[0]
    assert type(text) is str, "引擎的文本接口只收 str，unicode 会静默失败：%r" % (type(text),)
    for word in ("农夫乐事", "场景交互", "前置", "更新", "站点"):
        assert word in text, word


def testNothingIsReportedWithoutThePrerequisiteWithAGoodOneOrBeforeTheDecision():
    bootClient(None)
    playerLoaded()
    assert Mode.mode("client") == Mode.STANDALONE and env.notices == [] and env.timers == [], "没装前置包：不打扰玩家"
    bootClient(apiOf(3))
    playerLoaded()
    assert env.notices == [] and env.timers == [], "版本够：不提醒"
    env.reset()
    env.apis["client"] = apiOf(2)
    env.boot("client")                                   # 事件还没来：还没判定
    playerLoaded()
    assert Mode.mode("client") == Mode.PENDING and env.notices == [] and env.timers == []


def testAServerOnlyOutdatedPrerequisiteReportsNothingBecauseTheNoticeIsTheClientsJob():
    env.reset()
    env.apis["server"] = apiOf(2)
    env.boot("server")
    assert Mode.mode("server") == Mode.OUTDATED and env.notices == [] and env.timers == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
