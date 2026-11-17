# -*- coding: utf-8 -*-
# runner: both
"""炉灶朝向的游戏内自检的两半（Server/Debug/McdkGrillTest 的 mcdk_test_grill_facing / _restore，Client/Debug/McdkGrillTest 的 mcdk_test_grill_facing_client）
离线整条跑一遍：不是测朝向本身（那在 test_facing_of_aux.py / test_block_aux_helper.py），是保证自检代码没有拼写错误、两半约定的名字和算法对得上、
自检用的钩子（前置包登记的站点朝向钩子，不是直接调 Compat）确实被问到、普通世界和假日创造者实验玩法的世界（aux 是 0 / 4 / 8 / 12）都 ok、还原干净。
服务端那半用 stovefirekit 的假引擎（SetBlockNew / GetBlockStates 照官方文档），客户端那半用 panclient 的假引擎。"""
from __future__ import print_function

import sys

import facingkit as T
import panclient as C
import stovefirekit as F
from stovekit import fake

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

SERVER = F.potfake.load("Server.Debug.McdkGrillTest")
CLIENT = C.load("Client.Debug.McdkGrillTest")
GrillView = C.load("Compat.Diegesis.GrillView")
ServerApi = dgtest.load("Api.Server")
Engine = F.K._engine
world = C.world


class NS(object):
    def __init__(self, **fields):
        self.__dict__.update(fields)


def _server(installed=True, holiday=False):
    """干净的服务端假世界（炉灶站点登记好、玩家 a 在 (10.5, 64, 8.5)）；installed 假：前置包没装（ImportModule 回 None）。"""
    F.setup(look=False)
    fake.holiday = holiday
    SERVER._run.clear()
    Engine.serverApi.ImportModule = lambda name: ServerApi if installed and name == SERVER.STATION_API else None


def _client(installed=True):
    world.reset()
    behavior = NS(facing=GrillView.facingOf)
    sys_modules = C.sys.modules
    sys_modules[C.PACKAGE + ".Client.Engine"].clientApi.ImportModule = \
        lambda name: NS(getBehavior=lambda stationId: behavior if stationId == "arris:stove" else None) if installed and name == CLIENT.STATION_API else None


def testTheServerHalfSetsEveryDirectionAndReadsTheSameThingsTheHookDoes():
    _server()
    first = SERVER.mcdk_test_grill_facing(0)
    pos = first["pos"]
    assert pos == (25, 64, 21), "玩家脚下 (10.5, 64, 8.5) 往 +x 15 / +z 13"
    for direction in range(4):
        result = SERVER.mcdk_test_grill_facing(direction)
        assert result["ok"] is True and result["pos"] == pos and result["block"] == "arris:stove", result
        assert result["state_direction"] == direction and result["aux"] == direction and result["get_block_aux"] == direction, result
        assert result["aux_decodes_to"] == direction and result["server_facing"] == result["expected_yaw"] == T.YAW[direction], result
        assert fake.world.blocks[(0, pos)] == "arris:stove"
    restored = SERVER.mcdk_test_grill_facing_restore()
    assert restored["ok"] is True and restored["restored"] == "minecraft:air" and fake.world.blocks[(0, pos)] == "minecraft:air", restored


def testTheUnlitBlockIsChecked():
    _server()
    for direction in range(4):
        result = SERVER.mcdk_test_grill_facing(direction, "arris:stove_extinguish")
        assert result["ok"] is True and result["block"] == "arris:stove_extinguish" and result["server_facing"] == T.YAW[direction], result
        assert fake.world.blocks[(0, result["pos"])] == "arris:stove_extinguish"
    assert SERVER.mcdk_test_grill_facing(2, "arris:stove")["ok"] is True, "换回点着的"
    assert SERVER.mcdk_test_grill_facing_restore()["ok"] is True


def testAHolidayCreatorWorldGivesAux048And12AndStillComesOutOk():
    _server(holiday=True)
    seen = []
    for direction in range(4):
        result = SERVER.mcdk_test_grill_facing(direction)
        seen.append(result["aux"])
        assert result["ok"] is True and result["state_direction"] == direction and result["aux_decodes_to"] == direction, result
        assert result["server_facing"] == T.YAW[direction], result
    assert seen == [0, 4, 8, 12], seen
    assert SERVER.mcdk_test_grill_facing_restore()["ok"] is True


