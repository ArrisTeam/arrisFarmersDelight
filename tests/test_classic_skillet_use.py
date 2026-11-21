# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的煎锅（Server/Skillet.py 的右键放食物 / 空手取回，没装场景交互前置 / 站点关了时走的）对 FD 的 SkilletBlock.use 和 SkilletBlockEntity.addItemToCook，用假引擎驱动。

JE：addItemToCook 把手里的食物 insertItem 进锅里那一格（ItemStackHandler）：空着、或是同一种（isSameItemSameTags）就放进去，叠到一叠的最大数量为止，剩下的留在手里；
放进去了（数量变了）才算成功，成功一次这一件的进度从头算（cookingTime = 0）；放不进去什么也不发生；含水的提示 underwater，没有营火配方的提示 invalid_item。
成功放进去响一声 LANTERN_PLACE 0.7 / 1.0（SkilletBlock.java:83），锅原本是空的又在热源上再响一声 add_food 0.8 / 1.0（SkilletBlockEntity.java:188-190）；
空手取回没有声音，创造模式取下来的东西不给玩家（SkilletBlock.java:71-77，东西直接没了）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Skillet = fdtest.load("Server.Skillet")
Mix = fdtest.load("Shared.Rules.SoundMix")

POS = (7, 64, 7)
CENTER = (POS[0] + 0.5, POS[1] + 0.5, POS[2] + 0.5)
UNDERWATER, INVALID = "被水泡着可没法烹饪啊……", "这东西可不能被烹饪……"


def _item(name, count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def _setUp(hand=None, creative=False, pan=None, heated=True, below="minecraft:campfire"):
    world.reset()
    data = skilletkit.EngineData(heatEnable=heated)
    if pan is not None:
        data["cookingDict"] = dict(pan)
    world.setBlock(POS[0], POS[1], POS[2], "arris:skillet", data=data)
    world.setBlock(POS[0], POS[1] - 1, POS[2], below)
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    return data


def _use():
    world.runTimers()
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False}
    Skillet.OnServerSkilletBlockUse(args)
    return args


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _hand():
    return world.players["p1"]["hand"]


def _published():
    """方块上东西变了的广播里这口锅的内容。"""
    return [call[2]["items"]["0"] for call in world.calls if call[1] == "OnBlockItems"]


# ---------------------------------------------------------------- 放进占着的锅：同种合并

def testMoreOfTheSameFoodMergesIntoAnOccupiedPan():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2))
    data["cookTimer"] = 2.5
    _use()
    assert data["cookingDict"]["count"] == 5 and data["cookingDict"]["newItemName"] == "minecraft:beef"
    assert _hand() is None and _tips() == []
    assert data["cookTimer"] == 7.0, "放进去一次，这一件的进度从头算（JE 的 cookingTime = 0）"
    assert _published() == [{"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 5}], "客户端按新的数量重画"


def testMergingStopsAtTheMaxStackAndTheRestStaysInTheHand():
    data = _setUp(hand=_item("minecraft:beef", 10), pan=_item("minecraft:beef", 60))
    _use()
    assert data["cookingDict"]["count"] == 64 and _hand()["count"] == 6
    world.maxStack["minecraft:chicken"] = 16
    data = _setUp(hand=_item("minecraft:chicken", 20))
    _use()
    assert data["cookingDict"]["count"] == 16 and _hand()["count"] == 4, "空锅也不超过物品的最大堆叠"


def testAFullPanTakesNothingMoreAndNothingHappens():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 64))
    data["cookTimer"] = 2.5
    _use()
    assert data["cookingDict"]["count"] == 64 and _hand()["count"] == 3 and data["cookTimer"] == 2.5
    assert _tips() == [] and world.soundArgs == [] and _published() == [], "放不进去：没有提示、没有声音、进度不动"


def testADifferentKindOrDifferentDataDoesNotMerge():
    data = _setUp(hand=_item("minecraft:chicken", 3), pan=_item("minecraft:beef", 2))
    _use()
    assert data["cookingDict"]["newItemName"] == "minecraft:beef" and data["cookingDict"]["count"] == 2 and _hand()["count"] == 3 and _tips() == []
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2, extraId="marked"))
    _use()
    assert data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "JE 的 isSameItemSameTags：数据不一样不叠"
    data = _setUp(hand=_item("minecraft:beef", 3, newAuxValue=5), pan=_item("minecraft:beef", 2))
    _use()
    assert data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "aux 不一样也不叠"


def testCreativeMergesWithoutUsingUpTheStack():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2), creative=True)
    _use()
    assert data["cookingDict"]["count"] == 5 and _hand()["count"] == 3


def testAnOccupiedPanInTheWaterStillSaysUnderwater():
    data = _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2))
    world.water.add((0,) + POS)
    _use()
    assert _tips() == [UNDERWATER] and data["cookingDict"]["count"] == 2 and _hand()["count"] == 3, "JE 先看含水（addItemToCook），再看放不放得进去"


def testAnEmptyPanStillTakesTheWholeStack():
    data = _setUp(hand=_item("minecraft:beef", 5))
    _use()
    assert data["cookingDict"]["count"] == 5 and _hand() is None and data["cookTimer"] == 7.0


# ---------------------------------------------------------------- 声音

