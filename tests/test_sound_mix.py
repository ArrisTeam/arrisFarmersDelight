# -*- coding: utf-8 -*-
# runner: both
"""JE 的音量、音调换成引擎的数（Shared/Rules/SoundMix.py），以及服务端放一声到客户端放出来的来回（Server/Helpers/Fx.ToAllPlayerPlaySound -> Client/Endpoints.OnPlaySound）。

引擎放一声：音量 = 声音定义里采样自带的 volume × 调用给的音量，音调同理（Strata 知识库 SOUND_ENGINE.md §0.2）。本包刀声的采样自带 1.5、下料声 2.0，
原版挂灯放置声每个采样自带音调 1.1：JE 的数要除掉那一份，听到的才是 JE 的数。
"""
from __future__ import print_function

import io
import json
import os

import boardclient
import fakeengine
import fdtest

world = fakeengine.install()
Mix = fdtest.load("Shared.Rules.SoundMix")
Fx = fdtest.load("Server.Helpers.Fx")
Endpoints = fdtest.load("Client.Endpoints")
engine = boardclient.engine

VANILLA = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla/sounds/sound_definitions.json"


def _definitions(path):
    data = json.load(io.open(path, encoding="utf-8"))
    return data.get("sound_definitions", data)


def _samples(definition):
    return [sample if isinstance(sample, dict) else {"name": sample} for sample in definition["sounds"]]


def _heard(volume, pitch, name):
    """JE 的 (volume, pitch) 经 SoundMix 交给引擎，引擎再乘上每个采样自带的数：听到的。"""
    given = Mix.engineArgs(name, volume, pitch)
    return [(given[0] * sample.get("volume", 1.0), given[1] * sample.get("pitch", 1.0))
            for sample in _samples(_definitions(os.path.join(fdtest.ROOT, "rp", "sounds", "sound_definitions.json"))[name])]


def testTheKnifeAndTheAddFoodSoundsCarryTheVolumeTheTableSays():
    own = _definitions(os.path.join(fdtest.ROOT, "rp", "sounds", "sound_definitions.json"))
    for name in ("ambient.cutting_board.knife", "ambient.skillet.addfood"):
        volume, pitch = Mix.BUILT_IN[name]
        samples = _samples(own[name])
        assert samples and all(sample.get("volume", 1.0) == volume and sample.get("pitch", 1.0) == pitch for sample in samples), name


def testEveryOwnDefinitionThatCarriesItsOwnVolumeOrPitchIsInTheOneTable():
    """本包的声音定义里，采样自带音量 / 音调（不是 1）的每一条都在 BUILT_IN 里、数一样：全包放声音只经这一张表除回去，
    原来砧板、煎锅、炉灶、厨锅各抄一份，煎锅那份漏了挂灯放置声的音调。"""
    own = _definitions(os.path.join(fdtest.ROOT, "rp", "sounds", "sound_definitions.json"))
    for name, definition in sorted(own.items()):
        values = set((sample.get("volume", 1.0), sample.get("pitch", 1.0)) for sample in _samples(definition)) if definition.get("sounds") else set()
        if values and values != set([(1.0, 1.0)]):
            assert len(values) == 1, "一条定义里的采样不一样，除不回去：" + name
            assert Mix.BUILT_IN.get(name) == values.pop(), name


def testTheLanternPlaceSoundCarriesTheVanillaPitch():
    if not os.path.exists(VANILLA):
        print("（本机没有原版资源包：挂灯放置声的音调没查）")
        return
    samples = _samples(_definitions(VANILLA)["block.lantern.place"])
    assert samples and all(sample.get("pitch", 1.0) == Mix.BUILT_IN["block.lantern.place"][1] for sample in samples)


def testWhatTheEngineMultipliesBackIsWhatJavaSays():
    assert Mix.engineArgs("ambient.cutting_board.knife", 0.8, 1.0) == (0.8 / 1.5, 1.0)
    assert Mix.engineArgs("ambient.skillet.addfood", 0.8, 1.0) == (0.4, 1.0)
    volume, pitch = Mix.engineArgs("block.lantern.place", 0.5, 1.0)
    assert volume == 0.5 and abs(pitch - 1.0 / 1.1) < 1.0e-12
    assert Mix.engineArgs("dig.wood", 1.0, 0.8) == (1.0, 0.8), "定义里什么都不自带的声音原样给"
    for volume, pitch in ((0.8, 1.0), (0.4, 0.75)):
        heard = _heard(volume, pitch, "ambient.cutting_board.knife")
        assert all(abs(got[0] - volume) < 1.0e-12 and abs(got[1] - pitch) < 1.0e-12 for got in heard), heard


def testTheServerSendsOnlyWhatWasAskedFor():
    world.soundArgs[:] = []
    Fx.ToAllPlayerPlaySound(0, (1.5, 2.5, 3.5), "random.pop")
    Fx.ToAllPlayerPlaySound(0, (1.5, 2.5, 3.5), "dig.wood", 1.0, 0.8)
    Fx.ToAllPlayerPlaySound(1, (1.5, 2.5, 3.5), "ambient.cutting_board.knife", 0.8, 1.0)
    Fx.ToAllPlayerPlaySound(0, (1.5, 2.5, 3.5), "block.lantern.place", volume=0.5)
    plain, wood, knife, lantern = world.soundArgs
    assert plain == {"soundName": "random.pop", "pos": (1.5, 2.5, 3.5), "dimensionId": 0}, "不给音量 / 音调：载荷和原来一样"
    assert (wood["volume"], wood["pitch"]) == (1.0, 0.8)
    assert knife["dimensionId"] == 1 and knife["volume"] == 0.8 / 1.5 and knife["pitch"] == 1.0
    assert lantern["volume"] == 0.5 and lantern["pitch"] == 1.0 / 1.1, "只给了音量：音调按 1"


def testTheClientPlaysItAtTheVolumeAndPitchItIsGiven():
    engine.reset()
    Endpoints.OnPlaySound({"soundName": "dig.wood", "pos": (1.5, 2.5, 3.5), "dimensionId": 0, "volume": 0.4, "pitch": 0.8})
    Endpoints.OnPlaySound({"soundName": "random.pop", "pos": (4.5, 5.5, 6.5), "dimensionId": 0})
    assert engine.played == [("dig.wood", 0.4, 0.8), ("random.pop", 1, 1)] and engine.playedAt == [(1.5, 2.5, 3.5), (4.5, 5.5, 6.5)]
    Endpoints.OnPlaySound({"soundName": "dig.wood", "pos": (1.5, 2.5, 3.5), "dimensionId": 1, "volume": 0.4, "pitch": 0.8})
    assert len(engine.played) == 2, "别的维度的声音丢掉"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
