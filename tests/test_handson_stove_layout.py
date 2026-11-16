# -*- coding: utf-8 -*-
# runner: both
"""StoveLayout / StoveLook（炉灶烤架上的件：位置、命中盒、朝向、点一下做什么、画生的还是熟的）。数字来自 Hands-On Delight 的
scenes/stove.json 和 client/StoveBehavior.java（placeOf 315-317、yaw 220-222、look 186-188、nearestFree 427-443、onEvent 353-362、
onItemClick 417-423、heat 273-282）。"""
from __future__ import print_function

import fdtest

L = fdtest.load("Shared.Rules.HandsOn.StoveLayout")
K = fdtest.load("Shared.Rules.HandsOn.StoveLook")


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def testTheSixPlacesAreTwoRowsOfThreeAsTheSceneHasThem():
    assert L.PLACES == 6 and len(L.PIECE_AT) == 6
    for place in range(6):
        x, y, z = L.placeOf(place)
        assert (x, z) == ((12.8 if place % 3 == 0 else 8.0 if place % 3 == 1 else 3.2), (11.2 if place < 3 else 4.8)), place
        near(y, 16.02)
    assert L.PIECE_AT[0] == (12.8, 11.2) and L.PIECE_AT[5] == (3.2, 4.8), "stove.json 的 piece_0 / piece_5"


def testAPieceHasTheScenesHitBoxAroundItself():
    lo, hi = L.pieceBox(0)
    assert tuple(round(v, 6) for v in lo) == (10.4, 15.82, 8.6) and tuple(round(v, 6) for v in hi) == (15.2, 17.62, 13.8)
    lo, hi = L.pieceBox(4)
    assert tuple(round(v, 6) for v in lo) == (5.6, 15.82, 2.2) and tuple(round(v, 6) for v in hi) == (10.4, 17.62, 7.4)
    assert L.MOUTH_BOX == ((1.0, 15.8, 1.0), (15.0, 16.2, 15.0)), "拿着东西时整个烤架面"
    assert L.GRILL_BOX[1][1] < L.pieceBox(0)[1][1], "件的盒子比烤架面的薄板高：点在件上点到件"


def testTheCameraIsTheScenes():
    assert L.CAMERA["pos"] == (8.0, 50.5, -21.0) and L.CAMERA["target"] == (8.0, 16.0, 8.0) and L.CAMERA["fov"] == 30.0
    assert L.WORK_PLANE == 17.0


def testNoTwoPiecesLieTheSameWay():
    yaws = [L.yawOf(place) for place in range(6)]
    assert yaws == [-30.0, -21.0, -12.0, -3.0, 6.0, 15.0] and len(set(yaws)) == 6
    assert all(-30.0 <= yaw <= 30.0 for yaw in yaws)


def testTheWorldShowsThePiecesWhereTheSceneHasThem():
    fractions = L.blockFractions()
    assert fractions[0] == (0.8, 0.7) and fractions[2] == (0.2, 0.7) and fractions[4] == (0.5, 0.3)
    assert all(0.0 < x < 1.0 and 0.0 < z < 1.0 for x, z in fractions)


def testTheFreePlaceNearestTheCursor():
    centers = [(x, z) for x, _, z in (L.placeOf(i) for i in range(6))]
    free = [True] * 6
    assert L.nearestFree((12.0, 10.0), centers, free) == 0
    assert L.nearestFree((3.0, 5.0), centers, free) == 5
    assert L.nearestFree((8.0, 8.0), centers, free) == 1, "正中到一排三件的距离差不多：取先到的（严格小于才换）"
    free[0] = False
    assert L.nearestFree((12.0, 10.0), centers, free) == 1, "占了的不算"
    assert L.nearestFree((12.0, 10.0), centers, [False] * 6) == -1
    assert L.nearestFree(None, centers, [False, False, True, True, False, True]) == 2, "没有光标：最靠前的空位"


def testClickingAPieceTurnsItOrTakesItBack():
    assert L.pieceClick(0, False, 5.0) == L.TURN
    assert L.pieceClick(1, False, 5.0) == L.TAKE, "右键：取回，生的、半熟的也行，重来"
    assert L.pieceClick(0, True, 5.0) == L.TAKE, "烤好的：左键也是取"
    assert L.pieceClick(1, True, 5.0) == L.TAKE
    assert L.pieceClick(0, False, 0.35) is None, "离上次翻不到 FLIGHT + 0.05 秒：还在空中"
    assert L.pieceClick(0, False, 0.36) == L.TURN
    assert L.pieceClick(0, True, 0.0) == L.TAKE, "烤好的不看翻面的间隔"


def testAStackOnTheGrillGoesOnEverywhereOrOnTheNearestPlace():
    assert L.placeRequest(0, 3) == {}, "左键：每个空位一件"
    assert L.placeRequest(1, 3) == {"one": True, "place": 3}, "右键：离光标最近的空位那一个"
    assert L.placeRequest(1, -1) == {"one": True, "place": -1}


def testTheTopOfAPieceIsRawUntilItIsDone():
    assert K.look(-1.0) == -1 and K.look(0.0) == 0 and K.look(1.0) == 100 and K.look(1.5) == 100
    assert K.look(0.08) == 0 and K.look(0.09) == 1 and K.look(0.5) == 6 and K.look(0.999) == 11
    assert K.shownName("minecraft:beef", "minecraft:cooked_beef", 0.0) == "minecraft:beef"
    assert K.shownName("minecraft:beef", "minecraft:cooked_beef", 0.99) == "minecraft:beef"
    assert K.shownName("minecraft:beef", "minecraft:cooked_beef", 1.0) == "minecraft:cooked_beef", "翻过来朝上那面是熟的：画熟的"
    assert K.shownName("minecraft:cooked_beef", "minecraft:cooked_beef", 0.0) == "minecraft:cooked_beef", "烤好的本来就是熟的"
    assert K.shownName("minecraft:egg", "arris:fried_egg", 0.0, True) == "arris:egg_look_0", "FD 原样放上去的蛋：不连壳画，蛋清是灰的"
    assert K.shownName("minecraft:egg", "arris:fried_egg", 0.5, True) == "arris:egg_look_1"
    assert K.shownName("minecraft:egg", "arris:fried_egg", 1.0, True) == "arris:fried_egg"


def testAPieceWaitsOnlyWhenItsUnderSideIsDoneAndItWasLaidByHand():
    assert K.waits(True, 1.0, 0.0) and not K.waits(True, 0.5, 0.0) and not K.waits(True, 1.0, 1.0)
    assert not K.waits(False, 1.0, 0.0), "FD 原样烤的不等翻"


def testPiecesAreToldApartIntoCookingAndWaiting():
    pieces = [(True, 0.3, 0.0), (True, 1.0, 0.0), None, (False, 0.0, 0.0), (True, 1.0, 0.0), (True, 0.2, 0.0)]
    turned = [-10.0] * 6
    assert K.sortHeat(pieces, 5.0, turned) == ([0, 3, 5], [1, 4])
    turned[1] = 4.8
    assert K.sortHeat(pieces, 5.0, turned) == ([0, 3, 5], [4]), "刚翻过（不到 0.3 秒）的还在空中：两组都不算"
    assert K.sortHeat(pieces, 5.2, turned) == ([0, 3, 5], [1, 4]), "落下了"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
