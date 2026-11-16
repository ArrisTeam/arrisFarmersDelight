# -*- coding: utf-8 -*-
# runner: both
"""绳栅栏门的开关（Server/RopeFences.py），用假引擎驱动（tests/fakeengine.py）；规则本身见 test_rope_fence_rules.py。

JE 的 FenceGateBlock.use：右键开 / 关，声音 leash_knot.break / place；基岩版的门是"关着 / 开着"两个方块，
右键就是换成另一个、把朝向写回去、广播声音；用了门就不再把手里的方块放到门旁边。
"""
from __future__ import print_function

import io
import os

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
Gates = fdtest.load("Server.RopeFences")
Rule = fdtest.load("Shared.Rules.RopeFence")

GATE, OPEN = Rule.GATE, Rule.GATE_OPEN
POS = (5, 64, 5)
BLOCK_CALLS = []
STATE = {"yaw": 0.0}


def _blockInfo(target):
    def setBlockNew(pos, blockDict, handling=0, dim=0, *rest):
        BLOCK_CALLS.append((tuple(pos), blockDict["name"], handling))
        world.blocks[(dim,) + tuple(pos)] = {"name": blockDict["name"], "states": None, "data": None}
        return True
    return {"SetBlockNew": setBlockNew}


world._BlockInfo = _blockInfo
world._Rot = lambda target: {"GetRot": lambda: (0.0, STATE["yaw"])}


def _setUp(name, direction, yaw, hand=None):
    del BLOCK_CALLS[:]
    world.blocks.clear()
    world.sounds[:] = []
    world.calls[:] = []
    world.players.clear()
    world.entities.clear()
    world.modAttr.clear()
    world.timers = []
    STATE["yaw"] = yaw
    world.addPlayer("p1", hand=hand)
    world.setBlock(POS[0], POS[1], POS[2], name, states={"direction": direction})


def _use():
    name = world.blockName(*POS)
    args = {"playerId": "p1", "blockName": name, "aux": 0, "cancel": False, "x": POS[0], "y": POS[1], "z": POS[2],
            "dimensionId": 0, "face": 1, "itemDict": None}
    Registry.dispatch("ServerBlockUseEvent", args, name)
    world.runTimers()
    return args


def _states():
    return world.blocks[(0,) + POS]["states"]


def testRightClickOpensTheGateAndPlaysTheUntieSound():
    _setUp(GATE, 2, 0.0)                       # 前面朝北，玩家朝南站在北边
    args = _use()
    assert args["cancel"] is True               # 不让手里的方块再放到门旁边
    assert world.blockName(*POS) == OPEN and _states() == {"direction": 2}
    assert BLOCK_CALLS == [(POS, OPEN, 0)]      # 处理方式 0 = 替换（不掉落）
    assert world.sounds == [("leashknot.break", (5.5, 64.5, 5.5))]


def testRightClickClosesAnOpenGateAndPlaysTheTieSound():
    _setUp(OPEN, 3, 90.0)
    _use()
    assert world.blockName(*POS) == GATE and _states() == {"direction": 3}
    assert world.sounds == [("leashknot.place", (5.5, 64.5, 5.5))]


def testDirectionFallsBackToTheEventAuxWhenTheStateCannotBeRead():
    _setUp(GATE, 2, 180.0)
    world.blocks[(0,) + POS]["states"] = None              # 读不到方块状态
    args = {"playerId": "p1", "blockName": GATE, "aux": 2, "cancel": False, "x": POS[0], "y": POS[1], "z": POS[2],
            "dimensionId": 0, "face": 1, "itemDict": None}
    Registry.dispatch("ServerBlockUseEvent", args, GATE)
    assert world.blockName(*POS) == OPEN and _states() == {"direction": 0}      # aux 2 = 前面朝北，朝北站着开：转向


def testOpeningFromTheBackTurnsTheGate():
    _setUp(GATE, 2, 180.0)                      # 玩家朝北（站在南边）开前面朝北的门
    _use()
    assert world.blockName(*POS) == OPEN and _states() == {"direction": 0}


def testClickIsCancelledEvenDuringTheCooldownSoABlockInHandIsNotPlaced():
    _setUp(GATE, 2, 0.0)
    args = {"playerId": "p1", "blockName": GATE, "aux": 0, "cancel": False, "x": POS[0], "y": POS[1], "z": POS[2],
            "dimensionId": 0, "face": 1, "itemDict": None}
    Registry.dispatch("ServerBlockUseEvent", args, GATE)          # 第一下：开门
    world.blocks[(0,) + POS]["name"] = GATE                        # 假装还是关着的门，看冷却里的第二下
    again = dict(args, cancel=False)
    Registry.dispatch("ServerBlockUseEvent", again, GATE)
    assert again["cancel"] is True and len(BLOCK_CALLS) == 1


def testBothGateBlocksAreHandledAndTheEntryPointLoadsTheModule():
    handled = [ident for ident in Registry.handlerNames("ServerBlockUseEvent") if ident[1] == "OnUseRopeFenceGate"]
    assert len(handled) == 1
    with io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, "Server", "ModServer.py"), encoding="utf-8") as f:
        assert "from . import RopeFences" in f.read()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
