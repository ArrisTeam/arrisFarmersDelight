# -*- coding: utf-8 -*-
# runner: both
"""叠在一件平躺的客户端掉落物朝上那面上的图标粒子（Shared/Rules/TopOverlay）：由掉落物的姿态矩阵、中心、缩放算出粒子的位置、SetRot 的三个角、
半边长；斜着的、扣着的不给；掉落物一动就收着，停稳 SETTLE 秒才亮。
约定：掉落物从正面看图标的右边是 M·(-1, 0, 0)、上边是 M·(0, 1, 0)、正面朝 M·(0, 0, -1)（前置包 CarryPose.shadowOf 的说明）；
粒子 emitter_transform_xz 的图标右 = E.x、上 = -E.z、法线 = E.y，SetRot((x, y, z)) 得 E = Rz(z)·Ry(y)·Rx(x)（Strata 引擎知识库）；
只转 y 的那一支实机核对过（Shared/Rules/ParticleQuad：上边转到 (-sin y, -cos y)、右边 (cos y, -sin y)）。"""
from __future__ import print_function

import math
import random

import fdtest

O = fdtest.load("Shared.Rules.TopOverlay")
ItemPose = fdtest.load("Shared.Rules.ItemPose")
PanPose = fdtest.load("Shared.Rules.PanPose")
Quad = fdtest.load("Shared.Rules.ParticleQuad")
CENTER = (10.5, 64.1, 7.25)


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def close(u, v, eps=1e-6):
    return all(near(a, b, eps) for a, b in zip(u, v))


