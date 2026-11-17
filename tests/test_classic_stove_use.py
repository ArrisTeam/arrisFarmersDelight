# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的炉灶（Server/Stove.py 右键放食物、烤好弹出、盖住 / 拆了丢东西）对 FD 的 AbstractStoveBlock / AbstractStoveBlockEntity，用假引擎驱动。

JE：放食物进 getNextEmptySlot（序号最小的空烤位），没有"下一个"的记号（AbstractStoveBlockEntity.java:157-162）；
放上去响 LANTERN_PLACE 0.5 / 1.0（AbstractStoveBlock.java:140）；烤好的从 y + 1.0 带一点随机的横向初速、往上 0.1 弹出（cookAndOutputItems:128-130）；
上面盖了东西、拆了炉灶都是 ItemUtils.dropItems：每一叠从方块里随机一点掉出来、带随机初速（Containers.dropItemStack）。
"""
from __future__ import print_function

import stovefirekit as F
import stovekit as K
from stovekit import BEEF, fake

EMPTY = {"itemDict": None, "cookTimer": 30}


def _stove(**kwargs):
    manager, data = F.setup(look=False, **kwargs)
    return data


# ---------------------------------------------------------------- 放进序号最小的空烤位

def testTheFoodGoesIntoTheLowestEmptySlotNotTheOneAfterTheLastPlaced():
    data = _stove()
    F.give("a", BEEF, 8)
    for _ in range(3):
        F.use()
    assert K.names(data) == [BEEF, BEEF, BEEF, None, None, None]
    data["1"] = EMPTY                                  # 中间那件被取走了（站点里取、手放的烤好取走……）
    F.use()
    assert K.names(data) == [BEEF, BEEF, BEEF, None, None, None], "先补 1 号，不是接着 3 号往后放"
    data["0"], data["2"] = EMPTY, EMPTY
    F.use()
    assert K.names(data) == [BEEF, BEEF, None, None, None, None], "0 号、2 号都空着：序号小的 0 号先"
    F.use()
    assert K.names(data) == [BEEF, BEEF, BEEF, None, None, None] and F.held()["count"] == 2, "放了 6 次，手里 8 -> 2"


def testWhenTheLowestSlotsAreFullTheNextOneIsTheFirstFreeAfterThem():
    data = _stove()
    for place in (0, 1, 3):
        F.lay(data, place)
    F.give("a", BEEF, 2)
    F.use()
    F.use()
    assert K.names(data) == [BEEF] * 5 + [None], "2 号、再 4 号"


# ---------------------------------------------------------------- 放上去的声音

def _played():
    return [call[2][0] for call in fake.calls if call[1] == "OnPlaySound"]


def testPlacingPlaysTheLanternPlaceSoundAtHalfVolumeInTheMiddleOfTheBlock():
    _stove()
    F.give("a", BEEF, 2)
    F.use()
    call, = _played()
    assert call["soundName"] == "block.lantern.place" and call["volume"] == 0.5, "JE 的 LANTERN_PLACE 0.5"
    assert abs(call["pitch"] - 1.0 / 1.1) < 1.0e-12, "JE 音调 1.0；原版这条声音每个采样自带 1.1，除掉才是 1.0"
    assert tuple(call["pos"]) == (K.STOVE[0] + 0.5, K.STOVE[1] + 0.5, K.STOVE[2] + 0.5)
    F.use()
    assert len(_played()) == 2, "每放一件响一声"


def testNothingPlaysWhenNothingWasPlaced():
    _stove()
    F.give("a", "minecraft:stick", 1)
    F.use()
    F.give("a", BEEF, 1)
    for place in range(6):
        F.lay(F.data(), place)
    F.use()
    assert _played() == [], "不能烤的东西、满了：不响"


if __name__ == "__main__":
    raise SystemExit(F.fdtest.run(globals()))
