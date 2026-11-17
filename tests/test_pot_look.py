# -*- coding: utf-8 -*-
# runner: both
"""厨锅的世界外观广播（Server/PotLook.py）：默认不发、32 格内同维度的玩家才收、静态部分镜像进方块实体数据、搅拌限频、
一次性事件只给没开站点的旁观者；样子没变时刚走进 32 格的人单发一份，发出去的过几秒再补（间隔加倍）。引擎是 potfake.py 里的假的。"""
from __future__ import print_function

import dgtest
import potkit as K
from potkit import BOWL, POT, SAUCE, TOMATO, fake

PotLook = K.PotLook


def _looks():
    """到目前为止发出去的 OnPotLook：[(收的人, 负载)]。"""
    return [(players, args[0]) for players, key, args in fake.multi if key == PotLook.ENDPOINT]


def _watched():
    """开了广播，加一位 200 格外的玩家 c 和一位在别的维度的玩家 d（a 在锅北边、b 在锅东边，都近）。"""
    PotLook.enable()
    fake.addPlayer("c", (200.5, 64.0, 200.5))
    fake.addPlayer("d", (10.5, 64.0, 8.5), dim=1)


def testNothingIsBroadcastWhileItIsSwitchedOff():
    manager, data = K.setup()
    assert PotLook.enabled() is False, "默认关着：没装前置包什么都不发"
    K.feed(manager, TOMATO, 16)
    K.run(manager, 3.0, stir=True)
    assert _looks() == [] and data["potLook"] is None


def testTheLookGoesToThePlayersWithin32BlocksOfTheSameDimensionAndIsMirroredInTheBlockEntityData():
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 1.0)
    looks = _looks()
    assert len(looks) == 1 and looks[0][0] == ["a", "b"], "只发给同维度 32 格内的人：%r" % [look[0] for look in looks]
    payload = looks[0][1]
    assert sorted(payload) == ["cooking", "dimensionId", "dish", "heated", "items", "meal", "pos", "progress", "rate", "served",
                               "spoon", "stirring", "sunk"]
    assert payload["dimensionId"] == 0 and payload["pos"] == [10, 64, 10]
    assert [item.get("count") for item in payload["items"]] == [8, 8, None, None, None, None] and len(payload["items"]) == 6
    assert payload["dish"] == {"newItemName": SAUCE, "newAuxValue": 0, "count": 1}
    assert payload["served"] == {} and payload["meal"] == {} and payload["sunk"] == [] and payload["heated"] is True
    assert payload["stirring"] is False and payload["cooking"] is False and payload["rate"] == 0.0 and payload["spoon"] == [0.0, 0.0]
    mirror = data["potLook"]
    assert sorted(mirror) == ["dish", "heated", "items"] and all(isinstance(key, str) for key in mirror), \
        "静态部分镜像进方块实体数据，空的几项（served / meal / sunk）不写"
    assert dict((key, payload[key]) for key in mirror) == mirror and mirror["items"] == payload["items"]
    K.run(manager, 2.0)
    assert len(_looks()) == 1, "什么也没变：不再发"


def _emptyParts(mirror):
    """镜像里放着的空列表、空字典（items 里的空格是 {}，和 previewItemSlot 一样的写法，不算）：引擎文档没说放不放得下，不该有。"""
    return [key for key, value in mirror.items() if key != "items" and isinstance(value, (list, dict)) and not value]


def testTheMirrorLeavesOutTheEmptyPartsAndKeepsTheSixItemCells():
    manager, data = K.setup()
    _watched()
    K.run(manager, 0.5)
    assert data["potLook"] == {"items": [{}] * 6, "heated": True}, "空锅：只有六个空格和热源"
    fake.setContainer(POT, 0, "minecraft:milk_bucket", 1)
    fake.setContainer(POT, 1, "minecraft:carrot", 2)
    K.run(manager, 0.5)
    mirror = data["potLook"]
    assert sorted(mirror) == ["heated", "items", "sunk"] and mirror["sunk"] == [0], "奶桶沉着；凑不成菜，没有 dish"
    assert [sorted(item) for item in mirror["items"]] == [["count", "newAuxValue", "newItemName"]] * 2 + [[]] * 4
    assert _emptyParts(mirror) == []
    K.setMeal(SAUCE, 3, data)
    K.run(manager, 0.5)
    mirror = data["potLook"]
    assert mirror["meal"] == {"newItemName": SAUCE, "newAuxValue": 0, "count": 3}
    assert "dish" not in mirror and "served" not in mirror and _emptyParts(mirror) == []


