# -*- coding: utf-8 -*-
# runner: both
"""砧板场景的几何（Shared/Rules/HandsOn/BoardScene.py）：机位、点得到的盒子、板上东西多大、躺多高、层摆在哪。

数从 HoD 的 scenes/cutting_board.json 和 BoardBehavior 的常量来；这里锁住它们，砧板站点（本人看到的）和 Client/BlockItems
（没开站时看到的）共用同一份，两边不会各改各的。
"""
from __future__ import print_function

import fdtest

Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")


def _close(a, b, eps=1.0e-9):
    return abs(a - b) < eps


def testTheCameraIsTheOneInTheJavaScene():
    assert Scene.CAMERA["pos"] == (7.5, 35.5, -21.0) and Scene.CAMERA["target"] == (7.5, 1.0, 8.0) and Scene.CAMERA["fov"] == 30.0
    assert Scene.FLIGHT_SECONDS == 0.4 and Scene.WORK_PLANE == 3.0


def testBothPickBoxesAreInsideTheBlockAndTheMouthIsAtLeastAsBigAsTheSurface():
    for lo, hi in (Scene.MOUTH, Scene.SURFACE):
        assert all(0.0 <= value <= 16.0 for value in lo + hi), (lo, hi)
        assert all(a < b for a, b in zip(lo, hi))
    assert all(m <= s for m, s in zip(Scene.MOUTH[0], Scene.SURFACE[0])) and all(m >= s for m, s in zip(Scene.MOUTH[1], Scene.SURFACE[1]))


def testItemsAreTenPixelsAndBlocksFivePointTwoAndTheScaleIsAnEighthOfThat():
    assert _close(Scene.itemScale(), 10.0 / 8.0) and _close(Scene.itemScale(True), 5.2 / 4.0), "方块的掉落物是立方体：缩放 1 棱长 4 像素"
    assert _close(Scene.scaleOf(8.0), 1.0) and _close(Scene.scaleOf(Scene.layerSize(0)), 1.25) and _close(Scene.scaleOf(Scene.layerSize(1)), 9.0 / 8.0)
    assert Scene.layerSize(0) == 10.0 and all(Scene.layerSize(index) == 9.0 for index in range(1, 9))


def testALoneItemLiesOnTheBoardAndAPileLiftsTheTopOne():
    assert Scene.pileLift(1) == 0.0 and Scene.pileLift(2) == Motion.PILE_LIFT == 0.65
    assert _close(Scene.surfaceHeight(1), 1.0 + 10.0 / 16.0), "单个图标：板面 + 10 / 16"
    assert _close(Scene.surfaceHeight(5) - Scene.surfaceHeight(1), 0.65), "一叠不止一个：顶面抬 0.65"
    assert _close(Scene.surfaceHeight(1, True), 1.0 + 5.2), "方块立着：板面 + 边长"
    assert _close(Scene.centerHeight(0.0), 1.0 + Scene.FLAT_LIFT) and _close(Scene.centerHeight(0.0, True), 1.0 + 2.6)


def testEachLayerIsOneStepHigherAndHasItsOwnFixedTurnAndOffset():
    poses = [Scene.layerPose(index) for index in range(9)]
    assert [pose["y"] for pose in poses] == [index * Motion.LAYER_STEP for index in range(9)]
    assert poses == [Scene.layerPose(index) for index in range(9)], "固定的：刷新、换人看都一样"
    assert len(set(round(pose["turn"], 6) for pose in poses)) > 6, "各层转的角度各不相同"
    assert poses[0]["turn"] == 0.0 and (poses[0]["x"], poses[0]["z"]) == Motion.layerJitter(0)


def testAnUprightThingsCentreIsHalfItsEdgeAboveItsBottom():
    assert _close(Scene.uprightLift(1.0), 4.0) and _close(Scene.uprightLift(0.65), 2.6)
    block = Scene.itemScale(True)
    pivot = Scene.blockLift(block) - block * Scene.SPRITE_SPAN / 2.0       # 道具把轴心放在"中心"下方半个贴图边长
    assert _close(pivot + Scene.CUBE_LIFT, Scene.BLOCK_SIZE / 2.0), "引擎把立方体画在轴心上方 3.2 像素：它的中心正好在面上方半个棱长"
    half = Scene.itemScale(True) * 0.5
    assert _close(Scene.blockLift(half) - half * Scene.SPRITE_SPAN / 2.0 + Scene.CUBE_LIFT, half * Scene.CUBE_SPAN / 2.0), "缩小了底面还贴着面"


def testTheCarvedToolIsPlantedAtTheJavaHeightAndTheKnifeTipPointsDown():
    assert _close(Scene.CARVED_Y, 0.23 * 16.0 - 1.01) and Scene.CARVED_SCALE == 0.6
    assert Scene.KNIFE_ROLL == 135.0 and Scene.KNIFE_TIP > 0.0
    assert _close(Scene.KNIFE_SCALE, 0.45 * 2.0), "刀画 0.45 个图标大：7.2 像素 = 缩放 0.9"
