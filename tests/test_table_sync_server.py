# -*- coding: utf-8 -*-
# runner: both
"""下游追加的表什么时候发给客户端（Server/TableSync.py，假引擎见 fakeengine.py）：玩家进服发一次累计的差异、之后的头两轮各再整份发一次
（进服那一份可能丢了）、没有追加时什么都不发、定时看表变没变并只给收过的人补发变了的那几张、没进服 / 走掉的人不发、
出错的一轮不拖垮定时器、给一个人发出错不耽误别人、问题只在算差异时记一次日志；
发出去的消息拿给另一份包（客户端）并进去，表和服务端的一样；入口模块里导入了它。
"""
from __future__ import print_function

import io
import os
import sys

import fakeengine
import fdtest
import tablekit as K

world = fakeengine.install()
world.repeating = []              # AddRepeatedTimer 登记的 (秒, 函数)
_baseGame = world._Game


def _game(target):
    methods = _baseGame(target)
    methods["AddRepeatedTimer"] = lambda seconds, func: world.repeating.append((seconds, func)) or ("timer", len(world.repeating))
    return methods


world._Game = _game
Registry = fdtest.load("Server.EventRegistry")
TableSync = fdtest.load("Server.TableSync")
Diff = fdtest.load("Shared.Rules.TableDiff")
Tables = fdtest.load("Shared.Rules.SyncTables")
PRISTINE = K.Pristine(K.DEFAULT)
JOIN = "ClientLoadAddonsFinishServerEvent"


class _Capture(object):
    def __init__(self):
        self.chunks = []

    def write(self, text):
        self.chunks.append(text)

    def flush(self):
        pass


def _fresh(*players):
    """干净的开局：表是原样，Syncer 重新记基线（就像模块刚导入），没有计时器，这些玩家在线但还没进服。"""
    PRISTINE.restore()
    TableSync.syncer = Diff.Syncer()
    TableSync._known.clear()
    TableSync._again.clear()
    del TableSync._reported[:]
    del TableSync._timer[:]
    del world.repeating[:]
    del world.calls[:]
    world.players.clear()
    world.entities.clear()
    for playerId in players:
        world.addPlayer(playerId)


def _join(playerId):
    assert Registry.dispatch(JOIN, {"playerId": playerId}) is False, "处理函数不拦着别的模块（PlayerSession、Basket）处理同一个事件"


def _sent(playerId=None):
    """发出去的表同步消息：[(玩家, 消息)]，取走。"""
    found = [(target, data) for target, endpoint, data in world.calls if endpoint == Tables.ENDPOINT and playerId in (None, target)]
    world.calls[:] = [call for call in world.calls if call[1] != Tables.ENDPOINT or (playerId is not None and call[0] != playerId)]
    return found


def _poll():
    assert len(world.repeating) == 1
    world.repeating[0][1]()


def _settle():
    """进服之后的头几轮检查：把"进服那一份可能丢了"的那几次整份重发走完，丢掉发出去的。"""
    for _ in range(TableSync.RESENDS):
        _poll()
    _sent()


def testAJoiningPlayerGetsTheWholeDiffOnceAndTheTimerStarts():
    _fresh("a", "b")
    knives = K.downstream(K.DEFAULT)          # 下游在 LoadServerAddonScriptsAfter 里追加：晚于模块导入时记的基线
    _join("a")
    sent = _sent()
    assert [target for target, _message in sent] == ["a"] * 8 and all(message["rev"] == 1 for _target, message in sent), sent
    assert sorted(message["table"] for _target, message in sent) == sorted(["CuttingBoardDict", "knifeList", "axeList", "CanCookedFoodDict", "StoveList",
                                                                          "CanProvideHeatBlockList", "CookingPotRecipeList", "platePackagedFoodDict"])
    assert len(world.repeating) == 1 and world.repeating[0][0] == TableSync.POLL
    _join("b")
    assert [target for target, _message in _sent()] == ["b"] * 8 and len(world.repeating) == 1, "第二个玩家：也是全部，计时器还是一个"
    assert knives is K.DEFAULT.load("Shared.Data.Cutting").knifeList, "联动契约交出去的还是同一个对象"


def testNothingIsSentWhenNoDownstreamAddedAnything():
    _fresh("a")
    _join("a")
    for _ in range(4):
        _poll()
    assert _sent() == [] and TableSync._known == {"a": 0} and len(world.repeating) == 1, "没有追加：进服、重发、定时都什么也不发"


