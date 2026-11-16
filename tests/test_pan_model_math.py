# -*- coding: utf-8 -*-
# runner: both
"""煎锅方块实体模型的坐标换算（Shared/Rules/PanModelMath.py）：场景坐标（JE：锅柄朝 +z、镜头在锅柄那一侧）、锅自己的坐标、世界，
锅（pan 骨骼）和油膜（oil 骨骼）的动画通道。"""
from __future__ import print_function

import fdtest

Math = fdtest.load("Shared.Rules.PanModelMath")
Pot = fdtest.load("Shared.Rules.PotModelMath")
POS = (10, 64, -3)
FACINGS = (Pot.NORTH, Pot.EAST, Pot.SOUTH, Pot.WEST)


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def nearAll(a, b, eps=1e-6):
    return all(near(x, y, eps) for x, y in zip(a, b)) and len(a) == len(b)


def testSceneAndLocalAreAHalfTurnApart():
    assert Math.sceneToLocal(8.0, 3.0, 27.0) == (8.0, 3.0, -11.0), "锅柄尖 z = 27 在锅自己的坐标里是 -11（模型的正面一侧）"
    for point in ((0.0, 1.0, 2.0), (15.5, 7.0, 3.25)):
        assert Math.sceneToLocal(*Math.sceneToLocal(*point)) == point


def testTheHandlePointsWhereTheBlockFaces():
    for facing in FACINGS:
        centre = Math.worldPoint(facing, POS, (8.0, 0.0, 8.0))
        assert nearAll(centre, (POS[0] + 0.5, POS[1], POS[2] + 0.5)), "锅心在方块中心"
        tip = Math.worldPoint(facing, POS, (8.0, 0.0, 27.0))
        dx, dz = Math.handleSide(facing)
        assert nearAll((tip[0] - centre[0], tip[2] - centre[2]), (dx * 19.0 / 16.0, dz * 19.0 / 16.0)), facing
    assert Math.handleSide(Pot.SOUTH) == (0.0, 1.0), "玩家站在方块南边放下：aux 0 = 南，锅柄朝玩家"


def testWorldAndSceneAreInverse():
    for facing in FACINGS:
        for point in ((8.0, 0.0, 8.0), (2.0, 5.0, 20.0), (14.0, 1.0, -3.0)):
            world = Math.worldPoint(facing, POS, point)
            assert nearAll(Math.scenePoint(facing, POS, *world), point), (facing, point)


def testTheYawTurnsSceneDirectionsIntoWorldOnes():
    for facing in FACINGS:
        yaw = Math.worldYaw(facing)
        # 场景里朝镜头（+z）的方向转 yaw 度，要正好是锅柄朝的方向（PotServeMath.rotateY 的约定）
        import math
        x, z = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        assert nearAll((x, z), Math.handleSide(facing)), (facing, yaw)
    assert Math.worldYaw(Pot.SOUTH) == 0.0 and Math.worldYaw(Pot.NORTH) == 180.0


def testThePanBoneChannelsFollowTheSceneMotion():
    position, rotation = Math.panBone(11.0, (0.0, 1.2, 0.9))
    assert nearAll(position, (0.0, 1.2, -0.9)), "往厨师（锅柄）这一侧 0.9 像素：模型里锅柄在 -z，所以是 -0.9"
    assert nearAll(rotation, (11.0, 0.0, 0.0))
    assert nearAll(Math.panBone(0.0, (0.0, 0.0, 0.0))[0], (0.0, 0.0, 0.0)) and nearAll(Math.panBone(0.0, (0.0, 0.0, 0.0))[1], (0.0, 0.0, 0.0))


def testTheOilBoneMovesWithTheScenePuddle():
    assert nearAll(Math.oilBone(2.6, 0.4), (2.6, 0.0, -0.4))
    assert nearAll(Math.oilBone(0.0, 0.0), (0.0, 0.0, 0.0))


def testTheSceneBoxesAreJavas():
    assert Math.HANDLE_BOX == ((6.0, 0.5, 14.5), (10.0, 4.0, 27.5)), "handle 的碰撞盒 [-2, 0.5, 6.5] ~ [2, 4, 19.5] 加上锅在 (8, 0, 8)"
    assert Math.MOUTH_BOX == ((1.0, 0.0, 1.0), (15.0, 6.0, 15.0)) and Math.FOOD_BOX == ((1.5, 0.0, 1.5), (14.5, 5.0, 14.5))
    assert Math.SCENE_CAMERA == {"pos": (8.0, 40.0, 50.0), "target": (8.0, 1.0, 14.0), "fov": 34.0}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
