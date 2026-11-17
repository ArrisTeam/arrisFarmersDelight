# -*- coding: utf-8 -*-
# runner: both
"""砧板站点里第二个 assembled 在第一个的收尾 / 沉层还没演完时到了（Compat/Diegesis/BoardDrawEvents.assembled，假引擎见 boardclient.py）

书里点菜一键做成，assemble 每 0.1 秒就能来一次（令牌桶 40 个每秒）：第二个 assembled 到的时候第一个还在演。JE 的 BoardBehavior.assembled 不取消前一个
（排下的步骤照走），melting 是后一个覆盖前一个，层只在倒数走完时才还原（tick：scaleTo(1, 0) + setVisible(false)）；这边的 done 原来是每个 assembled 各还原一遍：
先演完的那个在后一个演到一半时把层的缩放 / 转角全还原了、倒数归零（板上的状态提前画），画面抖一下。
现在每个 assembled 的 done 只在它是最后一个演完时才还原。每个都照演（各自的收尾、各自做成的两声）。
"""
from __future__ import print_function

import boardclient as C
import fdtest
import test_board_finish_anim as F

Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
Kit = fdtest.load("Shared.Rules.HandsOn.BoardFinishKit")
DT = F.DT
TOSS = F.DISHES[1]                                      # 拌：收尾演一阵
SALAD = TOSS[1]


def _again(behavior, view, finish, dish, layers, count):
    """又做成了一道：状态是层清空、菜多了一份，随后 assembled 效果到。"""
    view.state.layers, view.state.board = [], C.item(dish, count)
    behavior.onState(F.CHANGED)
    behavior.onEffect("assembled", {"layers": [C.item(name) for name in layers], "finish": finish, "block": False})


def _reset(draw):
    return all(not thing.mover.visible and thing.mover.scale == 1.0 and thing.mover.rotation is None for thing in draw.layers)


def _pops():
    return [sound for sound in C.engine.played if sound[:2] == (F.POP[0][0], F.POP[0][1])]


def testTheFirstOfTwoOverlappingAssembliesDoesNotPutTheLayersBackWhileTheSecondStillPlays():
    finish, dish, layers = TOSS
    behavior, view = F._open(layers)
    F._made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    F._frames(behavior, 0.3)
    _again(behavior, view, finish, dish, layers, 2)
    assert draw.assembling == 2
    firstDone = Kit.finishing(finish, len(layers)) + Kit.MELT_TIME
    F._frames(behavior, firstDone - 0.3 + 3 * DT)                  # 第一个的 done 该走了：第二个才演到一半
    assert draw.assembling == 1, "第一个演完了，第二个还在演"
    assert draw.melting > 0.0, "第二个还在沉：倒数不归零"
    assert not _reset(draw), "第二个的层还在动：缩放 / 转角 / 显隐没被第一个还原"
    F._frames(behavior, 4.0)
    assert draw.assembling == 0 and draw.melting == 0.0 and draw.late is None
    assert _reset(draw), "最后一个演完：层还原"
    assert F._live(view) == [SALAD, SALAD], "只剩两份菜（一份在上、一份垫在下面）：没有层、盖子、替身留在世界里：%r" % (F._live(view),)
    behavior.onClose()
    assert F._live(view) == []


def testTheStateThatCameWhileTheLayersSankIsDrawnOnlyAfterTheLastAssemblyEnds():
    finish, dish, layers = TOSS
    behavior, view = F._open(layers)
    F._made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    F._frames(behavior, 0.3)
    _again(behavior, view, finish, dish, layers, 2)
    view.state.board, view.state.layers = None, [C.item(F.TOMATO)]            # 之后有人把菜取走、放了一层番茄
    behavior.onState(F.CHANGED)
    assert draw.late is not None
    firstDone = Kit.finishing(finish, len(layers)) + Kit.MELT_TIME
    F._frames(behavior, firstDone - 0.3 + 3 * DT)
    assert draw.late is not None and draw.shown["layers"] != [(F.TOMATO, 0)], "第一个演完不算：状态接着等"
    F._frames(behavior, 4.0)
    assert draw.late is None and draw.shown["layers"] == [(F.TOMATO, 0)] and F._live(view) == [F.TOMATO]
    tomato = draw.layers[0]
    assert tomato.mover.scale == 1.0 and tomato.mover.rotation is None, "放回的第一层不是缩着的、转着的"
    behavior.onClose()


