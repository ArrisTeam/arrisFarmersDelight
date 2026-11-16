# -*- coding: utf-8 -*-
"""RopeFence - 绳栅栏门开关的规则（双端，纯规则）

照 JE 的 FenceGateBlock.use（RopeFenceGateBlock 没改它）：
- 关着的门被右键：打开。门的朝向正对着玩家面朝方向的反方向（玩家站在门的背面）时，先转成玩家面朝的方向，
  这样打开的门总是朝远离玩家的一边收起来；
- 开着的门被右键：关上，朝向不变；
- 声音：打开 entity.leash_knot.break（基岩版 leashknot.break），关上 entity.leash_knot.place（leashknot.place）。

门有两个方块：arris:rope_fence_gate（关着）和 arris:rope_fence_gate_open（开着），开关就是换成另一个、朝向照算。
direction 状态沿用 netease:face_directional 的约定（方块的"前面"朝向放置的玩家，也就是 JE 的 FACING 的反方向）。
"""
from .Placement import directionOfFacing

GATE = "arris:rope_fence_gate"
GATE_OPEN = "arris:rope_fence_gate_open"
GATES = (GATE, GATE_OPEN)
SOUND_OPEN = "leashknot.break"
SOUND_CLOSE = "leashknot.place"


def toggleGate(name, direction, lookFacing):
    """右键门：返回 (换成的方块名, 新的 direction, 声音)。lookFacing 是玩家面朝的水平方向下标（0 南、1 西、2 北、3 东）。"""
    if name == GATE_OPEN:
        return GATE, direction, SOUND_CLOSE
    if direction == lookFacing:              # JE：FACING == 玩家方向的反方向 -> FACING = 玩家方向
        direction = directionOfFacing(lookFacing)
    return GATE_OPEN, direction, SOUND_OPEN
