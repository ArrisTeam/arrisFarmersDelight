# -*- coding: utf-8 -*-
# runner: both
"""炉灶的世界外观广播（Server/StoveLook.py，经 Server/Stove.py 的每一步和 Compat/Diegesis/GrillLogic.py 的动作发出）：
HoD 的炉灶场景是 idle_visible，32 格内的人不管开没开站点都看得到烤架上的东西、冒烟等翻、翻面落下取走、烤好的汽和闪。
样子变了才发（东西、手放的、贴灶面熟没熟、朝上面在哪一档），走进 32 格的人单发一份当前的，一次性的事件发给附近所有人。"""
from __future__ import print_function

import stovekit as K
from stovekit import BEEF, STICK, fake

COOKED = "minecraft:cooked_beef"
PAUSE = K.LookWatch.REFUSED_GAP + 0.05          # 隔够了（浮点的边界上不比）


def beef(count=1):
    return {"newItemName": BEEF, "newAuxValue": 0, "count": count}


def lay(manager, count=2):
    fake.give("a", 3, BEEF, count)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("place"))


def testNothingIsSentWithoutThePrerequisiteSwitch():
    manager, data = K.setup(look=False)
    lay(manager)
    K.step(1.0, manager=manager)
    assert not [call for call in fake.calls if call[1] == K.StoveLook.ENDPOINT]


def testTheLookIsBroadcastAsSoonAsAnActionChangesIt():
    manager, data = K.setup(look=True)
    lay(manager, 2)
    payload, players = K.looks()[-1]
    assert sorted(players) == ["a", "b"] and payload["dimensionId"] == 0 and payload["pos"] == list(K.STOVE)
    slots = payload["slots"]
    assert len(slots) == 6 and slots[0]["item"] == {"newItemName": BEEF, "newAuxValue": 0, "count": 1} and slots[1]["item"]["newItemName"] == BEEF
    assert slots[0]["hand"] is True and slots[0]["down"] == 0.0 and slots[0]["up"] == 0.0
    assert slots[2:] == [{}, {}, {}, {}], "没东西的烤位是空表"


def testItIsOnlySentWhenWhatTheEyeSeesChanges():
    """贴灶那面一点点烤熟（每 1/32 变一档）不用发：画面只看熟没熟；熟了（等翻）才发一次。（定期补发另算，在下面单独测，这里关掉。）"""
    manager, data = K.setup(look=True, refresh=None)
    lay(manager, 1)
    manager.close("a")
    sent = len(K.looks())
    K.step(8.0)
    assert len(K.looks()) == sent, "还在烤：画面没变，不发"
    K.step(3.0)
    assert len(K.looks()) == sent + 1, "贴灶面熟了：开始冒烟等翻"
    latest = K.looks()[-1][0]["slots"][0]
    assert latest["down"] == 1.0 and latest["up"] == 0.0 and latest["hand"] is True
    K.step(5.0)
    assert len(K.looks()) == sent + 1


def testTurningTellsEveryoneAndTheTopLooksDone():
    manager, data = K.setup(look=True)
    lay(manager, 1)
    K.step(11.0, manager=manager)
    mark = len(K.broadcasts("turned"))
    assert K.do(manager, "a", K.custom("turn", place=0))
    turned = K.broadcasts("turned")[mark:]
    assert len(turned) == 1 and turned[0][1]["place"] == 0 and turned[0][1]["up"] == 1.0 and sorted(turned[0][2]) == ["a", "b"]
    assert K.looks()[-1][0]["slots"][0]["up"] == 1.0 and K.looks()[-1][0]["slots"][0]["down"] == 0.0, "翻过来：熟的那面朝上，下面开始烤"
    assert K.do(manager, "a", K.custom("turn", place=0)) and len(K.broadcasts("unturned")) == 1, "离上次翻太近：没接，也告诉大家"


