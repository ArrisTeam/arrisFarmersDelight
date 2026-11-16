# -*- coding: utf-8 -*-
# runner: both
"""绳栅栏门开关的纯规则（Shared/Rules/RopeFence.py）。

JE 的 FenceGateBlock.use：关着的门打开，玩家站在门背面（门的朝向正对着玩家面朝的反方向）时先转向；开着的门关上；
RopeFenceGateBlock 的声音是 entity.leash_knot.break（打开，字幕"绳栅栏门：解开"）/ entity.leash_knot.place（关上，"系上"）。
基岩版的门是"关着 / 开着"两个方块，右键就是换成另一个、把朝向写回去（服务端见 test_rope_fence_gate.py）。
"""
from __future__ import print_function

import fdtest

Rule = fdtest.load("Shared.Rules.RopeFence")
GATE, OPEN = Rule.GATE, Rule.GATE_OPEN


def testClosedGateOpensAndAnOpenGateClosesKeepingItsDirection():
    assert Rule.toggleGate(OPEN, 2, 0) == (GATE, 2, "leashknot.place")
    assert Rule.toggleGate(OPEN, 1, 3) == (GATE, 1, "leashknot.place")
    assert Rule.toggleGate(GATE, 2, 0)[0] == OPEN
    assert Rule.toggleGate(GATE, 2, 0)[2] == "leashknot.break"


def testGateTurnsAwayWhenOpenedFromItsBack():
    # direction 2：前面朝北，放置的人站在北边朝南（lookFacing 0）。他开门不转向；
    # 站在南边朝北（lookFacing 2）的人开门：门转成前面朝南（direction 0），打开的门收向远离他的一边
    assert Rule.toggleGate(GATE, 2, 0)[1] == 2
    assert Rule.toggleGate(GATE, 2, 2)[1] == 0
    # 站在侧面（朝东 / 朝西）开：不转向
    assert Rule.toggleGate(GATE, 2, 1)[1] == 2 and Rule.toggleGate(GATE, 2, 3)[1] == 2
    # 四个朝向各自一致：玩家面朝方向 == direction 时转 180°
    for direction in range(4):
        for look in range(4):
            expected = (direction + 2) & 3 if look == direction else direction
            assert Rule.toggleGate(GATE, direction, look)[1] == expected, (direction, look)


def testGateNamesAndSounds():
    assert Rule.GATES == ("arris:rope_fence_gate", "arris:rope_fence_gate_open")
    assert (Rule.SOUND_OPEN, Rule.SOUND_CLOSE) == ("leashknot.break", "leashknot.place")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
