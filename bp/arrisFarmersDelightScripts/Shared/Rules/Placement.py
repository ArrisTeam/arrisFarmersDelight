# -*- coding: utf-8 -*-
"""Placement - 方块朝向与放置位置（双端，纯规则）"""
import math

# 方块朝向 aux（0-3）→ 展示实体的 (pitch, yaw)
ENTITY_FACE = {
    0: (0, -90),
    1: (0, 0),
    2: (0, 90),
    3: (0, 180)
}

# 点击面（Facing 枚举）→ 放置坐标相对点击方块的偏移
_FACE_OFFSET = {
    0: (0, -1, 0),  # Down
    1: (0, 1, 0),   # Up
    2: (0, 0, -1),  # North
    3: (0, 0, 1),   # South
    4: (-1, 0, 0),  # West
    5: (1, 0, 0),   # East
}

# 假日创造者实验玩法下，四个朝向的 aux 是 0/4/8/12 而不是 0/1/2/3
_HOLIDAY_AUX = {0: 0, 4: 1, 8: 2, 12: 3}
_PLAIN_AUX = {0: 0, 1: 1, 2: 2, 3: 3}


def auxFromAngle(x1, y1, x2, y2):
    """从方块 (x1, y1) 看向玩家 (x2, y2)（水平面），返回方块应朝的 aux 0-3。

    恰好落在 45° 分界线上时归入 2（与旧实现一致）。
    """
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if -45 < angle < 45:
        return 3
    if 45 < angle < 135:
        return 0
    if 135 < angle < 180 or -180 < angle < -135:
        return 1
    return 2


def placePositions(x, y, z):
    """点击 (x, y, z) 的各个面时，新方块的放置坐标：{面: 坐标}。"""
    return dict((face, (x + dx, y + dy, z + dz)) for face, (dx, dy, dz) in _FACE_OFFSET.items())


def holidayAuxMap(experimentalHoliday):
    """方块 aux → 朝向 0-3 的映射表；experimentalHoliday 为是否开启了假日创造者实验玩法。"""
    return _HOLIDAY_AUX if experimentalHoliday else _PLAIN_AUX


def placesPumpkinPie(sneaking, sneakToPlace):
    """原版南瓜派对方块使用时，是不是放成方块（JE PlacePumpkinPieMixin.usePumpkinPie）。

    配置 enablePumpkinPieSneakToPlace 为假（JE 缺省）：一律放；为真：只有潜行才放，不潜行照常吃。
    """
    return bool(sneaking) if sneakToPlace else True


def eatsPumpkinPie(aimsAtBlock, sneaking, sneakToPlace):
    """原版南瓜派右键时还能不能吃：准星对着方块、而且这一下该放方块时不吃（JE：useOn 返回放置的结果，放不下是 FAIL，
    不会再落到"吃"）；对着空气，或者配置要求潜行而没潜行，照常吃。"""
    return not (aimsAtBlock and placesPumpkinPie(sneaking, sneakToPlace))


# 水平朝向下标：0 南(+z)、1 西(-x)、2 北(-z)、3 东(+x)，与玩家的 yaw（0 朝南、90 朝西、180 朝北、-90 朝东）
# 和 netease:face_directional 的 direction 状态（south 0、west 1、north 2、east 3）是同一套编号
FACING_VECTORS = ((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))


def facingOfYaw(yaw):
    """玩家面朝的水平方向下标（JE 的 Direction.fromYRot：floor(yaw / 90 + 0.5) & 3）。"""
    return int(math.floor(yaw / 90.0 + 0.5)) & 3


def directionOfFacing(facing):
    """玩家面朝 facing 时放下的 direction 状态：方块的"前面"朝向玩家，也就是朝向的反方向（官方文档：玩家放置时 north 贴图面向玩家）。"""
    return (facing + 2) & 3


def facingOfDirection(direction):
    """direction 状态对应的放置者面朝方向（directionOfFacing 的逆，同一个公式）。"""
    return (direction + 2) & 3


def stepFacing(pos, facing, steps=1):
    """pos 沿水平朝向 facing 走 steps 格。"""
    dx, dy, dz = FACING_VECTORS[facing & 3]
    return (pos[0] + dx * steps, pos[1] + dy * steps, pos[2] + dz * steps)