def testTheNamesInTheMirrorAndThePayloadAreAlwaysPlainStrings():
    manager, data = K.setup()
    _watched()
    data["previewItemSlot"] = [{"newItemName": u"arris:tomato_sauce", "newAuxValue": 0, "count": 2}]    # py2：读回来的可能是 unicode
    K.run(manager, 0.5)
    for meal in (data["potLook"]["meal"], _looks()[-1][1]["meal"]):
        assert meal == {"newItemName": SAUCE, "newAuxValue": 0, "count": 2} and type(meal["newItemName"]) is str


def testTheMirrorFollowsEveryChangeOfTheStaticPart():
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 0.5)
    fake.setContainer(POT, 0, TOMATO, 7)
    K.run(manager, 0.5)
    assert data["potLook"]["items"][0]["count"] == 7, "格子变了就重写镜像"
    assert [look[1]["items"][0]["count"] for look in _looks()] == [8, 7]
    data["heatEnable"] = False
    K.run(manager, 0.5)
    assert data["potLook"]["heated"] is False and _looks()[-1][1]["heated"] is False


def testStirringBroadcastsTheSpoonAtMostEightTimesASecond():
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 0.5)
    del fake.multi[:]
    K.run(manager, 3.0, stir=True)
    stirred = [payload for players, payload in _looks() if payload["stirring"]]
    assert 6 <= len(stirred) <= 3 * 8 + 2, len(stirred)
    assert all(abs(p["spoon"][0]) <= 1.0 and abs(p["spoon"][1]) <= 1.0 for p in stirred) and any(p["spoon"] != [0.0, 0.0] for p in stirred)
    assert any(p["rate"] > 0.0 and p["cooking"] for p in stirred), "被搅着煮的整批：进度每秒走多少是给了的"
    assert abs(max(p["rate"] for p in stirred) - K.HandCooking.PotCooking.batchSpeed(8) / 5.0) < 1e-4
    hand = K.HandCooking.handOf(0, POT)
    del fake.multi[:]
    for index in range(10):
        PotLook.stroke(0, POT, data, hand, 500.0 + index * 0.01)
    assert len(_looks()) == 1, "0.1 秒里的 10 次搅只发 1 次"
    PotLook.stroke(0, POT, data, hand, 500.2)
    assert len(_looks()) == 2


def testTheProgressIsRefreshedEveryTwoSecondsWhileItRuns():
    manager, data = K.setup()
    _watched()
    fake.setContainer(POT, 0, TOMATO, 8)
    fake.setContainer(POT, 1, TOMATO, 8)
    K.alone(0.4)
    del fake.multi[:]
    K.alone(4.0)
    sends = _looks()
    assert 1 <= len(sends) <= 3, "FD 原样在煮：进度在走，每 2 秒补一次：%d" % len(sends)
    assert all(payload["rate"] > 0.0 and payload["cooking"] is False for players, payload in sends)
    assert abs(sends[0][1]["rate"] - 1.0 / 5.0) < 1e-6, "FD 原样：1 / 一份的总时长"


def testOneShotEventsGoToTheBystandersAndNotToThoseWhoAreInTheStation():
    manager, data = K.setup()
    _watched()
    K.setMeal(SAUCE, 3, data)
    fake.give("a", 5, BOWL, 3)
    K.opened(manager)
    K.run(manager, 0.2)                           # 站点告诉广播：现在 a 在用它
    del fake.multi[:]
    assert K.do(manager, "a", K.custom("scoop", from_inventory=True))
    events = [(players, payload) for players, payload in _looks() if "event" in payload]
    assert events == [(["b"], {"dimensionId": 0, "pos": [10, 64, 10], "event": "scooped", "count": 1})], events
    assert K.effects() == [("scooped", {"count": 1})], "站点里的人从站点的表现事件里拿"


def testTheServedEventOfAStirredBatchAlsoSkipsTheStationUsers():
    manager, data = K.setup()
    _watched()
    HandCooking = K.HandCooking
    HandCooking.addMade("a", SAUCE, 40)
    K.feed(manager, TOMATO, 16)
    del fake.multi[:]
    K.run(manager, 20.0, stir=True)
    events = [(players, payload) for players, payload in _looks() if payload.get("event") == "served"]
    assert events == [(["b"], {"dimensionId": 0, "pos": [10, 64, 10], "event": "served", "grade": 3, "bonus": 4})], events
    assert K.effects() == [("served", {"grade": 3, "bonus": 4})]
    last = _looks()[-1][1]
    assert last["meal"]["count"] == 12 and last["items"] == [{}] * 6, "出锅后静态部分：料没了，菜 12 份在等盛"


