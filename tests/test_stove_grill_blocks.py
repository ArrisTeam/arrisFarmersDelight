# -*- coding: utf-8 -*-
# runner: both
"""炉灶的两种方块（Shared/Rules/GrillBlocks.py）：点着的是 arris:stove，熄着的是另一个方块 arris:stove_extinguish。
对照 JE：AbstractStoveBlock.use 放食物不看 LIT、HoD 的 StoveStation.opens 不看 LIT；熄着时 FD 的件每刻冷却（AbstractStoveBlockEntity.coolItems）；
点火 / 灭火的东西（AbstractStoveBlock.tryToIgnite / tryToExtinguish）。对外的 StoveList / CanProvideHeatBlockList（linkage.md）不动。"""
from __future__ import print_function

import dgtest
import fdtest

Blocks = fdtest.load("Shared.Rules.GrillBlocks")
Cooking = fdtest.load("Shared.Data.Cooking")
Contract = fdtest.load("Api.LegacyModAttr")
Station = fdtest.load("Shared.Rules.GrillStation")

LIT, UNLIT = "arris:stove", "arris:stove_extinguish"
TOTAL = 30                                  # Server/Stove.COOK_TIMER：JE 营火配方的 600 刻
TICKS_PER_SECOND = 20


def testTheStoveIsTwoBlocksAndEveryoneAgreesWhichIsWhich():
    assert Blocks.UNLIT_OF == {LIT: UNLIT} and Blocks.LIT_OF == {UNLIT: LIT}
    assert Blocks.isLit(LIT) and not Blocks.isLit(UNLIT)
    assert Blocks.isUnlit(UNLIT) and not Blocks.isUnlit(LIT)
    assert Blocks.isGrill(LIT) and Blocks.isGrill(UNLIT), "点着的、熄着的都能摆烤位"
    for other in (None, "", "minecraft:stone", "arris:skillet", "arris:cooking_pot", "arris:cutting_board", "minecraft:campfire"):
        assert not Blocks.isGrill(other) and not Blocks.isLit(other) and not Blocks.isUnlit(other), other
    assert Blocks.twinOf(LIT) == UNLIT and Blocks.twinOf(UNLIT) == LIT, "点火 / 灭火换成对面那个"
    assert Blocks.twinOf("minecraft:stone") is None and Blocks.twinOf(None) is None


def testThePublicListsAreUntouchedAndTheUnlitBlockIsNotInThem():
    """linkage.md：StoveList 是"会烤食物的炉灶（点燃状态）"，CanProvideHeatBlockList 是"可以提供火源的方块"：下游按引用读。
    熄着的炉灶不烤、不给锅热，不能进这两张表；它是另一个概念（灶方块）。"""
    assert Cooking.StoveList == [LIT], "内容不变"
    assert UNLIT not in Cooking.StoveList and UNLIT not in Cooking.CanProvideHeatBlockList and LIT in Cooking.CanProvideHeatBlockList
    assert Contract.ArrisFarmersDelightObtain("StoveList") is Cooking.StoveList, "对象身份不变：下游拿到的就是这个列表"
    assert Contract.ArrisFarmersDelightObtain("CanProvideHeatBlockList") is Cooking.CanProvideHeatBlockList
    assert list(Contract.ArrisFarmersDelightObtain("StoveList")) == [LIT]
    list(Blocks.GRILL_BLOCKS), LIT in Blocks.GRILL_BLOCKS, Blocks.isGrill(UNLIT)       # 问几遍也不改它们
    assert Cooking.StoveList == [LIT] and UNLIT not in Cooking.CanProvideHeatBlockList


