# -*- coding: utf-8 -*-
"""PotSpoonPose - 厨锅勺子的姿势数学：倾斜、旋转矩阵、节点偏移、穿过液面的点、拾取盒（双端，纯函数）

移植自 Hands-On Delight：client/PotBehavior.java 的 pose（1375-1392）与 cooking_pot.json 的 ladle 节点（46-64）。
坐标是"锅局部"：原点在锅底中心（站点里的 (8, 0, 8)），x、z 是锅模型自己的轴，y 向上，单位 px；勺子在静止时手柄朝 +x 歪 22.5 度，
勺尖（模型里勺子的转轴）在锅心、离锅底 3 px。站点（场景）坐标 = 锅局部绕 y 转 turn 度（JOML rotationY：x' = x cos + z sin，
z' = -x sin + z cos；turn = 场景朝向 - 方块朝向，PotBehavior.turnToBlock 1271-1289）再加 (8, 0, 8)。矩阵是 3x3 行主序的 9 元 list。
"""
import math

REST_LEAN = 22.5             # 静止时手柄朝 +x 歪的角度，度（Shape.COOKING_POT.lean，PotBehavior.java:58；酒瓶锅是 -22.5）
STIR_LEAN = 7.0              # 握在手里时，勺尖在最远处手柄最多歪这么多，度（PotBehavior.java:148）
SPOON_END = 3.0              # 勺尖（转轴）离锅底的高度，px（Shape.spoonEnd，58 行）
SPOON_REACH = 2.3            # 勺尖离锅心最远，px（PotBehavior.java:146）
PICK_LO = (2.6, 11.5, -1.5)  # 手柄的拾取盒（节点自己的空间，静止时就是锅局部），px（cooking_pot.json:52-63）
PICK_HI = (6.6, 16.0, 1.5)


def restSlope(restLean=REST_LEAN):
    """静止时手柄每升高 1 px 往 +x 偏多少：tan(restLean)（PotBehavior.java:1377）。22.5 度 -> 0.41421。"""
    return math.tan(math.radians(restLean))


def leanSlopes(tipX, tipZ, grip, restLean=REST_LEAN, reach=SPOON_REACH):
    """手柄每升高 1 px 往 x、z 偏多少 (leanX, leanZ)：静止时 (tan 22.5, 0)，握在手里是勺尖偏移 * tan(7 度) / reach，按 grip 混合。

    tipX、tipZ：勺尖离锅心的偏移，px；grip：0 靠着，1 在汤里。对应 PotBehavior.java:1377-1380（lerp(grip, rest, tip * held)）。
    """
    rest = restSlope(restLean)
    held = math.tan(math.radians(STIR_LEAN)) / reach
    return rest + grip * (tipX * held - rest), grip * (tipZ * held)


def alignMatrix(m, fx, fy, fz, tx, ty, tz):
    """把单位向量 f 转到单位向量 t 的最短弧旋转，写进 m（9 元行主序）并返回 m。等同 JOML Quaternionf.rotationTo（PotBehavior.java:1382）。

    Rodrigues：R = I + K + K^2 / (1 + f.t)，K 是 f x t 的叉乘矩阵。f、t 几乎反向时（手柄不会）绕一根与 f 垂直的轴转半圈。
    """
    dot = fx * tx + fy * ty + fz * tz
    if dot < -1.0 + 1.0e-6:
        ax, ay, az = (0.0, -fz, fy) if abs(fx) < 0.9 else (-fz, 0.0, fx)
        norm = math.sqrt(ax * ax + ay * ay + az * az)
        ax, ay, az = ax / norm, ay / norm, az / norm
        m[0], m[1], m[2] = 2 * ax * ax - 1, 2 * ax * ay, 2 * ax * az
        m[3], m[4], m[5] = 2 * ax * ay, 2 * ay * ay - 1, 2 * ay * az
        m[6], m[7], m[8] = 2 * ax * az, 2 * ay * az, 2 * az * az - 1
        return m
    vx, vy, vz = fy * tz - fz * ty, fz * tx - fx * tz, fx * ty - fy * tx
    s2 = vx * vx + vy * vy + vz * vz
    k = 1.0 / (1.0 + dot)
    m[0], m[1], m[2] = 1.0 + k * (vx * vx - s2), -vz + k * vx * vy, vy + k * vx * vz
    m[3], m[4], m[5] = vz + k * vx * vy, 1.0 + k * (vy * vy - s2), -vx + k * vy * vz
    m[6], m[7], m[8] = -vy + k * vx * vz, vx + k * vy * vz, 1.0 + k * (vz * vz - s2)
    return m


