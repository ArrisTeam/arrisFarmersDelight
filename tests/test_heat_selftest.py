# -*- coding: utf-8 -*-
# runner: both
"""热源的游戏内自检（Server/Debug/McdkHeatTest：读一格的方块名、状态、能不能给上面热，是厨锅 / 煎锅时再读它存着的热和托盘）离线跑一遍：
不是测热源规则本身（那在 test_heat_sources.py / test_heat_conduct.py），是保证自检代码没有拼写错误、返回里的字段名和含义对得上清单里写的。"""
from __future__ import print_function

import sys

import fakeengine
import fdtest
import skilletkit

world = skilletkit.extend(fakeengine.install())
sys.modules[fakeengine.ENGINE_MODULE].GetBlockAux = lambda pos, dim: 0              # 假引擎没有这个读 aux 的入口，自检要
SELFTEST = fdtest.load("Server.Debug.McdkHeatTest")
LAVA = {"cauldron_liquid": "lava", "fill_level": 6}


def _setUp():
    world.reset()
    world.addPlayer("p1")


def testTheProbeSaysWhetherABlockIsALavaCauldronAndWhatSitsAboveItWouldFeel():
    _setUp()
    world.setBlock(10, 64, 10, "minecraft:cauldron", states=dict(LAVA))
    probed = SELFTEST.mcdk_test_heat_probe(10, 64, 10)
    assert probed["ok"] is True and probed["pos"] == (10, 64, 10) and probed["name"] == "minecraft:cauldron" and probed["states"] == LAVA, probed
    assert probed["heat_source"] is True and probed["heated_above"] is True and "stored_heat" not in probed, "不是锅：没有存着的热"
    world.setBlock(10, 64, 10, "minecraft:cauldron", states={"cauldron_liquid": "lava", "fill_level": 0})
    probed = SELFTEST.mcdk_test_heat_probe(10, 64, 10)
    assert probed["heat_source"] is False and probed["heated_above"] is False, "舀空了的不算"
    world.setBlock(10, 64, 10, "minecraft:stone")
    assert SELFTEST.mcdk_test_heat_probe(10, 64, 10)["states"] is None


def testTheProbeOfAPotOnAHopperShowsTheStoredHeatNextToWhatTheHelperWorksOutNow():
    _setUp()
    data = skilletkit.EngineData(heatEnable=True, shelfEnable=0.0)
    world.setBlock(10, 66, 10, "arris:cooking_pot", data=data)
    world.setBlock(10, 65, 10, "minecraft:hopper")
    world.setBlock(10, 64, 10, "minecraft:campfire", states={"extinguished": False})
    probed = SELFTEST.mcdk_test_heat_probe(10, 66, 10)
    assert probed["name"] == "arris:cooking_pot" and probed["below"] == "minecraft:hopper", probed
    assert probed["stored_heat"] is True and probed["stored_shelf"] == 0.0 and probed["heated_by_helper"] is True, probed
    world.setBlock(10, 64, 10, "minecraft:campfire", states={"extinguished": True})
    probed = SELFTEST.mcdk_test_heat_probe(10, 66, 10)
    assert probed["stored_heat"] is True and probed["heated_by_helper"] is False, "火灭了、锅还没刷新：两个读数对不上，就是还没轮到 HeatConduct"


def testTheProbeWithNoPlayerSaysSo():
    world.reset()
    assert SELFTEST.mcdk_test_heat_probe(0, 0, 0) == {"case": "heat_probe", "ok": False, "error": "no player"}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
