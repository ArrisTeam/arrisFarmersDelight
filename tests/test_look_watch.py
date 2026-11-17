# -*- coding: utf-8 -*-
# runner: both
"""世界外观广播的收件人（Server/Helpers/LookWatch.Audience）：谁已经收到这口锅 / 这座灶当前的样子。

广播发出去就不管有没有收到：客户端脚本还没就绪、区块还没加载好的时候整份丢掉，服务端却当他收到了，等翻面、烤好留在灶上这些状态又不再变，
丢了就永远补不上（实机：进世界时灶上本来就有东西，走到灶边客户端的场景一直不知道样子）。所以名单还记着每个人是什么时候收到的，
隔 refresh 秒再单发一份当前的样子；客户端收到同样的样子是幂等的。不给 refresh 就是原来的样子：只有新走进来的人才单发。"""
from __future__ import print_function

import potfake

potfake.install()
LookWatch = potfake.load("Server.Helpers.LookWatch")


def testWithoutARefreshOnlyNewcomersAreSentAndTheListFollowsTheRange():
    audience = LookWatch.Audience()
    assert audience.arrivals(["a", "b"]) == ["a", "b"], "第一次：都是新来的"
    assert audience.arrivals(["a", "b"]) == [] and audience.arrivals(["a", "b"], 1000.0) == [], "给了时钟也一样：没有 refresh 不重发"
    assert audience.arrivals(["a"]) == [] and audience.arrivals(["a", "b"]) == ["b"], "b 走出去划掉，回来时又算新来的"
    audience.sent(["a", "c"])
    assert audience.arrivals(["a", "b", "c"]) == ["b"], "刚发给了 a 和 c"


def testWithARefreshAPlayerGetsTheLookAgainOnceItIsOldEnough():
    audience = LookWatch.Audience(5.0)
    audience.sent(["a", "b"], 100.0)
    assert audience.arrivals(["a", "b"], 104.9) == [], "还没到"
    assert audience.arrivals(["a", "b"], 105.0) == ["a", "b"], "隔了 5 秒：再发一份（可能丢了）"
    assert audience.arrivals(["a", "b"], 109.9) == [] and audience.arrivals(["a", "b"], 110.0) == ["a", "b"], "之后每 5 秒一次"


def testEachPlayerIsOnHisOwnClock():
    audience = LookWatch.Audience(5.0)
    audience.sent(["a"], 100.0)
    assert audience.arrivals(["a", "b"], 103.0) == ["b"], "b 是 3 秒时才走进来的：马上单发，a 还没到"
    assert audience.arrivals(["a", "b"], 105.0) == ["a"], "a 的 5 秒到了，b 的还没"
    assert audience.arrivals(["a", "b"], 108.0) == ["b"], "b 是从自己收到那一刻起算的"


def testASendWithoutAClockIsDueAsSoonAsAClockIsGiven():
    """旧调用没给时钟（sent(near) 不记时刻）：之后给了时钟就当成该再发一份。"""
    audience = LookWatch.Audience(5.0)
    audience.sent(["a"])
    assert audience.arrivals(["a"]) == [], "还是没给时钟：不重发"
    assert audience.arrivals(["a"], 100.0) == ["a"]


def testAClockThatGoesBackwardsCountsAsDue():
    """换了世界、测试里的假时钟倒着走：不能因为差是负的就永远等下去。"""
    audience = LookWatch.Audience(5.0)
    audience.sent(["a"], 500.0)
    assert audience.arrivals(["a"], 10.0) == ["a"]


def testThoseWhoLeftAreForgottenAndComeBackAsNewcomersWhateverTheClock():
    audience = LookWatch.Audience(5.0)
    audience.sent(["a", "b"], 100.0)
    assert audience.arrivals(["a"], 101.0) == [] and "b" not in audience.known
    assert audience.arrivals(["a", "b"], 102.0) == ["b"], "回来的算新来的，不用等 5 秒"


def testWithAMostTheGapDoublesAfterEachRefreshUpToIt():
    """丢是进世界那一阵的事：几秒内补上就行，站久了的人不用一直每 5 秒收一份。间隔 5、10、20、40、60、60……"""
    audience = LookWatch.Audience(5.0, 60.0)
    audience.sent(["a"], 0.0)
    sentAt = [now for now in range(1, 400) if audience.arrivals(["a"], float(now)) == ["a"]]
    assert sentAt == [5, 15, 35, 75, 135, 195, 255, 315, 375], sentAt


def testAChangedLookAndAPlayerWhoCameBackStartTheGapOver():
    audience = LookWatch.Audience(5.0, 60.0)
    audience.sent(["a"], 0.0)
    assert audience.arrivals(["a"], 5.0) == ["a"] and audience.arrivals(["a"], 14.0) == [], "补过一次：下一份隔 10 秒"
    audience.sent(["a"], 14.0)                                      # 样子变了，发给了所有人
    assert audience.arrivals(["a"], 18.9) == [] and audience.arrivals(["a"], 19.0) == ["a"], "从头算：5 秒"
    assert audience.arrivals([], 20.0) == [] and audience.arrivals(["a"], 21.0) == ["a"], "走出去再回来：算新来的"
    assert audience.arrivals(["a"], 25.9) == [] and audience.arrivals(["a"], 26.0) == ["a"], "新来的也从 5 秒起"


def testAMostShorterThanTheRefreshNeverShortensTheGap():
    audience = LookWatch.Audience(5.0, 1.0)
    audience.sent(["a"], 0.0)
    assert [now for now in range(1, 21) if audience.arrivals(["a"], float(now)) == ["a"]] == [5, 10, 15, 20]


def testAFirstTimedSendAfterAnUntimedOneDoesNotDoubleYet():
    audience = LookWatch.Audience(5.0, 60.0)
    audience.sent(["a"])
    assert audience.arrivals(["a"], 100.0) == ["a"]
    assert audience.arrivals(["a"], 104.9) == [] and audience.arrivals(["a"], 105.0) == ["a"], "这才是第一份带时刻的：下一份还是隔 5 秒"
    assert audience.arrivals(["a"], 114.9) == [] and audience.arrivals(["a"], 115.0) == ["a"], "再往后才加倍"


def testTheProductionDefaultIsAFewSeconds():
    """丢了的最多这么久补上；一份几百字节，附近每人每隔这么久一份。炉灶 / 煎锅的广播用它（test_stove_look / test_pan_station_logic 里测）。"""
    assert 1.0 <= LookWatch.REFRESH_SECONDS <= 30.0
    assert LookWatch.REFRESH_SECONDS < LookWatch.REFRESH_MOST <= 120.0


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