def testTheGrillContainerIsLiveSoDownstreamStovesStillWork():
    """前置包登记站点只用 in（Station.binds / Registry.behaviorOf）：下游往 StoveList 追加的炉灶照旧开站，熄着的孪生方块也开站。"""
    grill = Blocks.GRILL_BLOCKS
    assert LIT in grill and UNLIT in grill and "minecraft:stone" not in grill and None not in grill
    assert list(grill) == [LIT, UNLIT]
    Contract.ArrisFarmersDelightInterface("StoveList", "addon:big_stove")
    try:
        assert "addon:big_stove" in grill and Blocks.isLit("addon:big_stove") and Blocks.isGrill("addon:big_stove")
        assert Blocks.twinOf("addon:big_stove") is None, "下游的炉灶没有熄着的孪生方块：点不灭、灭不了，照旧只有点着的"
        assert not Blocks.isUnlit("addon:big_stove")
        assert list(grill) == [LIT, "addon:big_stove", UNLIT]
        assert Blocks.useOf(True, "minecraft:water_bucket", "bucket") is not None, "规则只说东西能不能灭火；有没有孪生方块是 twinOf 的事"
    finally:
        Cooking.StoveList.remove("addon:big_stove")
    assert "addon:big_stove" not in grill and list(grill) == [LIT, UNLIT]


def testThePrerequisiteBindsTheStationToBothBlocksThroughItsPlainInCheck():
    """前置包登记站点只对 blocks 用 in：服务端 StationType.binds / Registry.stationTypeOf，客户端 Registry.behaviorOf（真的前置包模块，纯 Python）。
    GrillStation.STOVE_BLOCKS 就是 GrillView.register / GrillLogic.register 交给它的东西。"""
    serverStations, clientBehaviors = dgtest.load("Server.Registry"), dgtest.load("Client.Registry")
    serverStations.clearAll()
    clientBehaviors.clearAll()
    serverStations.registerStation(dgtest.load("Server.Station").StationType(Station.STATION_ID, Station.STOVE_BLOCKS))
    clientBehaviors.registerBehavior(Station.STATION_ID, Station.STOVE_BLOCKS, object)
    try:
        for name in (LIT, UNLIT):
            assert serverStations.stationTypeOf(name).stationId == "arris:stove", name
            assert clientBehaviors.behaviorOf(name).stationId == "arris:stove", name
        assert serverStations.stationTypeOf("minecraft:stone") is None and clientBehaviors.behaviorOf("minecraft:stone") is None
        Cooking.StoveList.append("addon:big_stove")
        try:
            assert serverStations.stationTypeOf("addon:big_stove") is not None and clientBehaviors.behaviorOf("addon:big_stove") is not None
        finally:
            Cooking.StoveList.remove("addon:big_stove")
        assert serverStations.stationTypeOf("addon:big_stove") is None and clientBehaviors.behaviorOf("addon:big_stove") is None
    finally:
        serverStations.clearAll()
        clientBehaviors.clearAll()


# ---------------------------------------------------------------- 冷却

def _javaCool(progress, ticks):
    """AbstractStoveBlockEntity.coolItems 一刻一刻照抄：进度 <= 0 不动，否则 clamp(进度 - 2, 0, 总时长)。"""
    for _ in range(ticks):
        if progress <= 0:
            continue
        progress = min(max(progress - 2, 0), TOTAL * TICKS_PER_SECOND)
    return progress


def testCoolingFollowsFarmersDelightsRuleTickByTick():
    """进度（刻）每刻 -2、不低于 0；我们的计时是"还剩几秒烤好"（30 秒烤好），按真实时间：每秒凉 2 秒。逐个起点、逐个时长和 Java 的整数刻比。"""
    for progressTicks in (0, 1, 2, 3, 40, 199, 200, 599, 600):
        for ticks in (0, 1, 2, 5, 20, 100, 300, 301, 400):
            timer = TOTAL - progressTicks / float(TICKS_PER_SECOND)
            ours = Blocks.cooledTimer(timer, ticks / float(TICKS_PER_SECOND), TOTAL)
            java = _javaCool(progressTicks, ticks)
            assert abs((TOTAL - ours) * TICKS_PER_SECOND - java) < 1.0e-6, (progressTicks, ticks, ours, java)


