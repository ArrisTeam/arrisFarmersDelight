# -*- coding: utf-8 -*-
"""PotServeMath - 厨师的手在锅边动作用到的缓动和三维小算术（双端）

移植自 Hands-On Delight 的 client/KitchenMotions.java：smooth / out（76-85 行）、tipped（51-65 行：容器倾斜后某一点的位置）、LEAN。
向量一律是 (x, y, z) 元组，场景像素；角度是度（Java 的 Mth.DEG_TO_RAD 在这里换成 math.radians）。
"""
import math

LEAN = 16.0             # 立着的东西往后仰这么多度，镜头从上往下才看得见它们的面而不是边（KitchenMotions 31）
LIP_X = -0.3            # 容器的瓶口 / 杯沿：离中心 -0.3 个身长，倾向的那一侧（KitchenMotions 52）
LIP_Y = 0.36            # 瓶口在中心上方 0.36 个身长（KitchenMotions 53）
ITEM_DRAWN = 8.0        # 一件物品的显示在缩放 1 时画这么高（像素）：物品自己的 fixed 展示砍半（KitchenMotions 33）


def clamp01(t):
    return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)


def smooth(t):
    """KitchenMotions.smooth：smoothstep，t 夹进 0..1。"""
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def out(t):
    """KitchenMotions.out：开头快、收尾慢，1 - (1 - t) 的平方。"""
    t = clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mix(a, b, k):
    """Vector3f.lerp：a 朝 b 走 k。"""
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)


def rotateY(point, degrees):
    """JOML 的 Vector3f.rotateY：绕竖轴转（x' = x cos + z sin，z' = -x sin + z cos）。"""
    sin, cos = math.sin(math.radians(degrees)), math.cos(math.radians(degrees))
    return (point[0] * cos + point[2] * sin, point[1], -point[0] * sin + point[2] * cos)


def tipped(x, y, size, tilt, yaw):
    """KitchenMotions.tipped：直立的物品上一点 (x, y)（以身长为单位，离中心）在倾斜 tilt 度（绕 z）、往后仰 LEAN 度（绕 x）、
    再随镜头转 yaw 度（绕 y）之后的位置（离物品中心，像素）。"""
    px, py, pz = x * size, y * size, 0.0
    sin, cos = math.sin(math.radians(tilt)), math.cos(math.radians(tilt))              # rotateZ
    px, py = px * cos - py * sin, px * sin + py * cos
    sin, cos = math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))              # rotateX
    py, pz = py * cos - pz * sin, py * sin + pz * cos
    return rotateY((px, py, pz), yaw)


def pose(pos, rot, scale, visible=True, **extra):
    """一个节点此刻的样子：{"pos": (x, y, z) 场景像素, "rot": (x, y, z) 度, "scale": 缩放（物品的显示缩放，1 = ITEM_DRAWN 像素高）, "visible"}。"""
    result = {"pos": tuple(pos), "rot": tuple(rot), "scale": scale, "visible": visible}
    result.update(extra)
    return result