def testTheJoinPushIsRepeatedOnTheNextTwoPollsBecauseItMayHaveBeenLost():
    """进服那一份发出去就不知道收没收到（客户端的端点还没登记好时整份丢掉）：之后的头两轮检查各再整份发一次，客户端并表是幂等的。"""
    _fresh("a", "b")
    K.downstream(K.DEFAULT)
    _join("a")
    first = _sent()
    assert len(first) == 8
    _poll()
    again = _sent()
    assert [message["table"] for _t, message in again] == [message["table"] for _t, message in first], "第一轮：整份再发"
    assert all(target == "a" for target, _m in again)
    _join("b")                                                      # b 晚一轮进服：各数各的
    _sent()
    _poll()
    assert sorted(set(target for target, _m in _sent())) == ["a", "b"], "a 的第二次、b 的第一次"
    _poll()
    assert sorted(set(target for target, _m in _sent())) == ["b"], "a 发完了，b 还有一次"
    _poll()
    assert _sent() == [], "都发完了：表不变就不再发"


def testAPlayerWhoseCallFailsIsRetriedAndDoesNotStarveTheOthers():
    """给一个人发的时候 Call 抛了异常：只记日志、下一轮再给他发，后面的人照收。"""
    _fresh("a", "b")
    knives = K.downstream(K.DEFAULT)
    _join("a")
    _join("b")
    _settle()
    real, capture, old = TableSync.Call, _Capture(), (sys.stdout, sys.stderr)

    def flaky(playerId, endpoint, message):
        if playerId == "a":
            raise RuntimeError("player a is gone")
        return real(playerId, endpoint, message)

    knives.append("ends_delight:late_knife")
    TableSync.Call = flaky
    sys.stdout = sys.stderr = capture
    try:
        _poll()
    finally:
        TableSync.Call = real
        sys.stdout, sys.stderr = old
    assert [target for target, _m in _sent()] == ["b"], "a 出错不耽误 b"
    assert TableSync._known["a"] == 1 and TableSync._known["b"] == 2, "a 没记成发过"
    assert "表同步" in "".join(capture.chunks)
    _poll()
    assert [(target, message["table"]) for target, message in _sent()] == [("a", "knifeList")], "下一轮补给 a"


def testAJoinWhosePushFailsIsStillRememberedAndFilledInLater():
    _fresh("a")
    K.downstream(K.DEFAULT)
    real, capture, old = TableSync.Call, _Capture(), (sys.stdout, sys.stderr)

    def broken(playerId, endpoint, message):
        raise RuntimeError("not ready")

    TableSync.Call = broken
    sys.stdout = sys.stderr = capture
    try:
        _join("a")
    finally:
        TableSync.Call = real
        sys.stdout, sys.stderr = old
    assert _sent() == [] and TableSync._known == {"a": 0}
    _poll()
    assert len(_sent("a")) == 8, "下一轮整份补上"


def testALateChangeGoesToEveryoneWhoJoinedAndOnlyForTheChangedTables():
    _fresh("a", "b")
    knives = K.downstream(K.DEFAULT)
    _join("a")
    _join("b")
    _settle()
    _poll()
    assert _sent() == [], "表没变：这一轮什么也不发"
    knives.append("ends_delight:late_knife")
    _poll()
    sent = _sent()
    assert sorted((target, message["table"], message["rev"]) for target, message in sent) == [("a", "knifeList", 2), ("b", "knifeList", 2)], sent
    assert sent[0][1]["ops"] == [K.KNIFE, "ends_delight:late_knife"]
    _poll()
    assert _sent() == [] and TableSync._known == {"a": 2, "b": 2}
    world.addPlayer("c")
    _join("c")
    assert sorted(message["table"] for _target, message in _sent("c")) == sorted(message["table"] for message in TableSync.syncer.messages()), "晚来的人要全部"
    assert TableSync._known["c"] == 2


def testAPlayerWhoHasNotFinishedLoadingGetsNothingAndAPlayerWhoLeftIsForgotten():
    _fresh("a", "b")
    knives = K.downstream(K.DEFAULT)
    _join("a")
    _join("b")
    _settle()
    world.addPlayer("c")                       # 在线，但客户端还没加载完（没收到 ClientLoadAddonsFinish）：端点还没登记，发了也丢
    del world.players["b"]
    knives.append("ends_delight:late_knife")
    _poll()
    assert [target for target, _message in _sent()] == ["a"] and sorted(TableSync._known) == ["a"], "b 走了忘掉，c 还没进服不发"
    _join("c")
    assert len(_sent("c")) == 8 and sorted(TableSync._known) == ["a", "c"]


def testStepForEveryoneAlsoReachesOnlinePlayersWhoNeverJoinedLikeAfterAScriptReload():
    """热重载脚本之后进过服的名单是空的、也不会再有进服事件：调试用的 step(everyone=True) 连在线却没进过服的人也发；平时的 step() 不发给他们。"""
    _fresh("a", "b")
    K.downstream(K.DEFAULT)
    TableSync.step()
    assert _sent() == [] and TableSync._known == {}
    TableSync.step(everyone=True)
    assert sorted(set(target for target, _message in _sent())) == ["a", "b"] and TableSync._known == {"a": 1, "b": 1}
    TableSync.step(everyone=True)
    assert _sent() == [], "收过的不再发"


