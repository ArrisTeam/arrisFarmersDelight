# -*- coding: utf-8 -*-
# runner: both
"""站点表现里触屏的手感（Compat/Diegesis/TouchFeel.py）：问前置包的 view.doubleSeconds，老版本的前置包没有就算了；
触屏的拖动门槛和容器库（dolorContainer）抄的原版值是同一个数。各站点在哪调，在各自的 test_*_view.py 里。"""
from __future__ import print_function

import dgtest
import fdtest

Feel = fdtest.load("Compat.Diegesis.TouchFeel")
Input = dgtest.load("Shared.Input")
Gestures = fdtest.load("dolorContainer.Client.Gestures")


class Old(object):
    """老版本前置包的视图：没有 doubleSeconds。"""


class New(object):
    def doubleSeconds(self):
        return 0.4


def testTheDoubleClickWindowIsTheViewsOrTheCallersDefault():
    assert Feel.doubleClick(New(), 0.25) == 0.4
    assert Feel.doubleClick(Old(), 0.25) == 0.25


def testTheTouchSlopIsTheContainerLibrarysTouchDragDistanceInScreenPixels():
    """内核的触屏拖动门槛是 dolorContainer 抄原版的 TOUCH_SCROLL_PIXELS（35.4 个屏幕像素），换成界面单位用；两处别各改各的。"""
    assert Input.TOUCH_DRAG_SCREEN_PIXELS == Gestures.TOUCH_SCROLL_PIXELS == 35.4


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
