# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的砧板（Server/CuttingBoard.py，没装沉浸式交互前置 / 站点关了 / 潜行右键时走的）对 FD 的 CuttingBoardBlock.use 和 CuttingBoardBlockEntity，用假引擎驱动。

JE：板空着、没插工具时 canAddItem 对任何东西都成立（ItemStackHandler 什么都收），所以什么都能摆上去；板上有东西、放不上去的（别的东西、同一种但叠满了或数据不一样）
走 processStoredItemUsingTool：板上的东西没有切法提示 invalid_item，手里的工具不对提示 invalid_tool，对了切一件、提示 remaining_items；
空手取回：创造模式取回的东西不给玩家（java:68 的 if (!player.isCreative())）。
声音：放上去 block.wood.place 1.0 / 0.8（java:84）、取回 block.wood.hit 0.25 / 0.5（:72），都在方块中心；切一件响一声（playProcessingSound：配方自带的声音 -> 剪刀 -> 刀 0.8 ->
方块的破坏声 1.0 / 0.8 -> 木头的破坏声 1.0 / 0.8），再飞 5 颗这件东西的碎屑（spawnCuttingParticles）。声音的数是 JE 的数，引擎要的数在 Shared/Rules/SoundMix（刀声要除掉采样自带的 1.5）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Board = fdtest.load("Server.CuttingBoard")

POS = (7, 64, 7)
TYPES = {"arris:iron_knife": "sword", "minecraft:iron_sword": "sword", "minecraft:iron_axe": "axe", "minecraft:cobblestone": "block", "minecraft:oak_log": "block",
         "minecraft:stone": "block", "minecraft:iron_pickaxe": "pickaxe", "minecraft:iron_hoe": "hoe", "minecraft:shears": "shears"}
CENTER = (POS[0] + 0.5, POS[1] + 0.5, POS[2] + 0.5)
INVALID_ITEM, INVALID_TOOL, NOT_STORABLE = "这东西可不能切啊……", "或许得换个工具……", "这东西放不上砧板……"


def _item(name, count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def _install():
    """fakeengine 的物品信息一律是 food：板要问工具类型、方块类型，这里按名字补。"""
    base = world._Item

    def _Item(target):
        methods = dict(base(target))
        methods["GetItemBasicInfo"] = lambda name, aux=0: {"itemType": TYPES.get(name, "food"), "maxDurability": 0, "maxStackSize": world.maxStack.get(name, 64)}
        return methods

    world._Item = _Item


_install()


def _setUp(hand=None, creative=False, board=None):
    world.reset()
    data = skilletkit.EngineData()
    if board is not None:
        data["cuttingDict"] = dict(board)
    world.setBlock(POS[0], POS[1], POS[2], "arris:cutting_board", data=data)
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    return data


def _use():
    world.runTimers()                         # 交互冷却的计时器（0.2 秒）：每次点击之间先过掉
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False}
    Board.OnServerCuttingBoardBlockUse(args)
    return args


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _hand():
    return world.players["p1"]["hand"]


# ---------------------------------------------------------------- 板空着：什么都能放

def testAnEmptyBoardTakesAnythingNotOnlyWhatCanBeCut():
    for name in ("minecraft:stick", "minecraft:bread", "minecraft:iron_sword", "minecraft:cobblestone", "arris:cabbage"):
        data = _setUp(hand=_item(name, 3))
        _use()
        assert data["cuttingDict"]["newItemName"] == name and data["cuttingDict"]["count"] == 3, name
        assert _hand() is None and _tips() == [], name


def testTheWholeStackGoesOntoTheBoardAndOnlyTheMaxStackFits():
    world.maxStack["minecraft:ender_pearl"] = 16
    data = _setUp(hand=_item("minecraft:ender_pearl", 20))
    _use()
    assert data["cuttingDict"]["count"] == 16 and _hand()["count"] == 4, "叠不过物品的最大堆叠，多的留在手里"
    data = _setUp(hand=_item("minecraft:stick", 10), board=_item("minecraft:stick", 60))
    _use()
    assert data["cuttingDict"]["count"] == 64 and _hand()["count"] == 6, "同一种接着叠，叠满为止"


