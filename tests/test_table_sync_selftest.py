# -*- coding: utf-8 -*-
# runner: both
"""游戏内自检的两半（Server/Debug/McdkTableSyncTest 追加、Client/Debug/McdkTableSyncTest 检查）离线跑一遍：约定的名字两边对得上
（并表之前客户端那半全是 False，服务端那半追加之后全是 True，拿掉之后又回到全 False）、重复追加不重复、追加后补发给进过服的玩家、
拿掉之后表和原来一模一样。离线只有一个进程，两端共用一份表，所以"客户端那半"看到的就是服务端刚追加的；真正走网络的在 test_table_sync_server.py。
"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest
import tablekit as K

world = fakeengine.install()
_quPackage = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs")
_quPackage.__path__ = []
_quClient = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Client")
_quClient.AllowCall = lambda fn: fn                       # Client/TableSync 只要这一个
sys.modules[fdtest.SCRIPTS + ".QuModLibs"], sys.modules[fdtest.SCRIPTS + ".QuModLibs.Client"] = _quPackage, _quClient
world.repeating = []
_baseGame = world._Game
world._Game = lambda target: dict(_baseGame(target), AddRepeatedTimer=lambda seconds, func: world.repeating.append((seconds, func)) or ("timer", 1))

Registry = fdtest.load("Server.EventRegistry")
TableSync = fdtest.load("Server.TableSync")
ServerTest = fdtest.load("Server.Debug.McdkTableSyncTest")
ClientTest = fdtest.load("Client.Debug.McdkTableSyncTest")
Diff = fdtest.load("Shared.Rules.TableDiff")
PRISTINE = K.Pristine(K.DEFAULT)
for _name in ("ArrisFarmersDelightInterface", "ArrisFarmersDelightObtain"):
    world.modAttr[("arris", _name)] = getattr(K.DEFAULT.load("Api.LegacyModAttr"), _name)


def _fresh():
    PRISTINE.restore()
    TableSync.syncer = Diff.Syncer()
    TableSync._known.clear()
    del TableSync._reported[:]
    del TableSync._timer[:]
    del world.repeating[:]
    del world.calls[:]
    world.players.clear()
    world.entities.clear()


def testTheClientHalfSaysFalseBeforeAndTrueAfterTheServerHalfAdds():
    _fresh()
    before = ClientTest.mcdk_test_table_sync_client()
    assert before["ok"] is False and not any(before["checks"].values()), before
    added = ServerTest.mcdk_test_table_sync_add()
    assert added["ok"] and added["rev"] == 1 and sorted(added["tables"]) == ["CanCookedFoodDict", "CookingPotRecipeList", "CuttingBoardDict", "knifeList"], added
    after = ClientTest.mcdk_test_table_sync_client()
    assert after["ok"] is True and all(after["checks"].values()) and sorted(after["checks"]) == sorted(before["checks"]), after
    assert set(after["sync"]) == set(["messages", "changed", "rev", "problems"])
    removed = ServerTest.mcdk_test_table_sync_remove()
    assert removed["ok"] and removed["removed"] == {"knife": True, "cutting": True, "cookable": True, "recipes": 1}, removed
    assert not any(ClientTest.mcdk_test_table_sync_client()["checks"].values())


def testAddingTwiceAddsOnceAndRemovingLeavesTheTablesAsTheyWere():
    _fresh()
    pristine = K.snapshot(K.DEFAULT)
    ServerTest.mcdk_test_table_sync_add()
    once = K.snapshot(K.DEFAULT)
    again = ServerTest.mcdk_test_table_sync_add()
    assert K.snapshot(K.DEFAULT) == once and again["rev"] == 1, "第二次什么也没追加：差异没变，版本还是 1"
    assert once != pristine
    ServerTest.mcdk_test_table_sync_remove()
    assert K.snapshot(K.DEFAULT) == pristine
    assert ServerTest.mcdk_test_table_sync_remove()["removed"] == {"knife": False, "cutting": False, "cookable": False, "recipes": 0}


def testAddingSendsToThePlayersWhoAlreadyJoinedWithoutWaitingForTheTimer():
    _fresh()
    world.addPlayer("a")
    assert Registry.dispatch("ClientLoadAddonsFinishServerEvent", {"playerId": "a"}) is False
    assert [call for call in world.calls if call[1] == "OnTableSync"] == []
    added = ServerTest.mcdk_test_table_sync_add()
    sent = [call for call in world.calls if call[1] == "OnTableSync"]
    assert added["players"] == ["a"] and sorted(call[2]["table"] for call in sent) == sorted(added["tables"]) and all(call[0] == "a" for call in sent), sent
    ServerTest.mcdk_test_table_sync_remove()


def testTheStaleSelfTestsAreReportedWhenTheContractIsMissing():
    saved = dict(world.modAttr)
    world.modAttr.clear()
    try:
        assert ServerTest.mcdk_test_table_sync_add()["ok"] is False and ServerTest.mcdk_test_table_sync_remove()["ok"] is False
    finally:
        world.modAttr.update(saved)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