def testWithoutThePrerequisiteTheHookIsNoneAndOkIsNotTrue():
    _server(installed=False)
    result = SERVER.mcdk_test_grill_facing(1)
    assert result["server_facing"] is None and result["ok"] is False and "前置包" in result["note"], result
    assert result["state_direction"] == 1 and result["aux_decodes_to"] == 1, "别的读法照样返回，能对"
    assert SERVER.mcdk_test_grill_facing_restore()["ok"] is True


def testTheServerHalfRefusesABadDirectionAndRestoreWithoutAStart():
    _server()
    assert SERVER.mcdk_test_grill_facing(4)["ok"] is False and SERVER.mcdk_test_grill_facing(-1)["ok"] is False
    assert SERVER.mcdk_test_grill_facing_restore() == {"case": "grill_facing_restore", "ok": False, "error": "not started"}


def testTheRestoreBringsBackWhateverWasThereBeforeIncludingItsDirection():
    _server()
    pos = (25, 64, 21)
    fake.world.blocks[(0, pos)] = "arris:skillet"
    fake.states[(0, pos)] = {"direction": 3}
    fake.blockAux[(0, pos)] = 3
    SERVER.mcdk_test_grill_facing(1)
    assert fake.world.blocks[(0, pos)] == "arris:stove"
    restored = SERVER.mcdk_test_grill_facing_restore()
    assert restored["ok"] is True and fake.world.blocks[(0, pos)] == "arris:skillet" and fake.states[(0, pos)] == {"direction": 3}


# ---------------------------------------------------------------- 客户端那半

def testTheClientHalfReadsTheBlocksAuxAndTheRegisteredBehaviorsHook():
    for name in ("arris:stove", "arris:stove_extinguish"):
        for aux, yaw in sorted(T.YAW.items()):
            _client()
            world.blocks[C.POS] = (name, aux)
            result = CLIENT.mcdk_test_grill_facing_client(list(C.POS))
            assert result["ok"] is True and result["block"] == name and result["aux"] == aux, result
            assert result["aux_decodes_to"] == T.DIRECTION[aux] and result["client_facing"] == result["expected_yaw"] == yaw, result
            assert result["pos"] == C.POS and result["dim"] == 0


def testTheClientHalfDefaultsToTheServerHalfsPositionAndRefusesWhatIsNotAStove():
    _client()
    x, y, z = world.foot
    where = (int(x) + 15, int(y), int(z) + 13)
    world.blocks[where] = ("arris:stove", 2)
    assert CLIENT.mcdk_test_grill_facing_client()["pos"] == where and CLIENT.mcdk_test_grill_facing_client()["ok"] is True
    world.blocks[where] = ("minecraft:stone", 0)
    result = CLIENT.mcdk_test_grill_facing_client()
    assert result["ok"] is False and "不是炉灶" in result["error"], result
    del world.blocks[where]
    assert CLIENT.mcdk_test_grill_facing_client()["ok"] is False, "那里没有方块（没加载）"


def testWithoutThePrerequisiteTheClientHookIsNoneAndOkIsNotTrue():
    _client(installed=False)
    world.blocks[C.POS] = ("arris:stove", 1)
    result = CLIENT.mcdk_test_grill_facing_client(C.POS)
    assert result["client_facing"] is None and result["ok"] is False and "前置包" in result["note"] and result["aux_decodes_to"] == 1, result


def testTheTwoHalvesAgreeOnTheSameBlockInBothKindsOfWorld():
    """把两半对起来（游戏里人工对的那件事）：服务端读到的 aux 放进客户端的方块，两端的钩子说同一个朝向，都等于期望的站点朝向。"""
    for holiday in (False, True):
        _server(holiday=holiday)
        for direction in range(4):
            served = SERVER.mcdk_test_grill_facing(direction)
            _client()
            world.blocks[C.POS] = (served["block"], served["aux"])
            seen = CLIENT.mcdk_test_grill_facing_client(C.POS)
            assert served["ok"] and seen["ok"] and served["server_facing"] == seen["client_facing"] == T.YAW[direction], (holiday, direction, served, seen)
            assert served["aux"] == seen["aux"] and served["aux_decodes_to"] == seen["aux_decodes_to"] == direction
        SERVER.mcdk_test_grill_facing_restore()


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
