# -*- coding: utf-8 -*-
"""PanModelMath - 煎锅方块实体模型的坐标换算：场景坐标（JE 的，锅柄朝 +z）、锅自己的坐标、世界，锅和油膜的骨骼值（双端，纯逻辑）

HoD 的场景文件 skillet.json 写在"锅柄朝 +z、镜头在锅柄那一侧、朝 -z 看"的坐标里（场景坐标，像素，原点在方块西北下角）。
基岩版的煎锅模型（rp/models/entity/skillet.geo.json）和厨锅一样写在"锅自己的坐标"里：方块朝北放时模型的正面（-z）朝北，锅柄在正面这一侧，
所以场景坐标和锅自己的坐标差一个绕竖轴转半圈：(x, y, z) <-> (16 - x, y, 16 - z)。锅自己的坐标再按方块朝向（netease:face_directional 的
direction = 玩家放下时方块的"正面"朝向 = 锅柄朝向）转到世界，换算用 PotModelMath 的（朝向、骨骼动画的符号都是同一套，实机核对过）。
所以：锅柄永远朝方块的朝向，镜头永远在锅柄那一侧（JE 的 Orientation.BLOCK），不管开站的人站在哪一边。

骨骼（模型里 pan 骨骼，枢轴在锅心，带着整只锅和锅里的油膜）：场景里"锅绕 x 转 θ 度、往 (0, oy, oz) 挪"：
- 场景转半圈到锅自己的坐标：绕 x 的转角变号（Rx(θ) 变成 Rx(-θ)），位移 (0, oy, oz) 变成 (0, oy, -oz)；
- 再用 PotModelMath.boneRotation / bonePosition 换成骨骼动画的两个通道：rotation = (θ, 0, 0)，position = (0, oy, -oz)。
"""
import math

from . import PotModelMath as Pot

SCENE_CAMERA = {"pos": (8.0, 40.0, 50.0), "target": (8.0, 1.0, 14.0), "fov": 34.0}     # scenes/skillet.json 的 camera
SCENE_PAN = (8.0, 0.0, 8.0)                  # pan 节点在场景里的位置：锅心、锅底
HANDLE_BOX = ((6.0, 0.5, 14.5), (10.0, 4.0, 27.5))      # handle 节点的碰撞盒 [-2, 0.5, 6.5] ~ [2, 4, 19.5]，加上 pan 的位置
MOUTH_BOX = ((1.0, 0.0, 1.0), (15.0, 6.0, 15.0))        # mouth（drop_zone "hand"）
FOOD_BOX = ((1.5, 0.0, 1.5), (14.5, 5.0, 14.5))         # food
SCENE_TURN = 180.0


def sceneToLocal(x, y, z):
    """场景坐标 -> 锅自己的坐标（绕方块中心转半圈）；反过来也是它。"""
    return (16.0 - x, y, 16.0 - z)


def worldPoint(facing, blockPos, point):
    """场景里一点（像素）-> 世界坐标（格）。facing 是 PotModelMath.facingOf(方块的 aux)。"""
    return Pot.localPoint(facing, blockPos, *sceneToLocal(*point))


def scenePoint(facing, blockPos, wx, wy, wz):
    """世界坐标（格）-> 场景里一点（像素）。"""
    x, z = Pot.worldToLocal(facing, (wx - blockPos[0] - 0.5) * 16.0, (wz - blockPos[2] - 0.5) * 16.0)
    return sceneToLocal(8.0 + x, (wy - blockPos[1]) * 16.0, 8.0 + z)


def worldYaw(facing):
    """场景里绕竖轴的转角 + 这么多度 = 世界里的转角（先转半圈到锅自己的坐标，再按朝向转）。"""
    return (Pot.FACING_YAW[facing] + SCENE_TURN) % 360.0


def handleSide(facing):
    """锅柄朝世界的哪个水平方向 (dx, dz)（单位向量）：镜头也在这一侧。"""
    return {Pot.NORTH: (0.0, -1.0), Pot.SOUTH: (0.0, 1.0), Pot.EAST: (1.0, 0.0), Pot.WEST: (-1.0, 0.0)}[facing]


def _rotX(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def panBone(tilt, offset):
    """场景里锅绕 x 转 tilt 度、位移 offset = (ox, oy, oz) 像素 -> pan 骨骼的 (position, rotation)（动画的两个通道）。"""
    return Pot.bonePosition((-offset[0], offset[1], -offset[2])), Pot.boneRotation(_rotX(-tilt))


def oilBone(x, z):
    """锅底上离锅心场景坐标 (x, z) 的油膜骨骼的 position 通道（骨骼在锅心，高度不动）。"""
    return Pot.bonePosition((-x, 0.0, -z))


def facingOf(aux):
    return Pot.facingOf(aux)