def testABatchDoneOnBothSidesMakesAGrilledEventEvenWithNobodyAtTheStation():
    manager, data = K.setup(look=True)
    lay(manager, 1)
    K.step(11.0, manager=manager)
    K.do(manager, "a", K.custom("turn", place=0))
    manager.close("a")
    K.step(11.0)
    grilled = K.broadcasts("grilled")
    assert len(grilled) == 1 and grilled[0][1]["place"] == 0 and grilled[0][1]["stack"]["newItemName"] == COOKED
    assert sorted(grilled[0][2]) == ["a", "b"] and K.names(data)[0] == COOKED
    assert K.looks()[-1][0]["slots"][0]["item"]["newItemName"] == COOKED, "成品留在烤架上"
    K.step(5.0)
    assert len(K.broadcasts("grilled")) == 1, "只报一回"


def testPlacingTakingAndBeingRefusedAreEventsForEveryone():
    manager, data = K.setup(look=True)
    lay(manager, 2)
    placed = K.broadcasts("placed")
    assert len(placed) == 1 and placed[0][1]["places"] == [0, 1] and sorted(placed[0][2]) == ["a", "b"]
    assert K.do(manager, "a", K.custom("take", place=1))
    taken = K.broadcasts("taken")
    assert len(taken) == 1 and taken[0][1]["place"] == 1 and taken[0][1]["stack"]["newItemName"] == BEEF
    fake.give("a", 4, STICK, 3)
    assert K.do(manager, "a", K.click(K.inv(4)))
    assert K.do(manager, "a", K.custom("place"))
    refused = K.broadcasts("refused")
    assert len(refused) == 1 and refused[0][1]["stack"] == {"newItemName": STICK, "newAuxValue": 0, "count": 1}


def _refuseSticks(manager, playerId, times, gap=0.07):
    """playerId 手上拿着木棍，一连点 times 下 place（炉灶不收木棍：每下都被拒），每下隔 gap 秒（假世界的钟）。"""
    for _ in range(times):
        fake.world.time += gap
        assert K.do(manager, playerId, K.custom("place"))


def _holdSticks(manager, playerId):
    fake.give(playerId, 4, STICK, 3)
    K.opened(manager, playerId)
    assert K.do(manager, playerId, K.click(K.inv(4)))


def testARefusedPlacementIsNotAHornTheCooksOwnClientCanBlowAtEveryoneNearby():
    """被拒的动作每秒能来 40 个：改过的客户端发一串非法的 place，每个都给 32 格内每个旁观的人广播一次、放一声敲击。同一个人被拒的敲击声，旁观的人 0.3 秒内至多听一声；
    站点里的人一个不少（他的客户端据此演被拒的东西弹开，连点几下弹几下）。"""
    manager, data = K.setup(look=True)
    fake.addPlayer("c", (11.5, 64.0, 8.5))                             # 旁观的人：32 格内，没开站点
    _holdSticks(manager, "a")
    before = len(K.broadcasts("refused"))
    _refuseSticks(manager, "a", 20)                                    # 20 个，每个隔 0.07 秒（一秒多一点）
    refused = K.broadcasts("refused")[before:]
    assert len(refused) == 20 and all("a" in players for _name, _payload, players in refused), "站点里的人 20 个都收到"
    assert sum(1 for _name, _payload, players in refused if "c" in players) == 4, "旁观的人只听到第 1、6、11、16 个（每隔 0.35 秒）"
    _refuseSticks(manager, "a", 1, gap=PAUSE)
    assert "c" in K.broadcasts("refused")[-1][2], "隔够了又能听到"


def testTheRefusalLimitIsPerPlayerAndLeavesPlacingAlone():
    manager, data = K.setup(look=True)
    fake.addPlayer("c", (11.5, 64.0, 8.5))
    _holdSticks(manager, "a")
    _holdSticks(manager, "b")
    before = len(K.broadcasts("refused"))
    for _ in range(3):                                                 # 两个人各发三个非法的 place，同一时刻
        for playerId in ("a", "b"):
            assert K.do(manager, playerId, K.custom("place"))
    refused = K.broadcasts("refused")[before:]
    assert len(refused) == 6 and sum(1 for _n, _p, players in refused if "c" in players) == 2, "旁观的人一个人一声，不是两个人共用一声"
    assert all("a" in players and "b" in players for _n, _p, players in refused), "站点里的两个人每个都收到"
    assert K.do(manager, "a", K.click(K.inv(4)))                       # 木棍放回背包，换成牛肉放上去：刚被拒完（0.3 秒内），合法的动作照样人人收到
    fake.give("a", 5, BEEF, 2)
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert K.do(manager, "a", K.custom("place"))
    placed = K.broadcasts("placed")
    assert len(placed) == 1 and "c" in placed[0][2], "放上去不受限"


