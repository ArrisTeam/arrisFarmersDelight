# -*- coding: utf-8 -*-
# runner: both
"""灶上东西的黑烟什么时候由 FD 放、什么时候让给炉灶站点：HoD 的 StoveSmokeMixin 在炉灶站点显示时取消 StoveBlockEntity.addSmokeParticles，
没装前置包、或 HoD 配置里关了炉灶站点（Shared/Rules/HandsOnOptions.stove）时站点不在，FD 的烟照放。
Compat/Diegesis/ClientBoot 登记炉灶站点（场景从此接管烤架）的同一处调 Client/StoveFlame.muteItemSmoke；火口的火星和噼啪声（animateTick）HoD 不碰，不看这个。
真的 ClientBoot，引擎是 bootkit 里的无害替身。"""
from __future__ import print_function

import bootkit as B
import fdtest
from optkit import Config

StoveFlame = fdtest.load("Client.StoveFlame")


class _OldKernel(object):
    API_VERSION = 2                  # 前置包比本包要的老（Presence.REQUIRED_API_VERSION 是 3）：一步也不联动


def _boot(api=None, **options):
    StoveFlame._state["muted"] = False         # 每次启动都是新进程：之前那次留下的不算
    with Config(**options):
        return B.bootClient(api)


def testWithTheStoveStationRegisteredTheStationTakesTheItemSmokeOver():
    client = _boot()
    assert client.looks["stove"] is True and B.STOVE in client.stations
    assert StoveFlame.muted() is True


def testWithTheStoveSwitchedOffInHandsOnDelightsConfigFarmersDelightsSmokeStays():
    client = _boot(stove=False)
    assert client.looks["stove"] is False and B.STOVE not in client.stations
    assert StoveFlame.muted() is False


def testWithoutThePrerequisiteFarmersDelightsSmokeStays():
    client = _boot(B.ABSENT)
    assert client.stations == [] and client.looks["stove"] is False and client.mode == B.Mode.STANDALONE
    assert StoveFlame.muted() is False


def testWithATooOldPrerequisiteFarmersDelightsSmokeStaysToo():
    client = _boot(_OldKernel)
    assert client.stations == [] and client.looks["stove"] is False and client.mode == B.Mode.OUTDATED
    assert StoveFlame.muted() is False


def testTheSmokeIsMutedExactlyWhenTheStoveSceneIsOnForEveryCombinationOfTheOtherSwitches():
    for pot in (True, False):
        for skillet in (True, False):
            for stove in (True, False):
                client = _boot(cooking_pot=pot, skillet=skillet, stove=stove)
                assert StoveFlame.muted() is client.looks["stove"] is stove, (pot, skillet, stove)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
