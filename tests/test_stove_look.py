# -*- coding: utf-8 -*-
# runner: both
"""炉灶的世界外观广播（Server/StoveLook.py，经 Server/Stove.py 的每一步和 Compat/Diegesis/GrillLogic.py 的动作发出）：
HoD 的炉灶场景是 idle_visible，32 格内的人不管开没开站点都看得到烤架上的东西、冒烟等翻、翻面落下取走、烤好的汽和闪。
样子变了才发（东西、手放的、贴灶面熟没熟、朝上面在哪一档），走进 32 格的人单发一份当前的，一次性的事件发给附近所有人。"""
from __future__ import print_function

import stovekit as K
from stovekit import BEEF, STICK, fake

COOKED = "minecraft:cooked_beef"


def beef(count=1):
    return {"newItemName": BEEF, "newAuxValue": 0, "count": count}


def lay(manager, count=2):
    fake.give("a", 3, BEEF, count)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("place"))


def testNothingIsSentWithoutThePrerequisiteSwitch():
    manager, data = K.setup()
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
    """贴灶那面一点点烤熟（每 1/32 变一档）不用发：画面只看熟没熟；熟了（等翻）才发一次。"""
    manager, data = K.setup(look=True)
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
    manager, data = K.setup(look=True)
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


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
