# -*- coding: utf-8 -*-
# runner: both
"""四个站点的触屏长按在有数量档的前置包上（Compat/Diegesis/HoldMenu.tapMode，前置包的 Protocol.TAP_MODE：视图上有 tap）：屏幕右下角的"全部 / 单个"按钮管
"拿着不止一个的一叠点一下放多少"（"单个"档里点一下就是右键），所以"放一个"不再放进轮盘——厨锅的锅口、砧板的板口、煎锅都没有它了；炉灶拿着一叠时的
"只放这一格"也归那个按钮（单个 = 右键 = 只摆离光标最近的那一格），手上只有一个时还在（两档都是左键，选哪一格还得靠它）。别的条目（插在板上、全部盛出、取回……）不变。
老版本的前置包（视图上没有 tap）照旧给：别的测试文件里的替身视图就是那种。用户 2026-11-19 定的：放多少用切换按钮，不用长按出轮盘。
"""
from __future__ import print_function

import test_board_view as B
import test_grill_view as G
import test_pan_view as P
import test_pot_view as K

import fdtest

HoldMenu = fdtest.load("Compat.Diegesis.HoldMenu")
KNIFE = B.KNIFE


class Old(object):
    """老版本的前置包的视图：没有 tap。"""


class New(object):
    tap = "stack"


def testTheKernelWithTheTapLevelIsToldFromAnOldOneByTheView():
    assert HoldMenu.tapMode(New()) and not HoldMenu.tapMode(Old())
    new = New()
    new.tap = "one"
    assert HoldMenu.tapMode(new), "停在哪一档都算有"


def testThePotsMouthNoLongerOffersPutOne():
    behavior, view = K.behaviorOf()
    view.hand = dict(K.CARROTS)
    assert K._hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}, "前提：老版本的前置包照旧给"
    view.tap = "stack"
    assert K._hold(behavior, "mouth") is None, "有数量档：按下立刻生效，不等长按"
    view.tap = "one"
    assert K._hold(behavior, "mouth") is None
    assert behavior.onPointer(K.Event(K.RIGHT, K.Hit("mouth"))) is True and view.spread.button == K.RIGHT, "单个档送来的右键：放一个"


def testTheBoardsMouthNoLongerOffersPutOneButStillOffersCarve():
    behavior, view = B._open(hand=B.C.item("arris:cabbage", 3))
    assert B._hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}, "前提：老版本的前置包照旧给"
    view.tap = "stack"
    assert B._hold(behavior, "mouth") is None
    behavior, view = B._open(hand=B.C.item(KNIFE))
    view.tap = "one"
    assert B._hold(behavior, "mouth") == {"menu": [HoldMenu.CARVE]}, "Shift 点击的变体不归数量档管：还在"


def testThePanNoLongerOffersPutOneButStillOffersTakeAllBack():
    behavior, view = P.make(hand=P.item("minecraft:beef", 5), food=None)
    assert P.hold(behavior, (8.0, 3.0, 8.0)) == {"menu": [HoldMenu.PUT_ONE]}, "前提：老版本的前置包照旧给"
    view.tap = "stack"
    for target in ((8.0, 3.0, 8.0), (8.0, 1.0, 8.0), (8.0, 2.0, 22.0)):
        assert P.hold(behavior, target) is None, target
    behavior, view = P.make()
    view.tap = "one"
    assert P.hold(behavior, (8.0, 1.0, 8.0)) == {"menu": [HoldMenu.TAKE_ALL_BACK]}, "空手的右键变体不归数量档管：还在"


def testTheGrillOffersPutHereOnlyForASingleItemNow():
    """炉灶的测试用的是真的前置包视图（有 tap）：拿着一叠——数量档管（单个 = 只放这一格），不给；只拿着一个——两档都是左键（摆第一个空位），选哪一格还得靠轮盘。"""
    view = G.make(pieces={1: G.item(G.BEEF)})
    assert HoldMenu.tapMode(view), "前提：这个前置包有数量档"
    view.setHand(G.item(G.BEEF, 5))
    assert view.holdOf(G.screenOf(view, 4)) is None
    assert G.click(view, 4, button=1) and G.actions()[-1] == ("place", {"one": True, "place": 4}), "单个档送来的右键：只摆离光标最近的那一格一件"
    view.setHand(G.item(G.BEEF, 1))
    assert view.holdOf(G.screenOf(view, 4)) == {"menu": [HoldMenu.PUT_HERE]}


def main():
    return fdtest.run(globals())


if __name__ == "__main__":
    raise SystemExit(main())