def eulerYXZ(m):
    """旋转矩阵（9 元行主序，R = Ry * Rx * Rz）的欧拉角 (x 俯仰, y 偏航, z 翻滚)，度。节点 rotateTo(x, y, z) 吃的就是它。

    对应 JOML Quaternionf.getEulerAnglesYXZ（PotBehavior.java:1383）：x = asin(-R12)，y = atan2(R02, R22)，z = atan2(R10, R11)。
    """
    sine = max(-1.0, min(1.0, -m[5]))
    return (math.degrees(math.asin(sine)) + 0.0, math.degrees(math.atan2(m[2], m[8])) + 0.0, math.degrees(math.atan2(m[3], m[4])) + 0.0)


def nodeOffset(m, tipX, tipZ, spoonEnd=SPOON_END):
    """勺子节点要平移的量 (x, y, z)，px：转完之后勺尖（模型里 (0, spoonEnd, 0) 那点）正好落在 (tipX, spoonEnd, tipZ)。

    节点的矩阵 = 平移(这个量) * 旋转(m)。对应 PotBehavior.java:1384-1385：moveTo(tip - R * (0, spoonEnd, 0))。
    """
    return (tipX - m[1] * spoonEnd, spoonEnd - m[4] * spoonEnd, tipZ - m[7] * spoonEnd)


def toScene(x, z, turn):
    """锅局部 (x, z) -> 场景里相对锅心的 (x, z)：绕 y 转 turn 度。turn = 0 时不变。"""
    c = math.cos(math.radians(turn))
    s = math.sin(math.radians(turn))
    return (x * c + z * s, -x * s + z * c)


def toLocal(x, z, turn):
    """toScene 的逆：场景里相对锅心的 (x, z) -> 锅局部（光标点要先换成它再交给勺子）。"""
    c = math.cos(math.radians(turn))
    s = math.sin(math.radians(turn))
    return (x * c - z * s, x * s + z * c)


def throughPoint(tipX, tipZ, leanX, leanZ, surfaceY, turn=0.0, spoonEnd=SPOON_END):
    """手柄穿过液面的点 (x, z)，场景里相对锅心，px：浮着的料绕着它走。对应 PotBehavior.java:1388-1391。

    手柄从勺尖往上每升 1 px 偏 (leanX, leanZ)，液面比勺尖高 surfaceY - spoonEnd。
    """
    height = surfaceY - spoonEnd
    return toScene(tipX + leanX * height, tipZ + leanZ * height, turn)


def pickMatrix(m, offset):
    """勺子节点 -> 锅局部的 3x4 列主序矩阵（12 元，下标 = 列 * 3 + 行，p' = M p，最后一行 (0,0,0,1) 不存）：旋转 m 加平移 offset。

    与 PICK_LO / PICK_HI 一起就是手柄的拾取盒（定向盒）：静止时是单位矩阵，盒子就是 [2.6,11.5,-1.5]-[6.6,16,1.5]。
    """
    return [m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8], offset[0], offset[1], offset[2]]


def pickAabb(m, offset):
    """手柄拾取盒在锅局部的轴对齐包围盒 ((x0, y0, z0), (x1, y1, z1))，px；倾斜时比定向盒略胖，要精确请用 pickMatrix。"""
    lo = [1.0e30, 1.0e30, 1.0e30]
    hi = [-1.0e30, -1.0e30, -1.0e30]
    for cx in (PICK_LO[0], PICK_HI[0]):
        for cy in (PICK_LO[1], PICK_HI[1]):
            for cz in (PICK_LO[2], PICK_HI[2]):
                for axis in (0, 1, 2):
                    value = m[axis * 3] * cx + m[axis * 3 + 1] * cy + m[axis * 3 + 2] * cz + offset[axis]
                    lo[axis] = min(lo[axis], value)
                    hi[axis] = max(hi[axis], value)
    return (tuple(lo), tuple(hi))
