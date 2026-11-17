# -*- coding: utf-8 -*-
"""ItemPose - 客户端掉落物的姿态换算：意图（平躺 / 竖立）-> 旋转矩阵 -> SetDropItemTransform 的三个角（双端，纯规则）

实机标定（3.10，2026-11-16）：物品贴图轴心在底边中点，缩放 1 时边长半格；rot = (0, 0, 0) 竖立、正面朝 -Z；
rot = (x, y, z) 表示 R = Rz(z)·Rx(x)·Ry(y)。坐标是格，方向是世界的 (dx, dz)。
与场景交互前置包的 Client/PropMath.py 同一套（两个包互不依赖，各带一份）；离线测试见 tests/test_block_display.py。
"""
import math

ITEM_SPAN = 8.0   # 缩放 1 时贴图边长（站点像素）
BLOCK_LIFT = 3.2  # 引擎给方块物品的掉落物加的抬高（站点像素 = 0.2 格），不随缩放和旋转变
RAISED_PIVOT = 2.5  # 画成一张平面图的方块物品：轴心离贴图底边这么远（缩放 1 时的站点像素 = 16 像素的贴图里从下往上第 5 行）


def _rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def engineEuler(m):
    """旋转矩阵 -> SetDropItemTransform 的 (x, y, z) 度，按 R = Rz(z)·Rx(x)·Ry(y) 分解。"""
    x = math.degrees(math.asin(max(-1.0, min(1.0, m[2][1]))))
    if abs(m[2][1]) > 1.0 - 1.0e-12:   # 万向锁：Y 与 Z 合成一个转角，全记在 Z 上
        return (x, 0.0, math.degrees(math.atan2(m[1][0], m[0][0])))
    return (x, math.degrees(math.atan2(-m[2][0], m[2][2])), math.degrees(math.atan2(-m[0][1], m[1][1])))


def flatMatrix(alongX, alongZ):
    """平躺、贴图横向（u 轴）沿世界方向 (alongX, alongZ)：Ry(α)·Rx(90)，u 轴落在 (cos α, 0, -sin α)。"""
    return _mul(_ry(math.degrees(math.atan2(-alongZ, alongX))), _rx(90.0))


def uprightMatrix(facingX, facingZ, roll):
    """竖立、正面朝世界方向 (facingX, facingZ)、在贴图平面内顺时针转 roll 度：Ry(β)·Rz(roll)。"""
    return _mul(_ry(math.degrees(math.atan2(-facingX, -facingZ))), _rz(roll))


def lyingMatrix(yaw, pitch=0.0, roll=0.0):
    """平躺着再转：先躺平（贴图朝上、贴图的上边朝世界 +Z），再照 JE 场景节点的欧拉角（度，顺序 y、x、z）转。
    厨锅里漂着的料用它：yaw 是在液面上转的角，pitch / roll 是随波的晃和翻身。"""
    return _mul(_mul(_mul(_ry(yaw), _rx(pitch)), _rz(roll)), _rx(90.0))


def framed(axes, matrix):
    """在一个转过的场景里算好的姿态换到世界里：axes 是 3x3，列是场景的 x / y / z 轴在世界里的方向。"""
    return _mul(axes, matrix)


def standingMatrix(axes, lean, tilt):
    """立着的东西：正面朝场景的 -z（镜头那边），往后仰 lean 度、在贴图平面里倾 tilt 度（JE 节点的欧拉角 (lean, 0, tilt)，顺序 y、x、z），
    再换到世界里：axes·Rx(lean)·Rz(tilt)。厨师手里端着的瓶、桶、蛋用它。"""
    return _mul(axes, _mul(_rx(lean), _rz(tilt)))


def pivotFor(center, matrix, scale):
    """视觉中心 -> 轴心（贴图底边中点）：中心 = 轴心 + R·(0, 半边长, 0)。坐标是格。"""
    half = ITEM_SPAN / 16.0 * scale * 0.5
    return (center[0] - matrix[0][1] * half, center[1] - matrix[1][1] * half, center[2] - matrix[2][1] * half)


def raisedShift(matrix, scale):
    """画成一张平面图的方块物品（花、树苗、野生作物：物品类型是 block，掉落物却是一张贴图）照贴图物品的规矩摆之前，中心要先挪多少
    （站点像素），画出来才落在本来要的中心上。matrix 是它的 3x3 姿态（y 朝上的空间都行：站点的、世界的）。
    实机（3.10，2026-11-18：胡萝卜和虞美人、野生胡萝卜并排，从侧面平视着量，缩放 1 和 2 各一次）：引擎画这类物品是
    T(0, 0.2 格, 0)·S·R 再画一张轴心在离底边 5/16 处的贴图——抬高那一段和方块物品的立方体一样不跟缩放、不跟旋转走，轴心那一段跟。
    照"轴心在底边中点"摆，它会高出 0.2 格（平躺时整张浮在面上）、并沿贴图自己的上方向错开 5/16 个边长：
    画出来的中心 = 报的中心 + (0, BLOCK_LIFT, 0) - R·(0, RAISED_PIVOT·缩放, 0)，所以报的中心要反着挪这么多。
    蘑菇丛不是这一类：它的掉落物是方块模型缩小的立体小蘑菇，不是一张贴图。"""
    reach = RAISED_PIVOT * scale
    return (matrix[0][1] * reach, matrix[1][1] * reach - BLOCK_LIFT, matrix[2][1] * reach)
