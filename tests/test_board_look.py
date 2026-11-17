# -*- coding: utf-8 -*-
# runner: both
"""砧板的旁观广播（Server/BoardLook.py + Compat/Diegesis/BoardEmit.py）：附近没开着站点的人也收到切菜声、放东西声的事件，开着站点的人只收站点自己的 effect，
不重复；服务端不再自己放固定的声音（刀声、放、取、做成都由两边的客户端按声音表放）。站点逻辑和前置包的 Manager 是真的，引擎是 potfake 的假引擎。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import boardkit as K
from boardkit import fake

BoardLook = K.potfake.load("Server.BoardLook")
LookWatch = K.potfake.load("Server.Helpers.LookWatch")             # 被拒的敲击声的限速在这里（砧板、煎锅、炉灶共用）
REFUSED_GAP = LookWatch.REFUSED_GAP
PAUSE = REFUSED_GAP + 0.05                                  # 隔够了（浮点的边界上不比）
KNIFE, CABBAGE = "arris:iron_knife", "arris:cabbage"
BOARD_SOUNDS = ("ambient.cutting_board.knife", "dig.wood", "armor.equip_leather", "random.pop")


def _setup(enabled=True):
    manager, data = K.setup()
    LookWatch.time = K.potfake.Clock(fake.world)             # 被拒的敲击声按玩家限速（真实时间）：测试里读假世界的钟
    LookWatch._refusedAt.clear()
    fake.addPlayer("c", (200.5, 64.0, 10.5))                 # 太远
    fake.addPlayer("d", (10.5, 64.0, 10.5), dim=1)           # 别的维度
    BoardLook.enable(enabled)
    return manager, data


def _looks(playerId):
    return [args[0] for target, name, args in fake.calls if target == playerId and name == "OnBoardLook"]


def _place(manager, name, count, slot=3):
    K.carry(manager, slot, name, count)
    return K.do(manager, "a", K.custom("place"))


def _chop(manager, mark=0):
    K.advance(0.2)
    return K.do(manager, "a", K.custom("chop", mark=mark, at=8.0, at_x=6.5, yaw=0))


def _knife(slot=7, durability=250):
    fake.give("a", slot, KNIFE, 1)
    fake.world.players["a"]["inv"][slot]["durability"] = durability


def _soundsPlayedByTheServer():
    return [args[0]["soundName"] for _target, name, args in fake.calls if name == "OnPlaySound" and args[0]["soundName"] in BOARD_SOUNDS]


def testOnlookersNearTheBoardGetTheEventsAndTheCookDoesNot():
    manager, data = _setup()
    try:
        K.opened(manager)
        assert _place(manager, CABBAGE, 2)
        _knife()
        assert _chop(manager)
        assert _looks("a") == [], "开着站点的人收站点自己的 effect，不再收一份广播"
        assert [look["event"] for look in _looks("b")] == ["placed", "chopped"], "站在旁边没开站点的人：放东西和切的事件"
        assert _looks("c") == [] and _looks("d") == [], "太远的、别的维度的什么也没有"
        chopped = _looks("b")[-1]
        assert chopped["event"] == "chopped" and chopped["done"] is True and chopped["count"] == 2 and chopped["dimensionId"] == 0
        assert chopped["pos"] == list(K.BOARD) and chopped["tool"] == KNIFE and chopped["item"] == CABBAGE
        assert chopped["stroke"] == "cut" and chopped["block"] is False and chopped["yields"] == ["arris:cabbage_leaf"], "声音和碎屑要用的"
    finally:
        BoardLook.enable(False)


def testNothingIsSentWhileTheBroadcastIsOff():
    manager, data = _setup(enabled=False)
    K.opened(manager)
    assert _place(manager, CABBAGE, 1)
    _knife()
    assert _chop(manager)
    assert not [1 for _target, name, _args in fake.calls if name == "OnBoardLook"], "默认关着：没装前置包的世界什么也不发"


def testEveryoneWhoHasTheStationOpenGetsItsEffectAndNoBroadcast():
    manager, data = _setup()
    try:
        K.opened(manager)
        K.opened(manager, "b")
        assert _place(manager, CABBAGE, 1)
        _knife()
        assert _chop(manager)
        assert _looks("a") == [] and _looks("b") == [], "两个人都开着站点：都走 effect"
        assert "chopped" in [name for name, _data in K.effects("b")], "b 自己的站点 effect 里有这一刀"
    finally:
        BoardLook.enable(False)


def testOnlyTheEventsThatMakeSoundOrDustAreBroadcastAndWithoutTheBigAnimationData():
    manager, data = _setup()
    try:
        K.opened(manager)
        assert _place(manager, "minecraft:bread", 1)
        assert _place(manager, "arris:tomato", 1, slot=4)
        assert K.do(manager, "a", K.custom("take"))
        assert K.do(manager, "a", K.custom("take"))
        events = [look["event"] for look in _looks("b")]
        assert events == ["placed", "placed", "taken", "taken"], events
        for look in _looks("b"):
            assert "stack" not in look and "layers" not in look, "动画才用的大块不带"
        assert [(look["at"], look["item"]) for look in _looks("b") if look["event"] == "placed"] == [(0, "minecraft:bread"), (1, "arris:tomato")],             "放下一层带着层号和放的什么：旁观的人据此补手倒 / 磕的声音"
        taken = [look for look in _looks("b") if look["event"] == "taken"][0]
        assert taken["carved"] is False and taken["at"] == 1
        assert not [look for look in _looks("b") if look["event"] == "refused"]
        K.do(manager, "a", K.custom("take"))                             # 板空了再取：没有东西被拒，什么事件也没有
        assert [look["event"] for look in _looks("b")] == events
        assert BoardLook.payloadOf(0, (1, 2, 3), "assembled", {"layers": [1], "finish": "sandwich", "block": False}) == \
            {"dimensionId": 0, "pos": [1, 2, 3], "event": "assembled", "finish": "sandwich", "block": False, "count": 1}, "assembled 多带做成了几层：旁观的人据此算收尾演多久"
    finally:
        BoardLook.enable(False)


def testARefusedPlaceChopOrAssembleIsHeardByOnlookersToo():
    """JE 的 refused 效果（放不上去、没有刀、两刀间隔太近、凑不成菜……每一种）发给所有看得见板的人，旁观的人也听得到那一声敲击；负载只有名字，弹回的那一叠（stack）不带。"""
    manager, data = _setup()
    try:
        K.opened(manager)
        assert _place(manager, "arris:tomato", 1)                          # 板不收番茄
        refused = [look for look in _looks("b") if look["event"] == "refused"]
        assert len(refused) == 1 and "stack" not in refused[0] and refused[0]["pos"] == list(K.BOARD), "放不上去：弹回，旁观的人听到敲击"
        assert _looks("a") == [], "开着站点的人收 effect，不再收一份广播"
        assert K.effects("a")[0][0] == "refused"
        before = len(_looks("b"))
        K.advance(PAUSE)                                                   # 同一个人被拒的敲击声旁观的人 0.3 秒内至多听一声
        assert K.do(manager, "a", K.custom("assemble")) is False
        assert [look["event"] for look in _looks("b")[before:]] == ["refused"], "凑不成菜：拒绝"
        K.do(manager, "a", K.click(K.inv(0), kind="PUT_AWAY"))
        assert _place(manager, CABBAGE, 1, slot=5)
        K.advance(0.2)
        before = len(_looks("b"))
        assert _chop(manager) and [look["event"] for look in _looks("b")[before:]] == ["refused"], "没有刀：这一刀被拒"
    finally:
        BoardLook.enable(False)


def testARefusedChopIsNotAHornTheCooksOwnClientCanBlowAtEveryoneNearby():
    """被拒的动作每秒能来 40 个：改过的客户端发一串非法的 chop，每个都给 32 格内每个旁观的人发一次广播、放一声敲击。同一个人被拒的敲击声旁观的人 0.3 秒内至多听一声；
    站点里的人收的 effect 一个不少（他的客户端据此撤回画好的切口）。"""
    manager, data = _setup()
    try:
        K.opened(manager)
        assert _place(manager, CABBAGE, 1)                                 # 板上有菜，没有刀
        K.effects()
        before = len(_looks("b"))
        for _ in range(20):                                                # 20 个非法的 chop，每个隔 0.07 秒（一秒多一点）
            K.advance(0.07)
            assert K.do(manager, "a", K.custom("chop", mark=7, at=8.0))
        heard = [look["event"] for look in _looks("b")[before:]]
        assert heard == ["refused"] * 4, "第 1、6、11、16 个（每隔 0.35 秒）：%r" % (heard,)
        assert [name for name, _data in K.effects("a")] == ["refused"] * 20, "站点里的人每个都收到"
        K.advance(PAUSE)
        K.do(manager, "a", K.custom("chop", mark=7, at=8.0))
        assert len(_looks("b")) == before + 5, "隔够了又能听到"
    finally:
        BoardLook.enable(False)


def testTheRefusalLimitIsPerPlayerAndOnlyForRefusedNotForTheOtherSounds():
    manager, data = _setup()
    fake.addPlayer("e", (11.5, 64.0, 10.5))                                # 另一个旁观的人
    try:
        K.opened(manager, "a")
        K.opened(manager, "b")
        assert _place(manager, CABBAGE, 1)
        K.effects("a")
        K.effects("b")
        before = len(_looks("e"))
        for _ in range(3):                                                 # 两个人各发三个非法的 chop，同一时刻
            for playerId in ("a", "b"):
                K.do(manager, playerId, K.custom("chop", mark=7, at=8.0))
        assert [look["event"] for look in _looks("e")[before:]] == ["refused", "refused"], "一个人一声，不是两个人共用一声"
        K.advance(PAUSE)
        _knife()                                                           # 刀来了：合法的 chop 和放东西不受限，连着来也都听得到
        before = len(_looks("e"))
        assert _chop(manager) and _place(manager, CABBAGE, 1, slot=5)
        assert [look["event"] for look in _looks("e")[before:]] == ["chopped", "placed"]
    finally:
        BoardLook.enable(False)


def testOnlyThePlayersRefusedAMomentAgoAreRemembered():
    LookWatch._refusedAt.clear()
    clock = LookWatch.time = K.potfake.Clock(fake.world)
    try:
        for index in range(300):
            clock.world.time += PAUSE
            assert LookWatch.mayHearRefusal("player%d" % index)
        assert len(LookWatch._refusedAt) <= 65, len(LookWatch._refusedAt)
        assert not LookWatch.mayHearRefusal("player299"), "刚听过的还在"
        clock.world.time -= 1000.0                                         # 时钟倒着走：当作隔够了
        assert LookWatch.mayHearRefusal("player299")
    finally:
        LookWatch._refusedAt.clear()


def testAnAssembledDishIsBroadcastWithItsFinishAndLayerCountButNotItsLayers():
    manager, data = _setup()
    try:
        K.opened(manager)
        fake.give("a", 5, "minecraft:bowl", 2)
        fake.give("a", 6, "minecraft:crimson_fungus", 2)
        fake.give("a", 7, "minecraft:warped_fungus", 2)
        assert K.do(manager, "a", K.custom("bookFill", key="d:arris:nether_salad", sets=1))
        made = [look for look in _looks("b") if look["event"] == "assembled"]
        assert len(made) == 1 and made[0]["finish"] and "layers" not in made[0]
        assert made[0]["count"] == 3, "碗和两样菌：三层"
    finally:
        BoardLook.enable(False)


def testNamesInTheBroadcastAreAlwaysPlainStrEvenForARecipeWithUnicodeNames():
    """py2 里下游包加的配方（从 JSON 读来的）名字可能是 unicode，事件走线格式只收 str：整个 chopped 被丢掉的话，站点里的人连一刀的动画都没有。"""
    cutting = K.potfake.load("Shared.Data.Cutting")
    manager, data = _setup()
    cutting.CuttingBoardDict[("x:thing", 0)] = {"itemList": [{"itemName": u"x:piece", "count": 2}], "tool": cutting.knifeList}
    try:
        K.opened(manager)
        assert _place(manager, "x:thing", 1)
        _knife()
        assert _chop(manager)
        look = [look for look in _looks("b") if look["event"] == "chopped"][0]
        assert look["yields"] == ["x:piece"] and all(type(name) is str for name in look["yields"] + [look["tool"], look["item"]]), look
        assert "chopped" in [name for name, _data in K.effects()], "站点里的人也收到了这一刀"
        assert K.count("x:piece") == 2
    finally:
        del cutting.CuttingBoardDict[("x:thing", 0)]
        BoardLook.enable(False)


def testTheServerPlaysNoFixedBoardSoundsAnyMore():
    """原来服务端对所有人放刀声（不分工具）、放 / 插 dig.wood、取 armor.equip_leather、做成 random.pop；现在由两边的客户端按声音表放。"""
    manager, data = _setup()
    try:
        K.opened(manager)
        assert _place(manager, CABBAGE, 1)
        _knife()
        assert _chop(manager)
        assert _place(manager, "minecraft:bread", 1)
        assert K.do(manager, "a", K.custom("take"))
        assert _soundsPlayedByTheServer() == [], _soundsPlayedByTheServer()
    finally:
        BoardLook.enable(False)


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
