# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点盛出（scoop）里抛了异常：锅里的菜不能已经少了一份（Compat/Diegesis/PotScoop.scoop / Server/PotServe.servingFrom，前置包的 Manager 是真的）

前置包的 Undo 只管站点自己的东西和背包窗口：动作作废时放回原样（碗没扣、菜没进背包）。预览槽（方块实体数据）、做过几份、经验球是直接写进锅和引擎的，撤不回来。
原来每盛一份就先把预览槽里的菜扣掉，之后才给背包、记做过几份、给经验、发表现事件：后面任何一步抛了异常，窗口作废了，锅里却已经少了一份菜（碗还在、菜没了）。
现在盛的时候只改预览槽的一份拷贝，容器扣完、菜给完、表现事件发完、记过几份给过经验之后，预览槽里菜减少是最后一步。
"""
from __future__ import print_function

import potkit as K
from potkit import fake, HandCooking, SAUCE, BOWL


def _setup(fromInventory=False):
    """锅里三份番茄酱（记着 4 份的经验），碗三个：在光标栈上，或在背包里。"""
    manager, data = K.setup()
    K.setMeal(SAUCE, 3, data)
    K.PotContainer.addUsed(data, SAUCE, 4)
    fake.give("a", 5, BOWL, 3)
    K.opened(manager)
    if not fromInventory:
        assert K.do(manager, "a", K.click(K.inv(5)))
    fake.world.take()
    return manager, data


def _station(manager):
    return manager.stations[(0, K.POT)]


def _boom(*args, **kwargs):
    raise RuntimeError("injected")


def _failing(manager, where):
    """让盛出里 where 这一步抛异常；返回撤销它的函数。"""
    if where == "served":
        real = K.PotServe.served
        K.PotServe.served = _boom
        return lambda: setattr(K.PotServe, "served", real)
    if where == "event":
        real = K.PotLook.event
        K.PotLook.event = _boom
        return lambda: setattr(K.PotLook, "event", real)
    station = _station(manager)                           # effect：站点（前置包的 Station）的方法
    station.effect = _boom
    return lambda: delattr(station, "effect")


def _untouched(manager, fromInventory):
    assert K.preview()["count"] == 3, "锅里的菜一份不少"
    assert fake.count("a", SAUCE) == 0, "菜没进背包"
    if fromInventory:
        assert manager.sessions["a"].hand is None and fake.world.players["a"]["inv"][5]["count"] == 3, "背包里的碗没扣"
    else:
        hand = manager.sessions["a"].hand
        assert hand["newItemName"] == BOWL and hand["count"] == 3, "光标栈上的碗没扣"
    assert HandCooking.madeOf("a", SAUCE) == 0 and K.orbs() == [], "没记做过几份、没给经验"


def testWhateverFailsInAScoopThePotStillHasAllItsServings():
    for fromInventory in (False, True):
        for where in ("effect", "event", "served"):
            manager, data = _setup(fromInventory)
            undo = _failing(manager, where)
            try:
                assert not K.do(manager, "a", K.custom("scoop", all=True, from_inventory=fromInventory)), where
            finally:
                undo()
            _untouched(manager, fromInventory)
            assert len(fake.world.errors) == 1 and fake.world.errors[0], "只记了一行日志"
            del fake.world.errors[:]
            assert K.do(manager, "a", K.custom("scoop", all=True, from_inventory=fromInventory)), "钩子好了：同一个动作照常盛出"
            assert K.preview() == {} and HandCooking.madeOf("a", SAUCE) == 3 and len(K.orbs()) == 1, (where, fromInventory)


def testThePotLosesItsServingsOnlyAfterTheDishesAreGivenTheCountIsRecordedAndTheExperienceIsOut():
    manager, data = _setup()
    seen = []
    real = K.PotServe.served

    def spy(playerId, dimensionId, blockEntityData, dish, count):
        seen.append(("served", K.preview()["count"], count))
        return real(playerId, dimensionId, blockEntityData, dish, count)

    K.PotServe.served = spy
    try:
        assert K.do(manager, "a", K.custom("scoop", all=True))
    finally:
        K.PotServe.served = real
    assert seen == [("served", 3, 3)], "记做过几份、给经验的时候，预览槽里还是 3 份：%r" % (seen,)
    assert K.preview() == {}, "三份都盛走了，预览槽最后才空"


def testAnEmptyPotOrNoVesselScoopsNothingAndWritesNothing():
    manager, data = _setup()
    K.setMeal("arris:dumplings", 2, data)                  # 饺子不要容器
    assert K.do(manager, "a", K.custom("scoop"))
    assert K.preview()["count"] == 2 and HandCooking.madeOf("a", "arris:dumplings") == 0
    K.setMeal(SAUCE, 0, data)                              # 空的预览槽
    assert K.do(manager, "a", K.custom("scoop"))
    assert K.preview() == {} and manager.sessions["a"].hand["count"] == 3


def testServingFromACopyLeavesTheMealItWasGivenWhole():
    """PotServe.servingFrom 只改传进来的字典；takeServing（右键盛、经典界面）照旧一份份直接写锅。"""
    meal = {"newItemName": SAUCE, "newAuxValue": 0, "count": 3}
    dish = K.PotServe.servingFrom(meal)
    assert dish == {"newItemName": SAUCE, "newAuxValue": 0, "count": 1} and meal["count"] == 2
    assert K.PotServe.servingFrom({}) is None and K.PotServe.servingFrom(None) is None
    manager, data = K.setup()
    K.setMeal(SAUCE, 2, data)
    assert K.PotServe.takeServing(data)["count"] == 1 and K.preview()["count"] == 1
    assert K.PotServe.takeServing(data)["count"] == 1 and K.preview() == {}
    assert K.PotServe.takeServing(data) is None


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
