# -*- coding: utf-8 -*-
# runner: both
"""服务端照引擎算"满足条件的 aux"（Server/HeatAux），给读不到方块状态的客户端：

  1. 炼药锅照引擎的样子（fill_level 占低 3 位、cauldron_liquid 占上面 2 位，中间有空号）算出熔岩 1–6 级 = aux 9–14，和静态的初值一样，表不动
  2. 条件变了的才重算，同一份条件只问一次引擎；别的模组写进条件表的方块算出来写进表（就地改）
  3. 引擎一个状态也问不出来（没预设、一直给 None、一直给 {}、抛异常）：表里原来的不动，打一行日志，同一份条件不再问
接到表同步上（进服那一份差异里条件和算好的 aux 集合一起到客户端）在 test_table_sync_server.py。
引擎是 fakeengine.py 里的假的（GetBlockStatesFromAuxValue 照 world.auxStates 答）。
"""
from __future__ import print_function

import sys

import fakeengine
import fdtest

world = fakeengine.install()
HeatAux = fdtest.load("Server.HeatAux")
Cooking = fdtest.load("Shared.Data.Cooking")
LIQUIDS = ("water", "lava", "powder_snow")
BRAZIER = "mymod:brazier"


def cauldron(aux):
    level, liquid = aux & 7, aux >> 3
    if level > 6 or liquid >= len(LIQUIDS):
        return None
    return {"fill_level": level, "cauldron_liquid": LIQUIDS[liquid]}


class Counted(object):
    """数一数问了几次的 read。"""

    def __init__(self, read):
        self.read, self.asked = read, 0

    def __call__(self, aux):
        self.asked += 1
        return self.read(aux)


class _Capture(object):
    def __init__(self):
        self.chunks = []

    def write(self, text):
        self.chunks.append(text)

    def flush(self):
        pass


def _fresh():
    """表放回原样，HeatAux 忘掉算过的。"""
    for table, pristine in ((Cooking.HeatSourceStateDict, {"minecraft:cauldron": {"cauldron_liquid": "lava", "fill_level": {"min": 1}}}),
                            (Cooking.HeatSourceAuxDict, {"minecraft:cauldron": [9, 10, 11, 12, 13, 14]})):
        table.clear()
        table.update(pristine)
    HeatAux._done.clear()
    HeatAux._last.clear()
    world.auxStates.clear()


def _quietly(call):
    saved, sys.stdout = sys.stdout, _Capture()
    try:
        result = call()
        return result, "".join(sys.stdout.chunks)
    finally:
        sys.stdout = saved


def testTheCauldronComesOutAsTheStaticTableAndNothingChanges():
    _fresh()
    world.auxStates["minecraft:cauldron"] = Counted(cauldron)
    table = Cooking.HeatSourceAuxDict
    assert HeatAux.refresh() == [] and Cooking.HeatSourceAuxDict is table
    assert table["minecraft:cauldron"] == [9, 10, 11, 12, 13, 14]
    report = HeatAux.report()["minecraft:cauldron"]
    assert report["aux"] == [9, 10, 11, 12, 13, 14] and report["top"] == 22 and report["written"] is True, report
    assert world.auxStates["minecraft:cauldron"].asked == 46
    assert HeatAux.refresh() == [] and world.auxStates["minecraft:cauldron"].asked == 46, "同一份条件不再问引擎"


def testAnotherModsConditionIsWorkedOutAndWrittenAndRedoneWhenItChanges():
    _fresh()
    world.auxStates["minecraft:cauldron"] = cauldron
    world.auxStates[BRAZIER] = Counted(lambda aux: {"mymod:coals": aux & 3, "direction": aux >> 2} if aux < 16 else None)
    Cooking.HeatSourceStateDict[BRAZIER] = {"mymod:coals": {"min": 1}, "direction": [0, 2]}
    assert HeatAux.refresh() == [BRAZIER]
    assert Cooking.HeatSourceAuxDict[BRAZIER] == [1, 2, 3, 9, 10, 11]
    asked = world.auxStates[BRAZIER].asked
    assert HeatAux.refresh() == [] and world.auxStates[BRAZIER].asked == asked
    Cooking.HeatSourceStateDict[BRAZIER] = {"mymod:coals": 3}
    assert HeatAux.refresh() == [BRAZIER] and Cooking.HeatSourceAuxDict[BRAZIER] == [3, 7, 11, 15], "换了条件：重算"
    Cooking.HeatSourceStateDict[BRAZIER]["mymod:coals"] = 2
    assert HeatAux.refresh() == [BRAZIER] and Cooking.HeatSourceAuxDict[BRAZIER] == [2, 6, 10, 14], "就地改了条件也看得出来"


def testWhenTheEngineAnswersNothingTheTableStaysAndItSaysSoOnce():
    for engine in (None, lambda aux: None, lambda aux: {}, "raise"):
        _fresh()
        if engine == "raise":
            def boom(aux):
                raise RuntimeError("no such aux")
            world.auxStates["minecraft:cauldron"] = boom
        elif engine is not None:
            world.auxStates["minecraft:cauldron"] = engine
        changed, printed = _quietly(HeatAux.refresh)
        assert changed == [] and Cooking.HeatSourceAuxDict["minecraft:cauldron"] == [9, 10, 11, 12, 13, 14], engine
        assert printed.count("minecraft:cauldron") == 1 and HeatAux.report()["minecraft:cauldron"]["written"] is False, printed
        changed, printed = _quietly(HeatAux.refresh)
        assert changed == [] and printed == "", "同一份条件不再问、不再说"
    _fresh()
    Cooking.HeatSourceStateDict[BRAZIER] = {"mymod:coals": {"min": 1}}
    changed, printed = _quietly(HeatAux.refresh)
    assert BRAZIER not in Cooking.HeatSourceAuxDict and BRAZIER in printed, "问不出来的新方块：表里没有它，客户端当不热"


def testTheServerReadsEachStateFromItsOwnComponent():
    """reader 每问一个 aux 都经 CreateBlockState(levelId)（组件不存放），抛了异常的那一个当没有方块，后面的照问。"""
    _fresh()
    answers = {0: {"mymod:coals": 0}, 1: "boom", 2: {"mymod:coals": 2}}

    def flaky(aux):
        answer = answers.get(aux)
        if answer == "boom":
            raise ValueError(aux)
        return answer

    world.auxStates[BRAZIER] = flaky
    read = HeatAux.reader(BRAZIER)
    assert [read(aux) for aux in range(4)] == [{"mymod:coals": 0}, None, {"mymod:coals": 2}, None]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