def testAFarmersDelightPieceShowsUpWithNobodyAtAStation():
    manager, data = K.setup(look=True)
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    K.step(0.5)
    slot = K.looks()[-1][0]["slots"][3]
    assert slot["item"]["newItemName"] == BEEF and slot["hand"] is False and slot["down"] == 0.0, "FD 原样烤的：不是手放的，两面进度没有"


def testAPieceStaysAfterTheStationClosesAndKeepsBeingToldAbout():
    manager, data = K.setup(look=True)
    lay(manager, 3)
    manager.close("a")
    K.step(11.0)
    latest = K.looks()[-1][0]["slots"]
    assert [slot["down"] for slot in latest[:3]] == [1.0, 1.0, 1.0] and all(slot["hand"] for slot in latest[:3]), "关了站点：等翻的照样在"


def testOnlyPlayersWithin32BlocksGetItAndANewcomerGetsTheCurrentLookOnce():
    manager, data = K.setup(look=True, refresh=None)
    fake.addPlayer("far", (10.5, 64.0, 80.5))
    lay(manager, 1)
    for payload, players in K.looks() + [(p, q) for p, q in K._grouped() if p.get("event")]:
        assert "far" not in players
    before = len(K.looks())
    fake.world.players["far"]["pos"] = (10.5, 64.0, 20.5)
    K.tick(fake.world.time + 2.0)
    arrivals = [(payload, players) for payload, players in K.looks() if "far" in players]
    assert len(K.looks()) == before + 1 and arrivals[0][1] == ["far"], "单发给他，a 和 b 不重复收"
    assert arrivals[0][0]["slots"][0]["item"]["newItemName"] == BEEF
    K.tick(fake.world.time + 3.0)
    assert len(K.looks()) == before + 1, "他已经有了"
    fake.world.players["far"]["pos"] = (10.5, 64.0, 90.5)
    K.tick(fake.world.time + 4.0)
    K.do(manager, "a", K.custom("take", place=0))
    fake.world.players["far"]["pos"] = (10.5, 64.0, 20.5)
    K.tick(fake.world.time + 6.0)
    assert K.looks()[-1][1] == ["far"] and K.looks()[-1][0]["slots"][0] == {}, "走远又回来：补到的是现在的样子"


def testNothingIsBuiltWhileNobodyIsInRangeAndTheFirstToComeBackGetsTheCurrentLook():
    """范围里没人：样子不用算（每座灶每 0.25 秒一次，不能白算），也不发；人回来了单发一份。"""
    manager, data = K.setup(look=True)
    for playerId in ("a", "b"):
        fake.world.players[playerId]["pos"] = (10.5, 64.0, 200.5)
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    built, original = [], K.StoveLook.build
    K.StoveLook.build = lambda *args: built.append(args) or original(*args)
    try:
        K.step(1.0)
    finally:
        K.StoveLook.build = original
    assert built == [] and not K.looks(), "没人在 32 格内：不算也不发"
    fake.world.players["a"]["pos"] = (10.5, 64.0, 8.5)
    K.step(1.0)
    assert [players for _, players in K.looks()] == [["a"]] and K.looks()[-1][0]["slots"][3]["item"]["newItemName"] == BEEF


def testAStoveWithAPotOnTopThrowsItsFoodOffAndEveryoneSeesItEmpty():
    manager, data = K.setup(look=True)
    lay(manager, 2)
    manager.close("a")
    fake.world.blocks[(0, (K.STOVE[0], K.STOVE[1] + 1, K.STOVE[2]))] = "arris:cooking_pot"
    K.step(0.6)
    assert K.names(data) == [None] * 6 and fake.spawned
    assert K.looks()[-1][0]["slots"] == [{}] * 6


