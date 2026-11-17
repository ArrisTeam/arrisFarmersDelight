# -*- coding: utf-8 -*-
# runner: both
"""砧板最后一刀里抛了异常：副手里的刀不能已经磨损（Compat/Diegesis/BoardChop._cutTheStack / BoardGive.putTool / settleTool，前置包的 Manager 是真的）

前置包的 Undo 只管站点自己的东西（槽、控件、输出、data、表现事件）和背包窗口：动作作废时放回原样。副手里的刀是直接写进引擎的，撤不回来，
原来它排在产物、板上剩下的、刀口、表现事件之前写：后面哪一步抛了异常，动作作废，板和背包都放回去了，副手的刀却已经磨损（或没了），产物没出。
现在直接写引擎的（副手的刀、刀碎的声音）是动作的最后一步。背包窗口里的刀（光标栈、背包格）照 HoD 的次序先写，随窗口一起丢。
刀口进度（BoardLogic 的 cut：已落几刀、两刀的间隔、刀口布局）、配方、板上东西的键也是站点逻辑自己的字段，Undo 同样不认识：原来落了一刀才出的错，动作作废了，
刀口数却停在加一的地方，板子拒绝之后每一刀，要把东西拿下来再放上去才好（测试里原来要自己重布一次、等一等才能再切）。现在 BoardLogic.onCustomAction 在动作之前存一份、抛了放回去再抛。
"""
from __future__ import print_function

import boardkit as K
from boardkit import fake

KNIFE = "arris:iron_knife"
CABBAGE = "arris:cabbage"
LEAF = "arris:cabbage_leaf"
HAM = "arris:ham"


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
        assert _logic(manager).cut.marks == 0, "%s 抛了：刀口数也回到动作之前（它是站点逻辑自己的字段，前置包的 Undo 不管，BoardLogic.onCustomAction 存了放回）" % where
        assert _chop(manager) and K.board(data) is None and K.count(LEAF) == 4, "钩子好了：同一刀马上照常切开，不用拿下来再放、不用等"
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
    assert _chop(manager), "钩子好了：同一刀马上切得下去"
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


def _setupHam():
    """火腿两个放在板上（刀口不止一刀：切第一刀不是最后一刀）；刀在背包第 7 格。"""
    manager, data = K.setup()
    K.opened(manager)
    K.carry(manager, 3, HAM, 2)
    assert K.do(manager, "a", K.custom("place"))
    fake.give("a", 7, KNIFE, 1)
    fake.world.players["a"]["inv"][7]["durability"] = 100
    K.effects()
    assert _logic(manager).cut.plan.marks >= 2, "要一块不止一刀的东西"
    return manager, data


def testAChopThatFailsAfterTheMarkWasCountedLeavesTheMarkAndTheTimerWhereTheyWere():
    """不是最后一刀的一刀里发表现事件抛了异常：动作作废，板和背包放回去了，刀口数却已经加一（站点逻辑自己的字段）——客户端收到的还是原来的、下一刀的序号对不上，
    板子拒绝之后每一刀，要把东西拿下来再放上去才好。现在刀口数和两刀的间隔都回到动作之前：同一刀马上切得下去。"""
    manager, data = _setupHam()
    undo = _failing(manager, "emit")
    try:
        assert not _chop(manager)
    finally:
        undo()
    assert len(fake.world.errors) == 1, "只记了一行日志"
    del fake.world.errors[:]
    assert _logic(manager).cut.marks == 0, "刀口数回到 0（原来是 1）"
    assert K.board(data) == (HAM, 2) and K.effects("a") == [], "板上还是两个火腿，没有表现事件"
    assert _chop(manager), "同一刀（第 0 刀）马上切得下去，不用等 0.15 秒"
    assert _logic(manager).cut.marks == 1 and [name for name, _data in K.effects("a")] == ["chopped"]


def testAnIgnoredActionAndAnUnknownOneChangeNothingAndAFailedOneOfAnotherKindRestoresToo():
    """别的动作中途抛了异常也一样（拿下板上的东西时发表现事件抛了）：板上的东西、刀口进度都回到动作之前；不认识的动作什么也不动。"""
    manager, data = _setupHam()
    assert _chop(manager) and _logic(manager).cut.marks == 1
    K.effects()
    before = (_logic(manager).cut.marks, _logic(manager).cut.lastChop, _logic(manager).itemKey)
    assert not K.do(manager, "a", K.custom("mystery"))
    emit = K.BoardLogic.emit
    K.BoardLogic.emit = _boom                              # 取回：板上的东西给厨师、重布刀口、发 taken，最后一步抛了
    try:
        assert not K.do(manager, "a", K.custom("take"))
    finally:
        K.BoardLogic.emit = emit
    del fake.world.errors[:]
    assert (_logic(manager).cut.marks, _logic(manager).cut.lastChop, _logic(manager).itemKey) == before and K.board(data) == (HAM, 2)


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
