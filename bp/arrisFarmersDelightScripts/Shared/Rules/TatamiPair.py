# -*- coding: utf-8 -*-
"""TatamiPair - 榻榻米方块两两配对：放下时和谁配成一对、另一半没了怎么拆开（双端，纯规则）

照 JE 的 TatamiBlock（FarmersDelight 1.20）：像床一样两格一对，不是连成一片——一对拼成一张两格长的榻榻米，
接缝处没有边框，两头是正方形的单块纹理；没配对的六面都是单块纹理。
- 方块态 FACING（六个方向）+ PAIRED。配对时 FACING 指向另一半；没配对时是放下时点的那一面的反方向（指向被点的方块）。
- 放下（getStateForPlacement + setPlacedBy）：玩家没潜行、点的是没配对的榻榻米时两块配成一对：新块 PAIRED，
  被点的那块 FACING 改成指回新块、也 PAIRED。潜行放下的不配对；点的是已经配了对的榻榻米也不配。
- 另一半没了（updateShape：FACING 那一格不再是榻榻米）：PAIRED 变假，FACING 不变。
  和 JE 不同的一处：活塞推着走的方块在路上是 minecraft:moving_block，这时不拆（JE 推一整对时先落地的那块会看到
  另一块还在路上、自己拆开，剩下一块半张的图指着它，是 JE 的毛病）；落定以后那一格再变时照常判。
外观全在方块 JSON 的 permutations 里（tools/gen_tatami.py 按 JE 的模型生成），服务端只写这两个方块态（Server/TatamiPairs.py）。

方块态的取值（bp/netease_blocks/arris_tatami.json）：
- arris:tatami_facing：网易 Facing 枚举（0 下 1 上 2 北 3 南 4 西 5 东），和放置事件的 face 同一套编号；缺省 0 就是 JE 的缺省 DOWN。
- arris:paired：0 / 1。
自定义方块态按名字降序从低位往高位排进 aux（名字大的占低位，arrisCreate 实测）：这两个名字让朝向占低 3 位、配对在第 4 位，
改成方块态以前放下的榻榻米（netease:face_directional，aux 是 direction 0..3）按位读出来都是没配对的。
"""
TATAMI = "arris:tatami"
FACING = "arris:tatami_facing"
PAIRED = "arris:paired"
MOVING_BLOCK = "minecraft:moving_block"

DOWN, UP, NORTH, SOUTH, WEST, EAST = range(6)
_STEP = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))


def opposite(facing):
    """反方向：Facing 枚举里相反的两个方向挨着（下 / 上、北 / 南、西 / 东）。"""
    return facing ^ 1


def step(pos, facing):
    """pos 沿 facing 走一格。"""
    dx, dy, dz = _STEP[facing]
    return (pos[0] + dx, pos[1] + dy, pos[2] + dz)


def _value(states, key):
    try:
        return int(states[key])
    except (KeyError, TypeError, ValueError):
        return None


def facingOf(states):
    """方块态里的朝向；没有、不认得的按缺省 0（下）。"""
    value = _value(states, FACING)
    return value if value in range(6) else DOWN


def isPaired(states):
    return _value(states, PAIRED) == 1


def stateOf(facing, paired):
    return {FACING: facing, PAIRED: 1 if paired else 0}


def placement(face, byPlayer, sneaking, clickedName, clickedStates):
    """一块榻榻米刚放下，放的时候点的是 face 面（Facing 枚举）。

    byPlayer：是不是玩家放的（JE 的 getPlayer() != null）；sneaking：玩家潜没潜行；
    clickedName / clickedStates：被点的那一格（新块沿 FACING 走一格）的方块名、方块态。
    返回 (新块的方块态, 被点的那块要改成的方块态；不配对时是 None)。
    """
    facing = opposite(face)
    pairing = bool(byPlayer) and not sneaking and clickedName == TATAMI and not isPaired(clickedStates)
    return stateOf(facing, pairing), (stateOf(opposite(facing), True) if pairing else None)


def keepsPairWith(partnerName):
    """配对的块 FACING 那一格是 partnerName 时还算不算一对：是榻榻米算；活塞推着走、还在路上的（moving_block）先不拆；
    没加载的格子（None）不拆。"""
    return partnerName in (TATAMI, MOVING_BLOCK, None)
