# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点的手势（Compat/Diegesis/PanGesture.py）：往上一甩 = 颠锅，点一下 = 取出，按住慢挪什么都不是。"""
from __future__ import print_function

import fdtest

PanGesture = fdtest.load("Compat.Diegesis.PanGesture")


def _drag(gesture, points, start=0.0, step=1.0 / 30.0):
    """按住、依次挪到 points、松手；返回 (每次颠锅的力度, 松手时是不是"点")。"""
    gesture.press(points[0], start)
    tosses, now = [], start
    for point in points[1:]:
        now += step
        force = gesture.move(point, now)
        if force is not None:
            tosses.append(force)
    return tosses, gesture.release(points[-1], now + step)


def testAFlickUpTosses():
    tosses, clicked = _drag(PanGesture.PanGesture(), [(300.0, 200.0 - 6.0 * i) for i in range(6)])
    assert len(tosses) == 1 and 0.3 <= tosses[0] <= 1.0, tosses
    assert not clicked, "甩过的那一按不算点"


def testAHardFlickIsAFullToss():
    tosses, _ = _drag(PanGesture.PanGesture(), [(300.0, 200.0), (300.0, 120.0)])
    assert tosses == [1.0]


def testATapTakes():
    gesture = PanGesture.PanGesture()
    gesture.press((300.0, 200.0), 0.0)
    assert gesture.release((301.0, 200.0), 0.1)
    gesture.press((300.0, 200.0), 1.0)
    assert not gesture.release((300.0, 200.0), 1.6), "按太久不算点"


def testDraggingSidewaysOrSlowlyDoesNothing():
    tosses, clicked = _drag(PanGesture.PanGesture(), [(300.0 + 10.0 * i, 200.0) for i in range(8)])
    assert tosses == [] and not clicked
    slow = PanGesture.PanGesture()
    tosses, clicked = _drag(slow, [(300.0, 200.0 - 1.0 * i) for i in range(60)])
    assert tosses == [], "慢慢往上挪（一秒 30 单位、0.3 秒的窗口里只有 9）不是甩"


def testHoldThenFlickStillTossesAndTwiceInOnePress():
    gesture = PanGesture.PanGesture()
    points = [(300.0, 200.0)] * 30 + [(300.0, 200.0 - 7.0 * i) for i in range(1, 5)]
    points += [points[-1]] * 30 + [(300.0, points[-1][1] - 7.0 * i) for i in range(1, 5)]
    tosses, clicked = _drag(gesture, points)
    assert len(tosses) == 2 and not clicked, tosses


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
