# -*- coding: utf-8 -*-
# runner: both
"""热源的游戏内自检（Server/Debug/McdkHeatTest：读一格的方块名、状态、能不能给上面热，是厨锅 / 煎锅时再读它存着的热和托盘；
摆四种炼药锅、读引擎的原始返回和服务端的三处判断、放回原样）离线跑一遍：不是测热源规则本身（那在 test_heat_sources.py / test_heat_states.py /
test_heat_conduct.py），是保证自检代码没有拼写错误、返回里的字段名和含义对得上清单里写的。客户端那一半在 test_skillet_near_heat_client.py。"""
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
    assert SELFTEST.mcdk_test_heat_cauldron_place()["error"] == "no player"


LIQUIDS = ("water", "lava", "powder_snow")


def _cauldron(aux):
    """照引擎的样子：fill_level 占低 3 位，cauldron_liquid 占上面 2 位；越界的位组合没有方块。aux 24 起抛异常（看自检记不记得下来）。"""
    if aux >= 24:
        raise ValueError("out of range")
    level, liquid = aux & 7, aux >> 3
    return None if level > 6 else {"fill_level": level, "cauldron_liquid": LIQUIDS[liquid]}


def testTheCauldronSelfTestPlacesReadsAndPutsBack():
    _setUp()
    world.auxStates["minecraft:cauldron"] = _cauldron
    world.setBlock(3, 64, 0, "minecraft:dirt", aux=2)                     # 东边 3 格原来是一块泥土：清的时候放回去
    placed = SELFTEST.mcdk_test_heat_cauldron_place(upto=26)
    assert placed["ok"] is True and placed["origin"] == (0, 64, 0) and sorted(placed["placed"]) == ["empty", "lava1", "lava6", "water6"], placed
    assert placed["placed"]["empty"]["was"] == "minecraft:dirt" and placed["placed"]["lava6"]["pos"] == (15, 64, 0)
    raw = dict((aux, value) for aux, value in placed["raw"])
    assert sorted(raw) == list(range(27)) and raw[14] == {"fill_level": 6, "cauldron_liquid": "lava"} and raw[7] is None
    assert raw[24].startswith("raise ValueError"), "抛了异常照样记下来"
    assert placed["computed"]["aux"] == [9, 10, 11, 12, 13, 14] and placed["table"] == [9, 10, 11, 12, 13, 14]
    assert placed["conditions"] == {"cauldron_liquid": "lava", "fill_level": {"min": 1}}
    assert SELFTEST.mcdk_test_heat_cauldron_place()["error"].startswith("已经摆着"), "摆着一组时不再摆第二组"
    for name, east, aux in (("empty", 3, 0), ("water6", 7, 6), ("lava1", 11, 9), ("lava6", 15, 14)):
        world.blocks[(0, east, 64, 0)]["aux"] = aux                         # 假引擎的 SetBlockStates 不改 aux：照真的引擎补上
    read = SELFTEST.mcdk_test_heat_cauldron_read()
    assert read["ok"] is True, read
    lava, water = read["cells"]["lava1"], read["cells"]["water6"]
    assert lava["name"] == "minecraft:cauldron" and lava["aux"] == 9 and lava["states"] == {"cauldron_liquid": "lava", "fill_level": 1}
    assert lava["heat_source"] is True and lava["near_cell"] is True and lava["near_heat"] is True and lava["expected"] is True
    assert water["heat_source"] is False and water["near_heat"] is False and water["ok"] is True
    cleared = SELFTEST.mcdk_test_heat_cauldron_clear()
    assert cleared["ok"] is True and len(cleared["restored"]) == 4
    assert world.blockName(3, 64, 0) == "minecraft:dirt" and world.blockName(15, 64, 0) == "minecraft:air", "放回原样"
    assert SELFTEST.mcdk_test_heat_cauldron_read()["error"].startswith("还没摆")
    world.auxStates.clear()


def testTheCauldronReadSaysWhichCellIsWrong():
    _setUp()
    SELFTEST.mcdk_test_heat_cauldron_place(upto=0)
    world.blocks[(0, 11, 64, 0)]["states"] = {"cauldron_liquid": "water", "fill_level": 1}     # 熔岩 1 级那格没摆成
    read = SELFTEST.mcdk_test_heat_cauldron_read()
    assert read["ok"] is False and read["cells"]["lava1"]["ok"] is False and read["cells"]["lava6"]["ok"] is False, "假引擎的 aux 是 0：不在表里"
    assert read["cells"]["empty"]["ok"] is True
    SELFTEST.mcdk_test_heat_cauldron_clear()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