def rx(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def ry(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def rz(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def column(m, j):
    return (m[0][j], m[1][j], m[2][j])


def emitter(rot):
    """SetRot((x, y, z)) 的发射器朝向：Rz(z)·Ry(y)·Rx(x)。"""
    return mul(mul(rz(rot[2]), ry(rot[1])), rx(rot[0]))


def angle(value):
    """角度夹到 (-180, 180]。"""
    value = math.fmod(value, 360.0)
    return value - 360.0 if value > 180.0 else (value + 360.0 if value <= -180.0 else value)


def testAFlatPieceGetsAQuadTurnedHalfARoundJustAboveItsTopFace():
    """平躺朝上（M = Ry(a)·Rx(90)，贴图的上边朝 (sin a, cos a)）：发射器只转 y，转 a + 180 度；粒子在中心正上方 lift(缩放) 像素；
    半边长是贴图边长 7.2 像素 x 缩放的一半。"""
    for yaw in (0.0, 12.0, 90.0, -35.5, 150.0, 181.0, 270.0):
        for scale in (0.694, 1.25):
            frame = O.frameOf(CENTER, ItemPose.lyingMatrix(yaw), scale)
            x, y, z = frame["rot"]
            assert x == 0.0 and z == 0.0 and near(angle(y - (yaw + 180.0)), 0.0, 0.051), (yaw, frame["rot"])
            assert close(frame["pos"], (CENTER[0], CENTER[1] + O.lift(scale) / 16.0, CENTER[2]))
            assert near(frame["half"], ItemPose.ITEM_SPAN * scale / 32.0)


def testTheQuadLiesExactlyOnTheItemsTopFaceAsTheVerifiedYawFormulaSays():
    """发射器的轴和掉落物的轴一一对上：E.x = 图标右、-E.z = 图标上、E.y = 正面；平躺时再按实机核对过的公式（ParticleQuad）看一遍：
    只转 y 的粒子上边在 (-sin y, -cos y)、右边在 (cos y, -sin y)，就是掉落物图标的上边、右边——同一张图，不镜像。"""
    for yaw in range(0, 360, 15):
        matrix = ItemPose.lyingMatrix(float(yaw))
        frame = O.frameOf(CENTER, matrix, 1.0)
        e = emitter(frame["rot"])
        right, up, front = [-v for v in column(matrix, 0)], column(matrix, 1), [-v for v in column(matrix, 2)]
        assert close(column(e, 0), right, 2e-3) and close([-v for v in column(e, 2)], up, 2e-3) and close(column(e, 1), front, 2e-3)
        psi = math.radians(frame["rot"][1])
        assert close((-math.sin(psi), -math.cos(psi)), (up[0], up[2]), 2e-3)
        assert close((math.cos(psi), -math.sin(psi)), (right[0], right[2]), 2e-3)
        assert near(angle(Quad.flatYaw(up[0], up[2]) - frame["rot"][1]), 0.0, 0.051), "和砧板的缝、虚线用的同一个偏航"


def testThePiecesOfARestingPanGetTheirQuadsThroughThePansOwnPose():
    """锅里停着的件（PanPose.lying + 锅的朝向换到世界、ItemPose.steadied 接着上一次的）：四个朝向、翻过奇数次（贴图在自己的平面里倒着）都给。"""
    for facing in ("north", "east", "south", "west"):
        for yaw in (-20.0, 13.2, 35.0):
            matrix = PanPose.toWorld(facing, PanPose.lying((0.0, yaw, 0.0)))
            flipped = ItemPose.steadied(matrix, [[-v for v in row] for row in matrix])
            for posed in (matrix, flipped):
                frame = O.frameOf(CENTER, posed, 1.04)
                assert frame is not None and frame["rot"][0] == 0.0 and frame["rot"][2] == 0.0
                e = emitter(frame["rot"])
                assert close(column(e, 0), [-v for v in column(posed, 0)], 1e-3) and close([-v for v in column(e, 2)], column(posed, 1), 1e-3)
            a, b = O.frameOf(CENTER, matrix, 1.04), O.frameOf(CENTER, flipped, 1.04)
            assert near(angle(a["rot"][1] - b["rot"][1] - 180.0), 0.0, 0.051), "翻过奇数次的那一块：同一块地方，粒子跟着转半圈"
            assert a["pos"] == b["pos"] and a["half"] == b["half"]


def testTiltedOrUpsideDownPiecesGetNoQuad():
    """只给平躺朝上的（正面和竖直差不到 FLAT_TILT 度）：颠起、翻面、落下的半路上斜着的不给，扣着的（正面朝下）不给。差一点点的照给，俯仰侧倾很小。"""
    flat = ItemPose.lyingMatrix(30.0)
    assert O.frameOf(CENTER, mul(rx(10.0), flat), 1.0) is None
    assert O.frameOf(CENTER, mul(rz(-30.0), flat), 1.0) is None
    assert O.frameOf(CENTER, ItemPose.lyingMatrix(30.0, pitch=180.0), 1.0) is None, "扣着"
    assert O.frameOf(CENTER, ItemPose.uprightMatrix(1.0, 0.0, 0.0), 1.0) is None, "立着"
    slight = O.frameOf(CENTER, mul(rx(0.5 * O.FLAT_TILT), flat), 1.0)
    assert slight is not None and abs(slight["rot"][0]) < O.FLAT_TILT and abs(slight["rot"][2]) < O.FLAT_TILT
    e = emitter(slight["rot"])
    assert close(column(e, 1), [-v for v in column(mul(rx(0.5 * O.FLAT_TILT), flat), 2)], 1e-3), "斜一点的照样贴着它的面"


def testTheEulerAnglesRebuildTheEmitterForAnyTurn():
    """emitterEuler：E -> (x, y, z)，Rz(z)·Ry(y)·Rx(x) 回到 E；只转 y 的给 (0, y, 0)（实机核对过的那一支），离它不远的转动俯仰、侧倾也小。"""
    rand = random.Random(11)
    for _ in range(200):
        e = mul(mul(ry(rand.uniform(-180, 180)), rx(rand.uniform(-180, 180))), rz(rand.uniform(-180, 180)))
        rot = O.emitterEuler(e)
        assert all(close(a, b, 1e-6) for a, b in zip(emitter(rot), e)), rot
    for psi in (0.0, 45.0, 90.0, 135.0, 179.0, -179.0, -90.0, 200.0):
        x, y, z = O.emitterEuler(ry(psi))
        assert (x, z) == (0.0, 0.0) and near(angle(y - psi), 0.0, 1e-6), (psi, x, y, z)
    x, y, z = O.emitterEuler(mul(ry(150.0), rx(1.0)))
    assert abs(x) < 2.0 and abs(z) < 2.0 and near(angle(y - 150.0), 0.0, 2.0), "接近只转 y 的取靠近它的那一组角"


def testTheQuadSitsAboveTheMeasuredTopFace():
    """掉落物有厚度：贴图逐像素挤出一个贴图像素厚、往正面那边挤（Strata 引擎知识库 ITEM_RENDER_ENGINE §3–§4），平躺朝上时顶面在中心平面上方
    7.2 / 16 像素 x 缩放。实机（2026-11-17，砧板上缩放 1.25 的平躺食物）：零厚度的虚线在中心上方 0.555 像素陷进去、0.655 露出来——顶面就在这中间；
    粒子要在它上面，但别浮得看得出来（1 像素以内）；跟着缩放走。"""
    assert near(O.TOP_FACE, 7.2 / 16.0) and 0.555 < O.TOP_FACE * 1.25 < 0.655
    assert 0.655 < O.lift(1.25) < 1.0
    assert O.lift(0.694) < O.lift(1.25) and near(O.lift(2.0) - O.lift(1.0), O.TOP_FACE)


def testAPieceMustStayStillForTwoTicksBeforeItsQuadShows():
    """掉落物的位置按游戏刻插值、晚到一两帧，粒子不晚：样子一变就收着，连着 SETTLE 秒（两个游戏刻）没变才亮；中途一动从头算。"""
    assert near(O.SETTLE, 0.1)
    still = O.Stillness()
    dt = 1.0 / 60.0
    assert still.step(dt, ("beef", (1.0, 2.0, 3.0), 1.0)) is False, "头一回见：刚到"
    frames = 1
    while not still.step(dt, ("beef", (1.0, 2.0, 3.0), 1.0)):
        frames += 1
        assert frames < 20
    assert 6 <= frames <= 7, frames
    assert still.step(dt, ("beef", (1.0, 2.0, 3.0), 1.0)) is True, "停着就一直亮着"
    assert still.step(dt, ("beef", (1.0, 2.01, 3.0), 1.0)) is False, "挪了一点：收着，从头算"
    assert still.step(0.05, ("beef", (1.0, 2.01, 3.0), 1.0)) is False and still.step(0.05, ("beef", (1.0, 2.01, 3.0), 1.0)) is True
    assert still.step(dt, ("beef", (1.0, 2.01, 3.0), 1.1)) is False, "大小变了也算动"
    assert still.step(0.2, ("pork", (1.0, 2.01, 3.0), 1.1)) is False, "换了东西：重新停一下"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