def testASecondAssemblyThatEndsBeforeTheFirstDoesNotPutTheLayersBackEither():
    """第一个是书里点的四层菜（先等层从玩家那边飞来），第二个只有一层、来得晚却先演完：它的 done 比第一个早到，同样不能还原还在演的层。"""
    finish, dish, layers = F.DISHES[3]
    behavior, view = F._open()
    draw = behavior.draw
    draw.quiet = False
    view.state.board = C.item(dish)
    behavior.onState(F.CHANGED)
    behavior.onEffect("assembled", {"layers": [C.item(name) for name in layers], "finish": finish, "block": False})
    first = draw.melting
    F._frames(behavior, 0.3)
    behavior.onEffect("assembled", {"layers": [C.item("minecraft:bread")], "finish": Assembly.FINISH_PRESS, "block": False})
    assert draw.assembling == 2
    second = draw.melting
    assert 0.3 + second < first - 0.1, "第二个比第一个先演完（%.2f、%.2f）" % (0.3 + second, first)
    F._frames(behavior, second + 4 * DT)                           # 第二个演完了：第一个还在演
    assert draw.assembling == 1 and draw.melting > 0.0, "第二个先演完，第一个的倒数照走"
    assert not _reset(draw), "第一个的层还在动：没被第二个的 done 还原"
    F._frames(behavior, 4.0)
    assert draw.assembling == 0 and draw.melting == 0.0 and _reset(draw) and F._live(view) == [dish]
    behavior.onClose()


def testEachOverlappingAssemblyStillPopsItsOwnDish():
    finish, dish, layers = TOSS
    behavior, view = F._open(layers)
    F._made(behavior, view, finish, dish, layers)
    F._frames(behavior, 0.3)
    _again(behavior, view, finish, dish, layers, 2)
    F._frames(behavior, 6.0)
    assert len(_pops()) == 2, "两道菜各响一次做成的声音：%r" % (_pops(),)
    behavior.onClose()


def testAnyTwoFinishesOverlappingLeaveNothingBehind():
    """十种收尾两两重叠（第二个在第一个演到 0.1 / 0.3 秒时到）：都演完之后倒数归零、没有排着的步骤、层都还原、世界里只剩第二道菜（夹的盖子、替身都收了）。"""
    for first in F.DISHES:
        for second in F.DISHES:
            for gap in (0.1, 0.3):
                behavior, view = F._open(first[2])
                F._made(behavior, view, first[0], first[1], first[2])
                draw = behavior.draw
                F._frames(behavior, gap)
                _again(behavior, view, second[0], second[1], second[2], 1)
                F._frames(behavior, 6.0)
                where = (first[0], second[0], gap)
                assert draw.assembling == 0 and draw.melting == 0.0 and draw.late is None and draw.steps == [], where
                assert _reset(draw) and all(not thing.mover.visible for thing in draw.ghosts), where
                assert F._live(view) == [second[1]], (where, F._live(view))
                behavior.onClose()
                assert F._live(view) == [], where


def testALoneAssemblyStillPutsTheLayersBackWhenItEnds():
    finish, dish, layers = TOSS
    behavior, view = F._open(layers)
    F._made(behavior, view, finish, dish, layers)
    assert behavior.draw.assembling == 1
    F._frames(behavior, 4.0)
    assert behavior.draw.assembling == 0 and behavior.draw.melting == 0.0 and _reset(behavior.draw) and F._live(view) == [SALAD]
    behavior.onClose()


if __name__ == "__main__":
    raise SystemExit(F.fdtest.run(globals()))