def testTheForgottenStoveIsNotRemembered():
    manager, data = K.setup(look=True)
    lay(manager, 1)
    assert (0, K.STOVE) in K.StoveLook._sent
    K.StoveLook.forget(0, K.STOVE)
    assert (0, K.STOVE) not in K.StoveLook._sent


# ---------------------------------------------------------------- 丢了的补上

def testALookTheClientNeverGotIsSentAgainEveryRefreshSecondsEvenThoughNothingChanged():
    """进世界时服务端发的第一份，客户端脚本还没就绪、区块还没加载好，整份丢了；服务端当他收到了，样子又不变，原来就永远补不上
    （实机：灶上本来就有 6 个肉饼，走到灶边客户端的场景一直不知道样子）。现在样子没变时每隔 REFRESH_SECONDS 秒再单发一份。"""
    manager, data = K.setup(look=True)
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    K.step(0.5)
    first = K.looks()
    assert len(first) == 1 and sorted(first[0][1]) == ["a", "b"]
    del fake.calls[:]                                           # 客户端没收到：服务端不知道
    K.step(4.0)
    assert K.looks() == [], "还没到 5 秒"
    K.step(2.0)
    again = K.looks()
    assert len(again) == 1 and sorted(again[0][1]) == ["a", "b"] and again[0][0]["slots"] == first[0][0]["slots"], "隔了 5 秒又发了一份同样的"
    del fake.calls[:]
    K.step(5.5)
    assert K.looks() == [], "补过一次：下一份要隔 10 秒（间隔逐次加倍，站久了的人不用一直每 5 秒收一份）"
    K.step(5.0)
    assert len(K.looks()) == 1, "隔够 10 秒：第二份"


def testStandingByAStoveForTwoMinutesCostsAHandfulOfLooksNotOneEveryFiveSeconds():
    """补发不能没有上限：灶多人多的时候每座灶每人每 5 秒一份会一直发下去。间隔加倍之后两分钟里是开头那一份加 5、15、35、75 秒的四份。"""
    manager, data = K.setup(look=True)                              # 空烤架：样子两分钟都不变
    K.step(120.0)
    looks = K.looks()
    assert len(looks) == 5 and all(sorted(players) == ["a", "b"] for _payload, players in looks), [players for _payload, players in looks]


def testTheRefreshIsOnlyForThosePlayersInRange():
    manager, data = K.setup(look=True)
    fake.addPlayer("far", (10.5, 64.0, 80.5))
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    K.step(12.0)
    assert all("far" not in players for _, players in K.looks()), "32 格外的人什么也收不到，补发也不给"


def testAnEmptyLitStoveIsRefreshedToo():
    """空烤架也有样子（热浪每秒 1.6 个，场景知道了才冒）：补发不看有没有东西。"""
    manager, data = K.setup(look=True)
    K.step(0.5)
    del fake.calls[:]
    K.step(6.0)
    assert len(K.looks()) == 1 and K.looks()[0][0]["slots"] == [{}] * 6


def testOpeningTheStationSendsTheOpenerTheCurrentLookAtOnce():
    """开站要用当前的样子摆命中盒、认哪几个烤位有东西：开站那一刻单发给开站的人一份（他的客户端先前可能丢了），别人不重复收。"""
    manager, data = K.setup(look=True, refresh=None)
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    K.step(0.5)                                                 # a 和 b 都已经收到了
    del fake.calls[:]
    K.opened(manager)                                           # a 开站
    looks = K.looks()
    assert len(looks) == 1 and looks[0][1] == ["a"] and looks[0][0]["slots"][3]["item"]["newItemName"] == BEEF, "只单发给开站的人"


def testNothingIsResentOnOpenWithoutThePrerequisiteSwitch():
    manager, data = K.setup(look=False)
    K.opened(manager)
    K.step(8.0)
    assert not [call for call in fake.calls if call[1] == K.StoveLook.ENDPOINT]


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