def _heard():
    """放过的声音：[(声音名, JE 的音量, JE 的音调, 位置)]。载荷里是交给引擎的数，乘回采样自带的（SoundMix.BUILT_IN）才是听到的。"""
    out = []
    for call in world.soundArgs:
        builtVolume, builtPitch = Mix.BUILT_IN.get(call["soundName"], (1.0, 1.0))
        out.append((call["soundName"], round(call.get("volume", 1.0) * builtVolume, 9), round(call.get("pitch", 1.0) * builtPitch, 9), call["pos"]))
    return out


def testTheFirstFoodOnAHotEmptyPanPlaysTheAddFoodSoundThenTheLanternPlace():
    _setUp(hand=_item("minecraft:beef", 3))
    _use()
    assert _heard() == [("ambient.skillet.addfood", 0.8, 1.0, CENTER), ("block.lantern.place", 0.7, 1.0, CENTER)], "JE：下料 0.8、挂灯 0.7，都在方块中心"


def testOnAColdPanOrWhenMergingOnlyTheLanternPlacePlays():
    _setUp(hand=_item("minecraft:beef", 3), heated=False, below="minecraft:stone")
    _use()
    assert _heard() == [("block.lantern.place", 0.7, 1.0, CENTER)], "锅是空的但不在热源上：只有挂灯"
    _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 2))
    _use()
    assert _heard() == [("block.lantern.place", 0.7, 1.0, CENTER)], "锅里已经有东西（合并）：只有挂灯"


def testTheEngineGetsTheNumbersWithTheSamplesOwnVolumeAndPitchDividedOut():
    _setUp(hand=_item("minecraft:beef", 1))
    _use()
    addFood, lantern = world.soundArgs
    assert addFood["volume"] == 0.4 and addFood["pitch"] == 1.0, "下料声的采样自带 2.0，0.8 要给 0.4"
    assert lantern["volume"] == 0.7 and abs(lantern["pitch"] - 1.0 / 1.1) < 1.0e-12, "原版挂灯放置声的采样自带音调 1.1，JE 的 1.0 要给 1 / 1.1"


def testNothingPlaysWhenNothingWasAdded():
    _setUp(hand=_item("minecraft:chicken", 3), pan=_item("minecraft:beef", 2))
    _use()
    _setUp(hand=_item("minecraft:beef", 3), pan=_item("minecraft:beef", 64))
    _use()
    _setUp(hand=_item("minecraft:beef", 3))
    world.water.add((0,) + POS)
    _use()
    _setUp(hand=_item("minecraft:stick", 1))
    _use()
    assert world.soundArgs == []


def testTakingTheFoodBackPlaysNothing():
    data = _setUp(pan=_item("minecraft:beef", 2))
    _use()
    assert data["cookingDict"] is None and _hand()["count"] == 2 and world.soundArgs == [], "JE 取回没有 playSound"


# ---------------------------------------------------------------- 空手取回

def testAnEmptyHandTakesTheWholeStackBackAndCreativeDoesNotGetIt():
    data = _setUp(pan=_item("minecraft:beef", 5))
    _use()
    assert data["cookingDict"] is None and _hand()["newItemName"] == "minecraft:beef" and _hand()["count"] == 5
    data = _setUp(pan=_item("minecraft:beef", 5), creative=True)
    _use()
    assert data["cookingDict"] is None and _hand() is None, "JE SkilletBlock.java:73：创造模式取下来的东西不给玩家，就这么没了"
    assert _published()[-1] == {}, "锅里清空了，客户端的展示也清掉"


# ---------------------------------------------------------------- 手里的东西不再对着锅用出去（JE SkilletBlock.use：方块实体在就 SUCCESS / CONSUME）

def _useItemOn(hand, sneaking=False):
    """对着放下的煎锅用手里的东西：引擎先发方块使用（放食物、提示），再发物品使用（ServerItemUseOnEvent：ret 为真就不再用出去）。"""
    _setUp(hand=hand)
    if sneaking:
        world.sneaking.add("p1")
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "entityId": "p1", "itemDict": dict(hand), "ret": False}
    return Skillet.OnUseItemOnPlacedSkillet(args), args


def testWhatIsHeldIsNotUsedOnThePlacedSkillet():
    # 实机（2026-11-21，不装前置包）：拿着石头右键放下的煎锅，提示之后石头还放到了锅上；水桶倒出水、打火石在锅上点火、刷怪蛋出了一头猪。
    # 方块使用的 cancel 拦不住（实机量过），要在物品使用上 ret：这一下归煎锅，后面的物品使用处理也不再看（返回真）
    for name in ("minecraft:stone", "minecraft:water_bucket", "minecraft:flint_and_steel", "minecraft:pig_spawn_egg", "arris:skillet_item",
                 "minecraft:beef"):
        handled, args = _useItemOn(_item(name))
        assert args["ret"] is True and handled is True, name


def testSneakingLeavesTheHeldItemToItsOwnUse():
    # 潜行拿着东西时原版不调方块的 use（JE 同）：方块放到锅旁边、潜行拿煎锅是再放一口锅（Server/SkilletItem.py），照常
    for name in ("minecraft:stone", "arris:skillet_item"):
        handled, args = _useItemOn(_item(name), sneaking=True)
        assert args["ret"] is False and handled is None, name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
