# -*- coding: utf-8 -*-
# runner: both
"""煎锅里的食物摆法（Shared/Rules/HandsOn/PanLayout.py）：数值照 Hands-On Delight 的 SkilletBehavior（place / size / yaw / look / counts / height）。"""
from __future__ import print_function

import fdtest

Layout = fdtest.load("Shared.Rules.HandsOn.PanLayout")


def testHowManyPiecesAreDrawn():
    counts = Layout.counts
    assert counts(0) == (0, 0, 0) and counts(-3) == (0, 0, 0), "空锅什么都不画"
    assert counts(1) == (1, 1, 0) and counts(4) == (4, 4, 0)
    assert counts(5) == (5, 4, 1), "多出来的垫在下面"
    assert counts(8) == (8, 4, 4) and counts(16) == (16, 4, 4), "一批 16 个只画 8 块"
    assert counts(40) == (16, 4, 4), "一批最多 16 件（FD 右键放进来的一大叠也只算 16 件煎）"


def testPieceSizeShrinksAsTheyCrowd():
    size = Layout.size
    assert size(0) == 9.0 and size(1) == 9.0 and size(2) == 7.5 and size(3) == 6.5 and size(4) == 6.5


def testWhereEachPieceLies():
    place = Layout.place
    assert place(0, 1) == (0.0, 0.0)
    assert place(0, 2) == (2.6, 0.4) and place(1, 2) == (-2.6, -0.4)
    assert [place(i, 3) for i in range(3)] == [(2.8, 2.2), (-2.8, 2.0), (0.2, -2.8)]
    assert [place(i, 4) for i in range(4)] == [(2.9, 2.9), (-2.9, 2.7), (2.7, -2.9), (-2.8, -2.8)]
    assert [place(i, 9) for i in range(4)] == [place(i, 4) for i in range(4)], "再多也是四个位置"


def testAPieceStillLandingWhenThePanHoldsLessLiesAtTheLastPlace():
    assert Layout.place(3, 2) == Layout.place(1, 2), "下标夹到最后一个位置"
    assert Layout.place(5, 4) == Layout.place(3, 4)
    assert Layout.place(0, 0) == (2.9, 2.9), "Java 的 switch 缺省分支：锅空着时问位置，是四块那一套的第一个"


def testEachPieceKeepsItsOwnTurn():
    turns = [Layout.yaw(i, False) for i in range(4)]
    for got, want in zip(turns, [-24.0, -16.8, -9.6, -2.4]):
        assert abs(got - want) < 1e-9, turns
    assert abs(Layout.yaw(0, True) - 11.0) < 1e-9, "垫在下面的再转 35 度"
    for i in range(8):
        assert abs(Layout.yaw(i, True) - Layout.yaw(i, False) - 35.0) < 1e-9
    assert Layout.yaw(7, False) == Layout.yaw(7, False), "每次一样，不会一刷新就跳"


def testHowDoneTheTopLooksInTwelveSteps():
    look = Layout.look
    assert look(-1.0) == -1 and look(0.0) == 0 and look(0.08) == 0 and look(0.09) == 1
    assert look(0.45) == 5 and look(0.99) == 11 and look(1.0) == 100 and look(1.5) == 100


def testLyingHeightRaisesTheTopWhenSomethingIsUnderIt():
    assert Layout.height(False, 0) == 0.0
    assert abs(Layout.height(False, 2) - 0.6) < 1e-9, "垫了东西，上面的抬 PILE"
    assert Layout.height(True, 2) == 0.0
    assert Layout.height(False, 0, flat=False) == 4.0, "没有图标的方块物品竖在中心上，再高 4"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
