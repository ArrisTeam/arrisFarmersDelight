# -*- coding: utf-8 -*-
# runner: both
"""FromPlayer（东西从屏幕底边飞到站点里）与 KitchenLooks（煎着的东西朝上那面的颜色）。数字来自 Hands-On Delight 的
client/FromPlayer.java（15-38）和 client/KitchenLooks.java（25-27、78-110）。"""
from __future__ import print_function

import math

import fdtest

F = fdtest.load("Shared.Rules.HandsOn.FromPlayer")
K = fdtest.load("Shared.Rules.HandsOn.KitchenLooks")
L = fdtest.load("Shared.Rules.HandsOn.StoveLayout")


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def camera_ray(camera, fx, fy, aspect=16.0 / 9.0):
    """针孔相机：屏幕宽、高的比例 (fx, fy)（左上角是 0, 0）-> 站点射线。垂直视野 fov 度。"""
    px, py, pz = camera["pos"]
    tx, ty, tz = camera["target"]
    fwd = (tx - px, ty - py, tz - pz)
    n = math.sqrt(sum(v * v for v in fwd))
    fwd = tuple(v / n for v in fwd)
    right = (-fwd[2], 0.0, fwd[0])                     # 看向 +z 时，屏幕右边是 -x
    rn = math.sqrt(right[0] ** 2 + right[2] ** 2)
    right = (right[0] / rn, 0.0, right[2] / rn)
    up = (right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])
    half = math.tan(math.radians(camera["fov"]) / 2.0)
    x, y = (fx * 2.0 - 1.0) * half * aspect, (1.0 - fy * 2.0) * half
    d = tuple(fwd[i] + right[i] * x + up[i] * y for i in range(3))
    return (px, py, pz, d[0], d[1], d[2])


def testTheStartsLieInARowAlongTheBottomOfTheScreen():
    assert F.startAt(0, 1) == (0.5, 0.97)
    xs = [F.startAt(i, 3)[0] for i in range(3)]
    near(xs[0], 0.45), near(xs[1], 0.5), near(xs[2], 0.55)
    xs = [F.startAt(i, 2)[0] for i in range(2)]
    near(xs[0], 0.475), near(xs[1], 0.525)
    assert all(F.startAt(i, 6)[1] == 0.97 for i in range(6))
    near(F.startAt(5, 6)[0] - F.startAt(0, 6)[0], 0.25)


def testTheOffsetIsTheHorizontalGapBetweenTheStartAndTheMiddleOfTheScreen():
    assert F.offsetOf(None, (1.0, 4.0, 2.0)) == (0.0, 0.0), "旁观的人没有屏幕：从正上方落下"
    assert F.offsetOf((1.0, 4.0, 2.0), None) == (0.0, 0.0)
    assert F.offsetOf((3.0, 4.0, 5.0), (1.0, 4.0, 2.0)) == (2.0, 3.0), "y 不算"


def testAPlaneCutsTheRayWhereItShould():
    assert F.planeAt((0.0, 10.0, 0.0, 0.0, -1.0, 1.0), 4.0) == (0.0, 4.0, 6.0)
    assert F.planeAt((0.0, 10.0, 0.0, 1.0, 0.0, 1.0), 4.0) is None, "平行"
    assert F.planeAt((0.0, 10.0, 0.0, 0.0, 1.0, 1.0), 4.0) is None, "朝上：在身后"


def testThePiecesComeInFromTheCameraSideOfTheirPlaces():
    """炉灶的机位：屏幕底边那一点投到 y = 4 的面上，比屏幕正中那一点离相机近十几个像素（-z），左右一样。"""
    middle = F.planeAt(camera_ray(L.CAMERA, 0.5, 0.5), 4.0)
    for index, count in ((0, 1), (0, 3), (1, 3), (2, 3)):
        fx, fy = F.startAt(index, count)
        offset = F.offsetOf(F.planeAt(camera_ray(L.CAMERA, fx, fy), 4.0), middle)
        assert -19.0 < offset[1] < -14.0, offset
        if count == 1 or index == 1:
            near(offset[0], 0.0, 1.0e-9)
    left, right = (F.offsetOf(F.planeAt(camera_ray(L.CAMERA, *F.startAt(i, 3)), 4.0), middle)[0] for i in (0, 2))
    assert left > 0.0 > right, "第一件在屏幕左边 = +x（站点里 +x 在画面左边）"


def testMixingColoursGoesChannelByChannel():
    assert K.mix(0xFF000000, 0xFFFFFFFF, 0.0) == 0xFF000000 and K.mix(0xFF000000, 0xFFFFFFFF, 1.0) == 0xFFFFFFFF
    assert K.mix(0x00000000, 0xFFFFFFFF, 0.5) == 0x80808080, "四个通道都算，包括透明度：127.5 进成 128"
    assert K.mix(0xFF102030, 0xFF304050, 0.5) == 0xFF203040


def testAnEggsWhiteClearsFromSeeThroughToWhiteAndNeverGoesBrown():
    assert K.fryingTint(0, 0, True, False, 0.0) == K.RAW_EGG == 0xC8E6E2D8
    assert K.fryingTint(0, 0, True, False, 0.5) == K.mix(K.RAW_EGG, 0xFFFFFFFF, 0.5)
    assert K.fryingTint(0, 0, True, False, 1.0) == 0xFFFFFFFF, "熟了：原样画熟的图"
    assert K.fryingTint(0, 0, True, False, -1.0) == K.RAW_EGG, "没有数据按 0 算"


def testFoodGoesFromItsRawColoursTowardsTheCookedOnesAndMeatSears():
    raw, cooked = 0xFFB05040, 0xFF603020
    assert K.fryingTint(raw, cooked, False, False, 1.0) == 0xFFFFFFFF
    assert K.fryingTint(raw, cooked, False, False, 0.0) == 0xFFFFFFFF, "朝上那面一点没烤：不染"
    target = K.mix(0xFFFFFFFF, 0xFF8B9980, 0.5 * K.SEAR)
    assert K.fryingTint(raw, cooked, False, False, 0.5) == target
    channels = [(target >> shift) & 0xFF for shift in (16, 8, 0)]
    assert channels == [round(255 + (0x8B - 255) * 0.35), round(255 + (0x99 - 255) * 0.35), round(255 + (0x80 - 255) * 0.35)]
    seared = K.fryingTint(raw, cooked, False, True, 0.5)
    assert seared == K.mix(0xFFFFFFFF, K.mix(0xFF8B9980, K.SEARED, 0.4), 0.5 * K.SEAR), "肉和鱼的目标色先往焦色走 4 成"
    assert seared != target
    capped = K.fryingTint(0xFF204020, 0xFF402010, False, False, 0.5)
    assert capped == K.mix(0xFFFFFFFF, 0xFFFF8080, 0.35), "熟的比生的亮的通道封顶在 255（不会超），暗的通道取比例"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