def testForgettingAPotMakesTheNextStepSendItAgain():
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 0.5)
    count = len(_looks())
    K.run(manager, 1.0)
    assert len(_looks()) == count
    PotLook.forget(0, POT)
    K.run(manager, 0.5)
    assert len(_looks()) == count + 1, "方块拆了再放：从头发"


# ---------------------------------------------------------------- 走近的人、丢了的

def testAPlayerWhoWalksIntoRangeGetsTheCurrentLookAlthoughNothingChanged():
    """别人做菜时他在 32 格外（区块却加载着，客户端的场景是老样子）：走近之后锅不再变，没有下一次广播来纠正，要单发给他一份。"""
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 1.0)
    count = len(_looks())
    assert count == 1 and _looks()[0][0] == ["a", "b"]
    fake.world.players["c"]["pos"] = (20.5, 64.0, 10.5)             # c 从 200 格外走到 10 格外
    K.run(manager, 1.0)
    looks = _looks()
    assert len(looks) == count + 1 and looks[-1][0] == ["c"], "只单发给刚走进来的人：%r" % [look[0] for look in looks]
    assert looks[-1][1]["items"] == looks[0][1]["items"] and looks[-1][1]["dish"] == looks[0][1]["dish"], "是锅现在的样子"
    K.run(manager, 1.0)
    assert len(_looks()) == count + 1, "发过了：不重复"
    fake.world.players["c"]["pos"] = (200.5, 64.0, 200.5)
    K.run(manager, 1.0)
    fake.world.players["c"]["pos"] = (20.5, 64.0, 10.5)
    K.run(manager, 1.0)
    assert _looks()[-1][0] == ["c"] and len(_looks()) == count + 2, "走出去再回来：又算新来的"


def testALookThatDidNotChangeIsSentAgainAfterAFewSecondsAndThenLessAndLessOften():
    """发出去就不管收没收到（客户端脚本还没就绪时整份丢掉）：过 5 秒再单发一份，之后间隔加倍（10、20……），站久了的人不会一直每 5 秒一份。"""
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 1.0)
    start, base = fake.world.time, len(_looks())
    K.run(manager, 4.0)
    assert len(_looks()) == base, "还没到 5 秒"
    K.run(manager, 1.5)
    looks = _looks()
    assert len(looks) == base + 1 and sorted(looks[-1][0]) == ["a", "b"], "过了 5 秒：给近处的人各补一份"
    assert looks[-1][1]["items"] == looks[0][1]["items"]
    K.run(manager, 8.0)
    assert len(_looks()) == base + 1, "补过一次：下一份要再隔 10 秒，离上一份才 8 秒"
    K.run(manager, 3.0)
    assert len(_looks()) == base + 2, "隔了 10 秒：第二份"
    assert all("c" not in players and "d" not in players for players, _ in _looks()), "32 格外的、别的维度的什么都收不到"
    assert fake.world.time - start < 20.0


def testAChangedLookGoesToEveryoneAndStartsTheGapOver():
    manager, data = K.setup()
    _watched()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 6.5)                                             # 第一份补发已经发过了
    count = len(_looks())
    fake.setContainer(POT, 2, "minecraft:carrot", 1)                # 锅里多了一样东西：变了
    K.alone(0.4)
    assert len(_looks()) == count + 1 and _looks()[-1][0] == ["a", "b"], "变了：发给近处所有人"
    K.alone(4.0)
    assert len(_looks()) == count + 1
    K.alone(1.5)
    assert len(_looks()) == count + 2, "间隔从头算：5 秒后补一份"


def testTheSunkItemsAreListedAndAStationClosingMeansNoOneIsAttending():
    manager, data = K.setup()
    _watched()
    fake.setContainer(POT, 0, "minecraft:milk_bucket", 1)
    fake.setContainer(POT, 1, "minecraft:carrot", 1)
    fake.setContainer(POT, 2, "minecraft:egg", 2)
    K.alone(0.4)
    assert _looks()[-1][1]["sunk"] == [0, 2] and data["potLook"]["sunk"] == [0, 2]
    K.opened(manager)
    K.run(manager, 0.2)
    assert PotLook._sent[(0, POT)]["users"] == ["a"]
    manager.close("a")
    K.run(manager, 0.2)
    assert PotLook._sent[(0, POT)]["users"] == [], "站点关了：旁观者的名单清空，事件发给所有近处的人"


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
