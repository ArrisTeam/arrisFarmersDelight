# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点的触屏长按（Compat/Diegesis/GrillHold.py）：手上拿着东西点烤架，"只放这一格"只给烤架收的东西（view.fits，和厨锅、煎锅的"放一个"一样）：
鸡蛋、铁锭、泥土烤架不收，左键右键都放不上去，选了也白选（评审的 s8）。
"""
from __future__ import print_function

import test_grill_view as T

import fdtest

item, HoldMenu = T.item, T.HoldMenu


def testNoPutHereForThingsTheGrillDoesNotTake():
    view = T.make(pieces={1: item(T.BEEF)})
    for name in ("minecraft:egg", "minecraft:iron_ingot", "minecraft:dirt"):
        view.setHand(item(name, 1))
        assert not T.Rules.mayPlace(item(name, 1)), "前提：烤架不收 %s" % name
        assert view.fits(T.Rules.GROUP_GRILL) is None
        assert view.holdOf(T.screenOf(view, 4)) is None, "%s：没有菜单" % name


def testPutHereStaysForWhatTheGrillTakesAndWhenMoreThanOnePlaceIsFree():
    view = T.make(pieces={1: item(T.BEEF)})
    view.setHand(item(T.BEEF, 1))                        # 拿着一叠的归前置包的数量档管（test_hold_tap_mode），这里看只拿着一个的
    assert view.fits(T.Rules.GROUP_GRILL) is not None
    assert view.holdOf(T.screenOf(view, 4)) == {"menu": [HoldMenu.PUT_HERE]}
    view = T.make(pieces=dict((place, item(T.BEEF)) for place in range(5)))
    view.setHand(item(T.BEEF, 1))
    assert view.holdOf(T.screenOf(view, 5)) is None, "只剩一个空位：一直没有（原来的规矩）"


def testAFullGrillHasNoMenuEither():
    view = T.make(pieces=dict((place, item(T.BEEF)) for place in range(6)))
    view.setHand(item(T.BEEF, 5))
    assert view.fits(T.Rules.GROUP_GRILL) is None and view.holdOf(T.screenOf(view, 4)) is None


def main():
    return fdtest.run(globals())


if __name__ == "__main__":
    raise SystemExit(main())