def testCreativeKeepsTheStackInTheHandWhenPlacing():
    data = _setUp(hand=_item("minecraft:stick", 5), creative=True)
    _use()
    assert data["cuttingDict"]["count"] == 5 and _hand()["count"] == 5


def testWhatTheEngineCannotStoreWithTheItemIsRefusedWithATip():
    data = _setUp(hand=_item("minecraft:stick", 1, userData={"mixed": [1, "x"]}))
    _use()
    assert data["cuttingDict"] is None and _hand() is not None and _tips() == [NOT_STORABLE]


def testTheSkilletItemIsLeftToItsOwnPlacement():
    data = _setUp(hand=_item("arris:skillet_item", 1))
    _use()
    assert data["cuttingDict"] is None and _hand() is not None and _tips() == []


# ---------------------------------------------------------------- 板上有东西、放不上去：当作拿工具来切（processStoredItemUsingTool）

def testAFullStackOfWhatCanBeCutAsksForAnotherTool():
    data = _setUp(hand=_item("arris:cabbage", 1), board=_item("arris:cabbage", 64))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 64 and _hand()["count"] == 1, "叠满了的同一种：当作拿它去切自己，不是工具"


def testAFullStackOfWhatHasNoRecipeSaysItCannotBeCut():
    data = _setUp(hand=_item("minecraft:stick", 1), board=_item("minecraft:stick", 64))
    _use()
    assert _tips() == [INVALID_ITEM] and data["cuttingDict"]["count"] == 64


def testTheSameThingWithOtherDataDoesNotMergeAndGoesTheToolWay():
    data = _setUp(hand=_item("arris:cabbage", 1), board=_item("arris:cabbage", 3, extraId="marked"))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 3 and _hand()["count"] == 1, "JE 的 isSameItemSameTags 不叠，走切的那一支"


def testTheWrongToolAndTheThingNoRecipeTakesGetTheirTips():
    data = _setUp(hand=_item("minecraft:iron_axe", 1), board=_item("arris:cabbage", 2))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 2 and world.spawned == []
    data = _setUp(hand=_item("arris:iron_knife", 1), board=_item("minecraft:stick", 2))
    _use()
    assert _tips() == [INVALID_ITEM] and data["cuttingDict"]["count"] == 2 and world.spawned == []


def testTheRightToolCutsOneAndSaysHowManyAreLeft():
    data = _setUp(hand=_item("arris:iron_knife", 1), board=_item("arris:cabbage", 2))
    _use()
    assert world.spawnedNames() == [("arris:cabbage_leaf", 2)] and data["cuttingDict"]["count"] == 1 and _tips() == ["还剩1个……"]
    _use()
    assert world.spawnedNames() == [("arris:cabbage_leaf", 2)] * 2 and data["cuttingDict"] is None


def testEachCutIsReportedAsADeedAndNothingElseIs():
    # JE 在 processStoredItemUsingTool 切成以后触发 use_cutting_board：Server/Helpers/Deeds 报一声，订阅的人（成就联动）收到
    Deeds = fdtest.load("Server.Helpers.Deeds")
    seen = []

    def record(playerId, detail):
        seen.append((playerId, detail))

    Deeds.subscribe(Deeds.CUT_ON_BOARD, record)
    try:
        _setUp(hand=_item("minecraft:iron_axe", 1), board=_item("arris:cabbage", 2))
        _use()
        assert seen == [], "工具不对：没切成"
        _setUp(hand=_item("arris:iron_knife", 1), board=_item("arris:cabbage", 2))
        _use()
        _use()
        assert seen == [("p1", "arris:cabbage")] * 2
    finally:
        Deeds.unsubscribe(Deeds.CUT_ON_BOARD, record)


# ---------------------------------------------------------------- 空手取回

def testAnEmptyHandTakesTheStackBackAndCreativeDoesNotGetIt():
    data = _setUp(board=_item("arris:cabbage", 5))
    _use()
    assert data["cuttingDict"] is None and _hand()["newItemName"] == "arris:cabbage" and _hand()["count"] == 5
    data = _setUp(board=_item("arris:cabbage", 5), creative=True)
    _use()
    assert data["cuttingDict"] is None and _hand() is None, "JE CuttingBoardBlock.java:68：创造模式取回的东西不给玩家"
    data = _setUp(creative=True)
    _use()
    assert data["cuttingDict"] is None and _hand() is None, "空板空手：什么也没有"


