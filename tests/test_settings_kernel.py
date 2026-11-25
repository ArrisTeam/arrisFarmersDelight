# -*- coding: utf-8 -*-
# runner: both
"""农夫乐事那一组玩家开关放进前置包真的设置表（它的 Shared/Settings：Item、Group、Store.stationOn）：内核替我们拦的站点和我们报给服务端的
"砧板站点对我开不开"（Shared/Rules/StationSwitches.boardOn）对每种开关组合都是同一个答案；厨锅、煎锅、炉灶的项只管自己的站点；
总开关关了四个都不开。项是 Compat/Diegesis/SettingsClientLink 登记的那份（StationSwitches.playerSwitches + 各站点登记用的站点 id）。"""
from __future__ import print_function

import itertools

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

Settings = dgtest.load("Shared.Settings")
Rules = fdtest.load("Shared.Rules.StationSwitches")
IDS = dict((key, fdtest.load("Shared.Rules." + module).STATION_ID) for key, module in
           (("cooking_pot", "PotStation"), ("cutting_board", "BoardStation"), ("skillet", "PanStation"), ("stove", "GrillStation")))
KEYS = ("enabled", "cooking_pot", "cutting_board", "skillet", "stove")


def _store(values):
    store = Settings.Store()
    store.register(Settings.Group(Rules.GROUP, Rules.GROUP_TITLE, [Settings.Item(**item) for item in Rules.playerSwitches(IDS)]))
    for key, value in values.items():
        assert store.set(Rules.GROUP, key, value) == value
    return store


def testTheKernelsGateAndTheReportAgreeOnEveryCombination():
    for flags in itertools.product((True, False), repeat=len(KEYS)):
        values = dict(zip(KEYS, flags))
        store = _store(values)
        mine = Rules.boardOn(store.get(Rules.GROUP, Rules.MASTER), store.get(Rules.GROUP, Rules.BOARD))
        assert store.stationOn(IDS[Rules.BOARD]) is mine, values
        for key, stationId in IDS.items():
            assert store.stationOn(stationId) is (values["enabled"] and values[key]), (values, key)


def testUntouchedSwitchesAreOnAndOtherStationsAreNotOurs():
    store = _store({})
    assert all(store.get(Rules.GROUP, key) is True for key in KEYS), "开关缺省开着"
    assert all(store.stationOn(stationId) for stationId in IDS.values())
    store.set(Rules.GROUP, Rules.MASTER, False)
    assert store.stationOn("minecraft:furnace") is True, "总开关只管这一组的站点"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
