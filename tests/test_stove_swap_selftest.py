# -*- coding: utf-8 -*-
# runner: both
"""炉灶点火 / 灭火换方块的游戏内自检（Server/Debug/McdkStoveFireTest：start 放炉灶摆东西、记引擎事件的先后并换方块，collect 核对、还原）离线整条跑一遍：
不是测换方块本身（那在 test_stove_fire.py），是保证自检代码没有拼写错误、记录的先后是对的、核对认得出东西丢了。
引擎事件的先后用 stovefirekit 的几种假引擎摆出来：同步 / 晚到 / 没有，方块实体当场在 / 晚建 / 一直不建。"""
from __future__ import print_function

import copy

import stovefirekit as F
import stovekit as K
from stovekit import fake

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest

SELFTEST = F.potfake.load("Server.Debug.McdkStoveFireTest")
POS = (25, 64, 25)                           # 玩家 a 在 (10.5, 64, 8.5)：+x 15 / +z 17 之前取整是 (10, 64, 8) -> (25, 64, 25)
LIT, UNLIT = F.LIT, F.UNLIT


def _tick(blockName, seconds=0.3):
    """自检放的那座炉灶（不在 stovekit 的 STOVE 位置）的方块实体 tick 走一遍真分发。"""
    fake.world.time += seconds
    args = {"dimension": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2], "blockName": blockName}
    F.EventRegistry.dispatch("ServerBlockEntityTickEvent", args, blockName)


def _run(events="sync", entity="now", toUnlit=True, tick=True):
    F.setup(events="sync", entity="now", swapMode={"events": events, "entity": entity}, look=False)     # 自检自己摆炉灶时引擎是好的，换方块时才是要试的先后
    F.StoveSwap._swaps.clear()
    started = SELFTEST.mcdk_test_stove_swap_start(toUnlit)
    F.flush()
    if tick and started.get("ok"):
        for _ in range(3):
            _tick(UNLIT if toUnlit else LIT)
    return started, SELFTEST.mcdk_test_stove_swap_collect()


def _order(log):
    """log 里的事件分成 swap 返回之前（同步到的）和之后（晚到的）两截。"""
    index = log.index(("swap_returned",))
    return log[:index], log[index + 1:]


def testTheSelfTestRunsStartToCollectAndAllChecksPassWhenTheEngineIsKind():
    started, collected = _run("sync", "now")
    assert started["ok"] is True and started["from"] == LIT and started["to"] == UNLIT and started["pos"] == POS, started
    assert started["block_now"] == UNLIT and started["entity_there_right_after"] is True and started["direction_right_after"] == 2, started
    assert started["data_pending_right_after"] is False, "事件同步到、方块实体当场在：数据当场写进去了"
    assert collected["ok"] is True and all(collected["checks"].values()) and collected["block"] == UNLIT, collected
    assert collected["removal_events_claimed"] == [True], "旧方块的移除事件来了、被当成换方块挡住"
    assert fake.world.blocks[(0, POS)] == "minecraft:air" and F.groundItems() == [], "还原干净，没有东西掉到地上"


def testTheLogShowsWhetherTheEventsCameBeforeOrAfterTheSwapReturned():
    started, collected = _run("sync", "now")
    before, after = _order(started["log"])
    assert ("claims", LIT, True) in before and ("apply", True) in before and after == [], started["log"]
    started, collected = _run("late", "now")
    before, after = _order(started["log"])
    assert ("apply", True) in before and not [entry for entry in before if entry[0] == "claims"], "当场写进去了，移除事件还没来"
    assert ("claims", LIT, True) in collected["log"][len(before) + 1:], "晚到的移除事件也被挡住"
    assert collected["ok"] is True, collected


def testTheDataWaitsWhenTheNewBlockEntityIsLateAndTheEventOrTheTickWritesIt():
    for events in ("sync", "late"):
        started, collected = _run(events, "later")
        assert started["entity_there_right_after"] is (events == "sync") and collected["ok"] is True, (events, started, collected)
        assert started["data_pending_right_after"] is (events == "late"), (events, started)
    started, collected = _run("silent", "now")
    assert started["data_pending_right_after"] is False and collected["ok"] is True and ("claims", LIT, True) not in collected["log"]


def testTheReverseDirectionLightsAnUnlitStove():
    started, collected = _run("sync", "now", toUnlit=False)
    assert started["from"] == UNLIT and started["to"] == LIT and started["block_now"] == LIT, started
    assert collected["ok"] is True and collected["block"] == LIT and collected["removal_events_claimed"] == [True], collected


def testTheCollectSaysNotOkWhenTheFoodIsLost():
    """新方块实体一直不来：数据只能等着（再过 5 秒丢在地上），collect 不能说 ok。"""
    started, collected = _run("silent", "never", tick=False)
    assert started["ok"] is True and started["entity_there_right_after"] is False and started["data_pending_right_after"] is True, started
    assert collected["ok"] is False and collected["checks"]["items_all_there_and_in_place"] is False, collected


def testTheHooksAreTakenOffAgainAndTheStartRefusesToRunTwice():
    originals = (F.StoveSwap.claims, F.StoveSwap.apply)
    started, collected = _run("sync", "now")
    assert (F.StoveSwap.claims, F.StoveSwap.apply) == originals, "套的记录用完还原了"
    F.setup(look=False)
    assert SELFTEST.mcdk_test_stove_swap_start()["ok"] is True
    again = SELFTEST.mcdk_test_stove_swap_start()
    assert again["ok"] is False and again["error"] == "already running"
    assert SELFTEST.mcdk_test_stove_swap_collect()["ok"] is True
    assert SELFTEST.mcdk_test_stove_swap_collect() == {"case": "stove_swap_collect", "ok": False, "error": "not started"}


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