def testItCoolsTwiceAsFastAsItCooksAndNeverPastNothingCookedYet():
    assert Blocks.COOL_PER_SECOND == 2.0
    assert Blocks.cooledTimer(20.0, 1.0, TOTAL) == 22.0, "烤了 10 秒的件，熄着一秒凉掉 2 秒"
    assert Blocks.cooledTimer(29.5, 0.25, TOTAL) == 30, "凉到没烤过为止：不会比总时长还长（clamp 的上界）"
    assert Blocks.cooledTimer(30, 5.0, TOTAL) == 30 and Blocks.cooledTimer(31, 5.0, TOTAL) == 31, "没烤过的（进度 <= 0）不动（FD 的 continue）"
    assert Blocks.cooledTimer(None, 1.0, TOTAL) == TOTAL, "没有计时：当没烤过"
    assert Blocks.cooledTimer(0.5, 0.0, TOTAL) == 0.5, "过了零秒什么也不变"
    timer, steps = 0.25, 0
    while timer < TOTAL:
        timer, steps = Blocks.cooledTimer(timer, 0.25, TOTAL), steps + 1
    assert timer == TOTAL and steps == 60, "几乎烤好的件：30 秒的进度要 15 秒凉完（每步 0.25 秒 -> 每步 +0.5）"


# ---------------------------------------------------------------- 点火 / 灭火

def testWhichItemsLightAnUnlitStoveAndWhichPutOutALitOne():
    """AbstractStoveBlock.use：点着的先看 tryToExtinguish（铲子 SHOVEL_DIG、水桶），熄着的先看 tryToIgnite（打火石、火焰弹）。"""
    assert Blocks.useOf(False, "minecraft:flint_and_steel", "") == (Blocks.IGNITE, Blocks.WEAR, "fire.ignite")
    assert Blocks.useOf(False, "minecraft:fire_charge", "") == (Blocks.IGNITE, Blocks.SPEND, "mob.ghast.fireball")
    assert Blocks.useOf(True, "minecraft:iron_shovel", "shovel") == (Blocks.EXTINGUISH, Blocks.WEAR, "random.fizz")
    assert Blocks.useOf(True, "arris:modded_shovel", "shovel")[0] == Blocks.EXTINGUISH, "按物品类型认铲子（ToolActions.SHOVEL_DIG），模组的铲子也算"
    assert Blocks.useOf(True, "minecraft:water_bucket", "bucket") == (Blocks.EXTINGUISH, Blocks.EMPTY, "random.fizz")
    for lit in (True, False):
        for name, kind in (("minecraft:stick", ""), ("minecraft:iron_pickaxe", "pickaxe"), ("minecraft:lava_bucket", "bucket"),
                           ("minecraft:milk_bucket", "bucket"), ("minecraft:beef", "food"), ("minecraft:bucket", "bucket"), ("", ""), (None, None)):
            assert Blocks.useOf(lit, name, kind) is None, (lit, name)
    assert Blocks.useOf(True, "minecraft:flint_and_steel", "") is None and Blocks.useOf(True, "minecraft:fire_charge", "") is None, "点着的拿打火石：不是它的事"
    assert Blocks.useOf(False, "minecraft:iron_shovel", "shovel") is None and Blocks.useOf(False, "minecraft:water_bucket", "bucket") is None, "熄着的拿铲子、水桶：也不是"


def testTheStovesOwnToolsAreNeverTheThingThatCannotBeCooked():
    for name, kind in (("minecraft:flint_and_steel", ""), ("minecraft:fire_charge", ""), ("minecraft:iron_shovel", "shovel"), ("minecraft:water_bucket", "bucket")):
        assert Blocks.isTool(name, kind), name
    for name, kind in (("minecraft:stick", ""), ("minecraft:beef", "food"), ("minecraft:iron_pickaxe", "pickaxe"), ("minecraft:lava_bucket", "bucket")):
        assert not Blocks.isTool(name, kind), name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
