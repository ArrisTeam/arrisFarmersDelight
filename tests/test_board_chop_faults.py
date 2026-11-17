# -*- coding: utf-8 -*-
# runner: both
"""砧板最后一刀里抛了异常：副手里的刀不能已经磨损（Compat/Diegesis/BoardChop._cutTheStack / BoardGive.putTool / settleTool，前置包的 Manager 是真的）

前置包的 Undo 只管站点自己的东西（槽、控件、输出、data、表现事件）和背包窗口：动作作废时放回原样。副手里的刀是直接写进引擎的，撤不回来，
原来它排在产物、板上剩下的、刀口、表现事件之前写：后面哪一步抛了异常，动作作废，板和背包都放回去了，副手的刀却已经磨损（或没了），产物没出。
现在直接写引擎的（副手的刀、刀碎的声音）是动作的最后一步。背包窗口里的刀（光标栈、背包格）照 HoD 的次序先写，随窗口一起丢。
"""
from __future__ import print_function

import boardkit as K
from boardkit import fake

KNIFE = "arris:iron_knife"
CABBAGE = "arris:cabbage"
LEAF = "arris:cabbage_leaf"


def _setup(offhand=70, slot=None, durability=100):
    """卷心菜两个放在板上；刀在副手（offhand 是它的耐久）或背包第 slot 格；返回 (Manager, 板的数据)。"""
    manager, data = K.setup()
    K.opened(manager)
    K.carry(manager, 3, CABBAGE, 2)
    assert K.do(manager, "a", K.custom("place"))
    if slot is None:
        fake.world.players["a"]["offhand"] = {"newItemName": KNIFE, "newAuxValue": 0, "count": 1, "durability": offhand}
    else:
        fake.give("a", slot, KNIFE, 1)
        fake.world.players["a"]["inv"][slot]["durability"] = durability
    K.effects()
    return manager, data


def _chop(manager):
    return K.do(manager, "a", K.custom("chop", mark=0, at=8.0))


def _logic(manager):
    return manager.stations[(0, K.BOARD)].logic


def _boom(*args, **kwargs):
    raise RuntimeError("injected")


def _failing(manager, where):
    """让最后一刀里 where 这一步抛异常；返回撤销它的函数。"""
    logic = _logic(manager)
    if where == "give":
        give = K.BoardChop.BoardGive.give
        K.BoardChop.BoardGive.give = _boom
        return lambda: setattr(K.BoardChop.BoardGive, "give", give)
    if where == "emit":
        emit = K.BoardChop.emit
        K.BoardChop.emit = _boom
        return lambda: setattr(K.BoardChop, "emit", emit)
    setattr(logic, where, _boom)                           # setBoard / restart：站点逻辑的方法
    return lambda: delattr(logic, where)


def testWhateverFailsInTheLastChopTheKnifeInTheOffHandIsNotWorn():
    for where in ("give", "setBoard", "restart", "emit"):
        manager, data = _setup(offhand=70)
        undo = _failing(manager, where)
        try:
            assert not _chop(manager), where
        finally:
            undo()
        assert fake.world.players["a"]["offhand"]["durability"] == 70, "%s 抛了：副手的刀原样" % where
        assert K.board(data) == (CABBAGE, 2) and K.count(LEAF) == 0, "%s 抛了：板上的卷心菜还在，叶子没出" % where
        assert len(fake.world.errors) == 1, "只记了一行日志"
        del fake.world.errors[:]
        _logic(manager).restart()                          # 刀口数是站点逻辑自己的字段，前置包不管（Undo 的文档）：重布一次再切，这里只看副手和板
        K.advance(0.2)
        assert _chop(manager) and K.board(data) is None and K.count(LEAF) == 4, "钩子好了：同一刀照常切开"
        assert fake.world.players["a"]["offhand"]["durability"] == 68


def testABrokenKnifeInTheOffHandIsStillThereWhenTheChopFails():
    manager, data = _setup(offhand=1)
    undo = _failing(manager, "emit")
    try:
        assert not _chop(manager)
    finally:
        undo()
    assert fake.world.players["a"]["offhand"] == {"newItemName": KNIFE, "newAuxValue": 0, "count": 1, "durability": 1}, "最后一点耐久也还在"
    assert K.board(data) == (CABBAGE, 2)
    _logic(manager).restart()
    K.advance(0.2)
    assert _chop(manager)
    assert fake.world.players["a"]["offhand"] is None, "切成功了：刀用坏，副手空了"
    assert K.count(LEAF) == 2 and K.board(data) == (CABBAGE, 1), "耐久只够切一个卷心菜"


def testTheOffHandKnifeIsWrittenAfterEverythingElseOfTheChopIsDone():
    manager, data = _setup(offhand=70)
    seen = []
    emit = K.BoardChop.emit

    def spy(logic, name, payload):
        seen.append((name, fake.world.players["a"]["offhand"]["durability"], K.board(data), K.count(LEAF)))
        return emit(logic, name, payload)

    K.BoardChop.emit = spy
    try:
        assert _chop(manager)
    finally:
        K.BoardChop.emit = emit
    assert seen == [("chopped", 70, None, 0)], "表现事件发出的时候板已经切空（叶子还在背包窗口里，没写回引擎），副手的刀还没动：%r" % (seen,)
    assert fake.world.players["a"]["offhand"]["durability"] == 68


def testAKnifeInTheInventoryIsStillUntouchedWhenTheChopFailsToo():
    manager, data = _setup(slot=7, durability=100)
    undo = _failing(manager, "setBoard")
    try:
        assert not _chop(manager)
    finally:
        undo()
    assert fake.world.players["a"]["inv"][7]["durability"] == 100, "背包窗口里的刀随窗口一起丢，没写回"
    assert K.board(data) == (CABBAGE, 2) and K.count(LEAF) == 0


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