def testTheMessagesAreWireSafeAndTheClientEndsUpWithTheSameTables():
    _fresh("a")
    K.downstream(K.DEFAULT)
    _join("a")
    client = K.Package()
    results = K.deliver([message for _target, message in _sent("a")], client)
    assert all(result["changed"] and not result["problems"] for result in results), results
    assert K.snapshot(K.DEFAULT) == K.snapshot(client)


def testProblemsAreLoggedWhenTheDiffIsComputedNotOnEveryPoll():
    _fresh("a")
    legacy = K.DEFAULT.load("Api.LegacyModAttr")
    legacy.ArrisFarmersDelightInterface("CanCookedFoodDict", {"x:raw": "x:cooked", "x:weird": set(["a"])})
    saved, sys.stdout = sys.stdout, _Capture()
    try:
        _join("a")
        _poll()
        _poll()
        printed = "".join(sys.stdout.chunks)
    finally:
        sys.stdout = saved
    assert printed.count("表同步") == 1 and "x:weird" in printed, printed
    assert [message["ops"] for _target, message in _sent("a")][0][0]["k"] == "x:raw", "能发的照发"


def testABadEntryIsLoggedEvenWhenItIsTheOnlyThingDownstreamAddedAndOnlyOnce():
    _fresh("a")
    legacy = K.DEFAULT.load("Api.LegacyModAttr")
    legacy.ArrisFarmersDelightInterface("CanCookedFoodDict", {"x:weird": set(["a"])})
    saved, sys.stdout = sys.stdout, _Capture()
    try:
        _join("a")
        _poll()
        legacy.ArrisFarmersDelightInterface("CanCookedFoodDict", {"x:weird2": object()})      # 又一条坏的：新的问题再写一次，旧的不重复
        _poll()
        printed = "".join(sys.stdout.chunks)
    finally:
        sys.stdout = saved
    assert printed.count("表同步") == 2 and "x:weird" in printed and "x:weird2" in printed, printed
    assert _sent() == [] and TableSync.syncer.rev == 0, "没有能发的：什么也不发"


def testAFailingPollIsLoggedAndTheNextOneRunsAgain():
    _fresh("a")
    knives = K.downstream(K.DEFAULT)
    _join("a")
    _settle()
    original = TableSync.syncer.refresh

    def broken():
        raise RuntimeError("boom")

    TableSync.syncer.refresh = broken
    saved, sys.stdout, savedErr, sys.stderr = sys.stdout, _Capture(), sys.stderr, _Capture()       # 异常的 traceback 也打到 stderr，别在测试输出里吓人
    try:
        _poll()
        printed = "".join(sys.stdout.chunks)
        trace = "".join(sys.stderr.chunks)
    finally:
        sys.stdout, sys.stderr = saved, savedErr
        TableSync.syncer.refresh = original
    assert "表同步出错" in printed and "boom" in trace and _sent() == []
    knives.append("ends_delight:late_knife")
    _poll()
    assert [message["table"] for _target, message in _sent("a")] == ["knifeList"]


def testAHeatConditionWrittenOnTheServerGoesOutWithTheAuxSetTheServerWorkedOut():
    """热源的状态条件（契约之外的表）：服务端写进来的条件，在算差异之前先由 Server/HeatAux 照引擎（假的 GetBlockStatesFromAuxValue）
    算出满足条件的 aux，进服那一份里两张表一起发；并进另一份包（客户端）以后，客户端的 heatsByAux 按它判。"""
    _fresh("a")
    HeatAux = fdtest.load("Server.HeatAux")
    cooking = K.DEFAULT.load("Shared.Data.Cooking")
    world.auxStates["mymod:brazier"] = lambda aux: {"mymod:coals": aux} if aux < 4 else None
    cooking.HeatSourceStateDict["mymod:brazier"] = {"mymod:coals": {"min": 2}}
    try:
        _join("a")
        sent = [message for _target, message in _sent("a")]
        assert sorted(message["table"] for message in sent) == ["HeatSourceAuxDict", "HeatSourceStateDict"], sent
        assert cooking.HeatSourceAuxDict["mymod:brazier"] == [2, 3]
        client = K.Package()
        assert all(result["changed"] and not result["problems"] for result in K.deliver(sent, client))
        heats = client.load("Shared.Rules.HeatSources")
        assert heats.heatsByAux("mymod:brazier", 3) and not heats.heatsByAux("mymod:brazier", 1), "客户端按服务端算好的 aux 判"
        assert K.snapshot(K.DEFAULT) == K.snapshot(client)
    finally:
        world.auxStates.pop("mymod:brazier", None)
        HeatAux._done.pop("mymod:brazier", None)


def testTheEntryPointsImportTheTwoEnds():
    root = os.path.join(fdtest.BP, fdtest.SCRIPTS)
    for relPath in ("Server/ModServer.py", "Client/ModClient.py"):
        source = io.open(os.path.join(root, relPath), encoding="utf-8").read()
        assert "from . import TableSync  # noqa: F401" in source, relPath
    assert Tables.ENDPOINT == "OnTableSync"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