# ---------------------------------------------------------------- 声音和碎屑

def _heard():
    """放过的声音：[(声音名, JE 的音量, JE 的音调, 位置)]。载荷里的是交给引擎的数，要乘回采样自带的（刀声 1.5）才是听到的；这里按声音名换回 JE 的数。"""
    built = {"ambient.cutting_board.knife": 1.5}
    return [(call["soundName"], call.get("volume", 1.0) * built.get(call["soundName"], 1.0), call.get("pitch", 1.0), call["pos"]) for call in world.soundArgs]


def _near(got, want):
    assert len(got) == len(want), (got, want)
    for have, expect in zip(got, want):
        assert have[0] == expect[0] and have[3] == expect[3] and abs(have[1] - expect[1]) < 1.0e-9 and abs(have[2] - expect[2]) < 1.0e-9, (have, expect)


def testPlacingPlaysWoodPlaceAtFullVolumeAndLowPitchAtTheBlockCentre():
    _setUp(hand=_item("minecraft:stick", 1))
    _use()
    _near(_heard(), [("dig.wood", 1.0, 0.8, CENTER)])


def testTakingBackPlaysWoodHitQuietAndDeepEvenInCreative():
    for creative in (False, True):
        _setUp(board=_item("arris:cabbage", 2), creative=creative)
        _use()
        _near(_heard(), [("hit.wood", 0.25, 0.5, CENTER)])


def testEachCutPlaysFarmersDelightsChain():
    cases = (("arris:iron_knife", "arris:cabbage", ("ambient.cutting_board.knife", 0.8, 1.0)),          # 刀 0.8
             ("minecraft:shears", "minecraft:leather_helmet", ("mob.sheep.shear", 1.0, 1.0)),          # 剪刀
             ("minecraft:iron_axe", "minecraft:oak_log", ("use.wood", 1.0, 1.0)),                      # 削皮：配方自带的 item.axe.strip
             ("minecraft:iron_pickaxe", "minecraft:stone", ("dig.stone", 1.0, 0.8)),                   # 被切的是方块：它的破坏声
             ("minecraft:iron_hoe", "minecraft:oak_chest_boat", ("dig.wood", 1.0, 0.8)))               # 不是方块：木头的破坏声
    for tool, item, (name, volume, pitch) in cases:
        _setUp(hand=_item(tool, 1), board=_item(item, 1))
        _use()
        _near(_heard(), [(name, volume, pitch, CENTER)])


def testTheKnifeSoundIsGivenToTheEngineWithItsOwnVolumeDividedOut():
    _setUp(hand=_item("arris:iron_knife", 1), board=_item("arris:cabbage", 1))
    _use()
    call, = world.soundArgs
    assert call["volume"] == 0.8 / 1.5 and call["pitch"] == 1.0, "定义里每个采样自带 1.5：交给引擎 0.8 / 1.5，听到的才是 FD 的 0.8"


def testNothingPlaysWhenNothingIsCutOrPlacedOrTaken():
    _setUp(hand=_item("minecraft:iron_axe", 1), board=_item("arris:cabbage", 2))
    _use()
    _setUp(hand=_item("arris:iron_knife", 1), board=_item("minecraft:stick", 2))
    _use()
    assert world.soundArgs == [] and [call for call in world.calls if call[1] == "PlayCrumbs"] == [], "提示换工具 / 不能切：没有声音也没有碎屑"


def testEveryCutThrowsCrumbsOfTheThingBeingCut():
    _setUp(hand=_item("arris:iron_knife", 1), board=_item("arris:cabbage", 2))
    _use()
    _use()
    crumbs = [call[2] for call in world.calls if call[1] == "PlayCrumbs"]
    assert crumbs == [{"dimensionId": 0, "blockPos": POS, "itemName": "arris:cabbage"}] * 2, "切一件一阵，两件两阵"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
