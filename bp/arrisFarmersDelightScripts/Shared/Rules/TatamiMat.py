# -*- coding: utf-8 -*-
"""TatamiMat - 长榻榻米垫（像床一样的两格方块）与短榻榻米垫的放置、拆除规则（双端，纯规则）

照 JE 的 TatamiMatBlock / TatamiHalfMatBlock：
- 放置：脚（FOOT）放在点到的格子，头（HEAD）在玩家面朝方向的下一格（getStateForPlacement 用 getHorizontalDirection）；
  头所在的格子要能被顶替（canBeReplaced），两格的下面都不能是空气（canSurvive：!level.isEmptyBlock(pos.below())）；
- 拆除：拆哪一半，另一半都跟着没（updateShape 里另一半不见了就变成空气），只掉一个；
- 下面的方块没了，这一半碎掉（短垫子同样靠 canSurvive）。

方块的 direction 状态沿用 netease:face_directional 的约定（south 0、west 1、north 2、east 3，方块的"前面"朝向放置的玩家），
所以头在 direction 对面那一侧、也就是放置者面朝的方向。
"""
from ..Data.Blocks import cabinetList
from ..Data.Cooking import StoveList
from .Placement import directionOfFacing, facingOfDirection, facingOfYaw, placePositions, stepFacing

FOOT = "arris:tatami_full_mat"
HEAD = "arris:tatami_full_mat_head"
HALF = "arris:tatami_half_mat"
PAIR = (FOOT, HEAD)
SUPPORTED = (FOOT, HEAD, HALF)
AIR = "minecraft:air"

# 放方块时直接顶替掉的原版方块（原版资料库里 replaceable 的草、藤、火、水……；雪层只有一层才算，这里不算）
REPLACEABLE = frozenset((
    "minecraft:deadbush", "minecraft:fern", "minecraft:large_fern", "minecraft:short_grass", "minecraft:tall_grass",
    "minecraft:short_dry_grass", "minecraft:tall_dry_grass", "minecraft:seagrass", "minecraft:vine",
    "minecraft:glow_lichen", "minecraft:sculk_vein", "minecraft:crimson_roots", "minecraft:warped_roots",
    "minecraft:nether_sprouts", "minecraft:fire", "minecraft:soul_fire",
    "minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava",
))


# 自己会处理右键的方块：手里拿着东西点它们时先轮到它们（JE：方块的 use 优先，潜行才改成放方块）
USES_THE_CLICK = ("arris:cutting_board", "arris:cooking_pot", "arris:skillet", "arris:basket", "minecraft:frame",
                  "minecraft:glow_frame")


def usesTheClick(blockName):
    return blockName in USES_THE_CLICK or blockName in cabinetList or blockName in StoveList


def isReplaceable(name):
    """这一格放新方块时能不能直接占掉（没加载的格子 name 是 None，不行）。"""
    return name == AIR or name in REPLACEABLE


def hasGround(belowName):
    """JE 的 canSurvive：下面那一格不是空气就行（水、草、半砖都算；没加载的格子不算）。"""
    return belowName is not None and belowName != AIR


def below(pos):
    return (pos[0], pos[1] - 1, pos[2])


def partnerName(name):
    return HEAD if name == FOOT else FOOT


def partnerPos(name, pos, direction):
    """另一半的位置：脚的头在放置者面朝的方向，头的脚在反方向。"""
    look = facingOfDirection(direction)
    return stepFacing(pos, look) if name == FOOT else stepFacing(pos, look, -1)


def isSideNeighbor(pos, other):
    """other 是不是 pos 水平相邻的四格之一。"""
    return other[1] == pos[1] and abs(other[0] - pos[0]) + abs(other[2] - pos[2]) == 1


def _footCell(clicked, face, clickedName):
    # JE 的 BlockPlaceContext：点到的方块能被顶替就放在它那一格，否则放在点到的面外侧
    return tuple(clicked) if isReplaceable(clickedName) else placePositions(*clicked)[face]


def placementPlan(clicked, face, clickedName, yaw, nameAt):
    """玩家（面朝 yaw）点方块 clicked 的 face 面放长榻榻米垫。

    放得下返回 (脚的位置, 头的位置, 两格的 direction 状态)，放不下返回 None。
    nameAt(pos) 是查那一格方块名的函数（没加载的格子返回 None）。
    """
    foot = _footCell(clicked, face, clickedName)
    if not isReplaceable(nameAt(foot)):
        return None
    facing = facingOfYaw(yaw)
    head = stepFacing(foot, facing)
    if not isReplaceable(nameAt(head)):
        return None
    if not hasGround(nameAt(below(foot))) or not hasGround(nameAt(below(head))):
        return None
    return foot, head, directionOfFacing(facing)


def halfMatPlaceable(clicked, face, clickedName, nameAt):
    """短榻榻米垫放下去的那一格下面要有方块（引擎照常放，只在不满足时取消）。"""
    return hasGround(nameAt(below(_footCell(clicked, face, clickedName))))


def supportLost(pos, neighborPos, toName):
    """邻居变化事件：脚下的方块变成了空气。"""
    return neighborPos == below(pos) and toName == AIR


def partnerLost(name, pos, direction, neighborPos, toName):
    """邻居变化事件：另一半所在的格子不再是另一半了。"""
    return name in PAIR and neighborPos == partnerPos(name, pos, direction) and toName != partnerName(name)
