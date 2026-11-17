# -*- coding: utf-8 -*-
# runner: both
"""触屏的拖动门槛和容器库（dolorContainer）抄的原版值是同一个数（站点表现里触屏的手感在 TouchFeel，后面的提交再补它的用例）。"""
from __future__ import print_function

import dgtest
import fdtest

Input = dgtest.load("Shared.Input")
Gestures = fdtest.load("dolorContainer.Client.Gestures")


def testTheTouchSlopIsTheContainerLibrarysTouchDragDistanceInScreenPixels():
    """内核的触屏拖动门槛是 dolorContainer 抄原版的 TOUCH_SCROLL_PIXELS（35.4 个屏幕像素），换成界面单位用；两处别各改各的。"""
    assert Input.TOUCH_DRAG_SCREEN_PIXELS == Gestures.TOUCH_SCROLL_PIXELS == 35.4


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
