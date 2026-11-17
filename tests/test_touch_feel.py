# -*- coding: utf-8 -*-
# runner: both
"""站点表现里触屏的手感（Compat/Diegesis/TouchFeel.py）：问前置包的 view.buzz / view.doubleSeconds，老版本的前置包没有就算了；
种类名和前置包的 Shared/Haptics 对得上；触屏的拖动门槛和容器库（dolorContainer）抄的原版值是同一个数。
各站点在哪调、调了什么，在各自的 test_*_view.py 里。"""
from __future__ import print_function

import dgtest
import fdtest

Feel = fdtest.load("Compat.Diegesis.TouchFeel")
Haptics = dgtest.load("Shared.Haptics")
Input = dgtest.load("Shared.Input")
Gestures = fdtest.load("dolorContainer.Client.Gestures")


class Old(object):
    """老版本前置包的视图：没有 buzz / doubleSeconds。"""


class New(object):
    def __init__(self):
        self.buzzes = []

    def buzz(self, kind):
        self.buzzes.append(kind)

    def doubleSeconds(self):
        return 0.4


def testTheKindsAreTheKernelsKindsAndEveryOneHasADuration():
    assert (Feel.PICK, Feel.PUT, Feel.CUT, Feel.FLIP, Feel.REFUSE) == (Haptics.PICK, Haptics.PUT, Haptics.CUT, Haptics.FLIP, Haptics.REFUSE)
    assert set(Haptics.BUZZ_MS) == set((Feel.PICK, Feel.PUT, Feel.CUT, Feel.FLIP, Feel.REFUSE)), "表里的种类和这边用的一一对上"
    assert set(Feel.SETTLED.values()) <= set(Haptics.BUZZ_MS)


def testBuzzAsksTheViewAndDoesNothingOnAnOldKernel():
    view = New()
    Feel.buzz(view, Feel.CUT)
    assert view.buzzes == ["cut"]
    Feel.buzz(Old(), Feel.CUT)


def testTheDoubleClickWindowIsTheViewsOrTheCallersDefault():
    assert Feel.doubleClick(New(), 0.25) == 0.4
    assert Feel.doubleClick(Old(), 0.25) == 0.25


def testOnlyThePlacedAndRefusedResultsBuzzThroughTheSceneAndOnlyWhileTheStationIsOpen():
    kinds = []
    for name in ("placed", "refused", "tossed", "turned", "taken", "fried", "grilled"):
        Feel.settled(kinds.append, name)
    assert kinds == ["put", "refuse"], "别人的动作、烤好煎好不是本人的手"
    Feel.settled(None, "placed")


def testTheTouchSlopIsTheContainerLibrarysTouchDragDistanceInScreenPixels():
    """内核的触屏拖动门槛是 dolorContainer 抄原版的 TOUCH_SCROLL_PIXELS（35.4 个屏幕像素），换成界面单位用；两处别各改各的。"""
    assert Input.TOUCH_DRAG_SCREEN_PIXELS == Gestures.TOUCH_SCROLL_PIXELS == 35.4


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
