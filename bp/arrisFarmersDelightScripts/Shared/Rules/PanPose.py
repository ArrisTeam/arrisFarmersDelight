# -*- coding: utf-8 -*-
"""PanPose - 锅里的节点摆成什么姿态：锅（pan 节点）转着挪着，上面的食物跟着它（场景坐标）；再换成世界里的转角（双端，纯逻辑）

Diegesis 的节点矩阵（NodeInstance.computeLocal）：先平移（基准 + moveTo 的位移），再按欧拉角 y、x、z 的次序转（Ry·Rx·Rz），再缩放；
孩子的矩阵是父亲的乘上自己的。锅里的 piece / under / lift 是 pan 的孩子：锅一颠（绕 x 转 TILT 度、往上往厨师一拽），它们跟着走；
蛋的手 hand_N 和蛋液 spill_N 是场景里最外层的节点，不跟锅。矩阵是 3x3 行优先元组（右手系，作用在列向量上），角度是度。
掉落物（平躺的）要再乘 Rx(90)：先躺平，贴图朝上。世界里的转角 = 绕竖轴转 PanModelMath.worldYaw(朝向)。
"""
import math

from . import PanModelMath
from . import PotModelMath as Pot


def _rx(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _ry(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _rz(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def euler(rot):
    """节点的欧拉角 (x, y, z) 度 -> 矩阵 Ry(y)·Rx(x)·Rz(z)（Transform.toQuaternion 的次序）。"""
    return Pot.multiply(Pot.multiply(_ry(rot[1]), _rx(rot[0])), _rz(rot[2]))


def lying(rot, panRot=(0.0, 0.0, 0.0)):
    """平躺在锅里的一块：锅的转动 · 自己的欧拉角 · 躺平。panRot 是锅这一刻的转角。"""
    return Pot.multiply(Pot.multiply(euler(panRot), euler(rot)), _rx(90.0))


def upright(rot):
    """立着的（蛋）：贴图正面朝 -z，再按欧拉角转。"""
    return euler(rot)


def inPan(panPos, panRot, local):
    """锅里一点（节点自己的位置，离锅节点原点）在场景里的位置：锅的位置 + 锅的转动 · local。"""
    x, y, z = Pot.apply(euler(panRot), local)
    return (panPos[0] + x, panPos[1] + y, panPos[2] + z)


def toWorld(facing, matrix):
    """场景里的矩阵 -> 世界里的矩阵（先转半圈到锅自己的坐标，再按朝向转：绕竖轴转 worldYaw）。"""
    return Pot.multiply(_ry(PanModelMath.worldYaw(facing)), matrix)
