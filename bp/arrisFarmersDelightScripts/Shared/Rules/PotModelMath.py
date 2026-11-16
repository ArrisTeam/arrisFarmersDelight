# -*- coding: utf-8 -*-
"""PotModelMath - 厨锅方块实体模型的坐标换算：方块朝向、勺子骨骼的位移与欧拉角（双端，纯逻辑）

场景里的量都用"锅自己的坐标"（和 JE 的方块模型一样：朝北放的方块，+x 东、+y 上、+z 南，单位像素，原点在方块西北下角），
这里把它换成引擎要的：
- 朝向：netease:face_directional 的 direction（就是方块的 aux）0 南、1 西、2 北、3 东，模型正面（-z）朝那边、绕方块中心转
  （Strata 知识库 14_block_entity_model §3.3，实机核对过朝北、朝南）；
- 骨骼动画：几何文件的 x 和 JE 反着，位移是 (-x, y, z)；骨骼的 rotation 在文件空间里等价于 Rz(-rz)·Ry(ry)·Rx(-rx)
  （03_model_skeleton/GEOMETRY_ENGINE.md §5），换回 JE 的坐标是 Q = Rz(rz)·Ry(-ry)·Rx(-rx)，所以把 Q 拆成
  Rz(c)·Ry(b)·Rx(a) 之后 rotation = (-a, -b, c)。
矩阵是 3×3 的行优先元组（右手系，作用在列向量上）。
"""
import math

NORTH, EAST, SOUTH, WEST = "north", "east", "south", "west"
FACINGS = {0: SOUTH, 1: WEST, 2: NORTH, 3: EAST}
FACING_YAW = {NORTH: 0.0, EAST: -90.0, SOUTH: 180.0, WEST: 90.0}   # 锅自己的坐标 -> 世界：绕 y 转这么多度
LADLE_REST = -22.5               # 靠在锅里的勺子：绕 z 转这么多度（柄朝 +x 歪）
LADLE_PIVOT = (8.0, 3.0, 8.0)    # 勺子的下端（骨骼的枢轴）
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def facingOf(aux):
    """方块的 aux（direction 状态）-> 朝向；越界按引擎的缺省当朝北。"""
    return FACINGS.get(int(aux or 0) & 3, NORTH)


def localToWorld(facing, dx, dz):
    """锅自己坐标里离方块中心 (dx, dz) 的水平偏移 -> 世界里的偏移。"""
    if facing == SOUTH:
        return -dx, -dz
    if facing == EAST:
        return -dz, dx
    if facing == WEST:
        return dz, -dx
    return dx, dz


def localPoint(facing, blockPos, x, y, z):
    """锅自己坐标里的一点（像素，原点在方块西北下角、方块朝北时）-> 世界坐标（格）。"""
    wx, wz = localToWorld(facing, x - 8.0, z - 8.0)
    return (blockPos[0] + 0.5 + wx / 16.0, blockPos[1] + y / 16.0, blockPos[2] + 0.5 + wz / 16.0)


def worldToLocal(facing, wx, wz):
    """世界里离方块中心的水平偏移 -> 锅自己的坐标。"""
    if facing == SOUTH:
        return -wx, -wz
    if facing == EAST:
        return wz, -wx
    if facing == WEST:
        return -wz, wx
    return wx, wz


def rotZ(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def multiply(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(matrix, vector):
    return tuple(sum(matrix[i][k] * vector[k] for k in range(3)) for i in range(3))


def boneRotation(matrix):
    """JE 坐标里的旋转矩阵 -> 骨骼动画的 rotation（度）。俯仰到 ±90 度时 a、c 分不开，取 a = 0。"""
    sinB = max(-1.0, min(1.0, -matrix[2][0]))
    b = math.asin(sinB)
    if abs(sinB) > 0.99999:
        a, c = 0.0, math.atan2(-matrix[0][1], matrix[1][1])
    else:
        a, c = math.atan2(matrix[2][1], matrix[2][2]), math.atan2(matrix[1][0], matrix[0][0])
    return (-math.degrees(a), -math.degrees(b), math.degrees(c))


def bonePosition(offset):
    """JE 坐标里的位移（像素）-> 骨骼动画的 position。"""
    return (-offset[0], offset[1], offset[2])


def ladleBone(tip, turn=IDENTITY):
    """勺子的下端在锅自己坐标里的位置 tip（像素）、相对"靠着的样子"又转了 turn（JE 的 rotationTo(rest, lean)）
    -> (position, rotation)：模型里 ladle 骨骼的两个动画通道。靠着不动时是 ((0, 0, 0), (0, 0, -22.5))。"""
    offset = (tip[0] - LADLE_PIVOT[0], tip[1] - LADLE_PIVOT[1], tip[2] - LADLE_PIVOT[2])
    return bonePosition(offset), boneRotation(multiply(turn, rotZ(LADLE_REST)))
