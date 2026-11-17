# -*- coding: utf-8 -*-
# runner: both
"""熄着的炉灶（arris:stove_extinguish）：服务端的经典玩法和站点（Server/Stove.py、Server/HandGrill.py、站点逻辑，假引擎，前置包的 Manager 是真的）。
对照 JE：AbstractStoveBlock.use 放食物不看 LIT（java:66-77，tryToPlaceFoodItem 在点火 / 灭火之后、不分 LIT）；HoD 的 StoveStation.opens 不看 LIT（StoveStation.java:108-115）；
熄着时 FD 的件每刻冷却、不烤（AbstractStoveBlockEntity.serverTick:104-108，coolItems:139-150），HoD 手放的件不烤也不凉（StoveCooking.tick 的 !lit 分支）；
盖着东西的炉灶不管点没点着都把烤架上的东西丢出来（serverTick:98-102）；拆了掉东西（onRemove:195-201）。热源的两张名单不变：熄着的炉灶不给锅热。"""
from __future__ import print_function

import stovefirekit as F
import stovekit as K
from stovekit import BEEF, EGG, STICK, fake

LIT, UNLIT = F.LIT, F.UNLIT
SIDE = 10.0                                  # 手放的一面 30 / 1.5 / 2 = 10 秒


def _place(blockName, count=3, **kwargs):
    """在这个方块上用右键放一件牛肉，返回看得见的结果（点着的和熄着的要一模一样）。"""
    manager, data = F.setup(**kwargs)
    F.setBlock(blockName)
    F.give("a", BEEF, count)
    K.BlockItems.startRecording()
    args, handled = F.use()
    published = K.BlockItems.stopRecording()
    return {"items": K.items(data), "hand": F.held()["count"], "timer": data["0"]["cookTimer"],
            "shown": [payload["items"]["0"] for payload in published], "kind": [payload["kind"] for payload in published],
            "sounds": F.sounds(), "tips": list(fake.tips), "ret": args["ret"], "handled": handled, "calls": [c[1] for c in fake.calls]}


# ---------------------------------------------------------------- 经典玩法：右键放、不烤、冷却、拆了掉

def testFoodGoesOnAnUnlitStoveJustLikeOnALitOne():
    """同样的格子、同样的展示、同样的声音和提示：熄着的炉灶和点着的没有区别（JE 的 use 放食物不看 LIT）。"""
    lit, unlit = _place(LIT, look=False), _place(UNLIT, look=False)
    assert unlit == lit, (lit, unlit)
    assert unlit["items"] == [(BEEF, 1)] + [None] * 5 and unlit["hand"] == 2 and unlit["timer"] == 30
    assert unlit["shown"] == [{"newItemName": BEEF, "newAuxValue": 0, "count": 1}] and unlit["kind"] == ["stove"], "世界里的展示照样发给客户端"
    assert unlit["sounds"] == ["block.lantern.place"], "没装前置包：放上去那一声（FD 的 LANTERN_PLACE）"


def testWithThePrerequisiteTheSameOnePlacedEventGoesOutLitOrNot():
    for blockName in (LIT, UNLIT):
        manager, data = F.setup()
        F.setBlock(blockName)
        F.give("a", BEEF, 1)
        F.use()
        assert K.effects("a") == [("placed", {"places": [0]})], blockName
        assert K.names(data)[0] == BEEF and not F.sounds(), "声音由客户端的场景放，服务端不再广播"


def testSixPiecesFillTheUnlitStoveAndTheSeventhStaysInTheHand():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    F.give("a", BEEF, 8)
    for _ in range(6):
        F.use()
    assert K.items(data) == [(BEEF, 1)] * 6 and F.held()["count"] == 2
    args, _ = F.use()
    assert K.items(data) == [(BEEF, 1)] * 6 and F.held()["count"] == 2 and not fake.tips, "满了：什么也不发生（和点着的一样）"


def testTheSameTipsOnABlockedTopAndOnThingsThatCannotBeCooked():
    for blockName in (LIT, UNLIT):
        manager, data = F.setup(covered="minecraft:stone", look=False)
        F.setBlock(blockName)
        F.give("a", BEEF, 1)
        F.use()
        assert fake.tips == [("a", "炉灶上方被挡住了……")] and K.names(data) == [None] * 6, blockName
    for blockName in (LIT, UNLIT):
        manager, data = F.setup(look=False)
        F.setBlock(blockName)
        for name, tipped in (("minecraft:apple", True), (STICK, True), ("arris:cutting_board", False), ("arris:cooking_pot", False),
                             ("arris:skillet_item", False)):
            del fake.tips[:]
            F.give("a", name, 1)
            F.use()
            assert bool(fake.tips) is tipped and K.names(data) == [None] * 6, (blockName, name)
            assert not tipped or fake.tips == [("a", "这东西可不能被烹饪……")]


def testTheStovesOwnToolsAreNotToldTheyCannotBeCooked():
    """JE 里点着的炉灶拿打火石、熄着的拿铲子 / 水桶什么也不提示（PASS）；这里原来对一切不能烤的东西都提示一句。"""
    for blockName, tools in ((LIT, (F.FLINT, F.CHARGE)), (UNLIT, (F.SHOVEL, F.WATER))):
        manager, data = F.setup(look=False)
        F.setBlock(blockName)
        for name in tools:
            F.give("a", name, 1)
            args, handled = F.use()
            assert not fake.tips and not handled and not args["ret"] and F.blockName() == blockName, (blockName, name)


def testAnUnlitStoveDoesNotCookAndALitOneDoes():
    manager, data = F.setup(look=False)
    F.give("a", BEEF, 1)
    F.setBlock(LIT)
    F.use()
    K.step(31.0)
    assert K.names(data)[0] is None and "minecraft:cooked_beef" in F.groundItems(), "点着的 30 秒烤好弹出"
    manager, data = F.setup(look=False)
    del fake.spawned[:]
    F.give("a", BEEF, 1)
    F.setBlock(UNLIT)
    F.use()
    K.step(90.0)
    assert K.names(data)[0] == BEEF and data["0"]["cookTimer"] == 30 and F.groundItems() == [], "熄着的：三倍的时间也不烤、不弹出、计时纹丝不动"


def testFarmersDelightsPieceCoolsAtTwiceTheSpeedItCooksOnceTheStoveGoesOut():
    """AbstractStoveBlockEntity.coolItems：熄着时进度每刻 -2、clamp 到 [0, 总时长]；灶点着时每刻 +1。再点着接着烤（进度没丢）。"""
    manager, data = F.setup(look=False)
    F.lay(data, 0, timer=30)
    F.lay(data, 3, timer=30)
    F.setBlock(LIT)
    K.step(10.0)
    started = data["0"]["cookTimer"]
    assert abs(started - 20.0) < 0.3 and data["3"]["cookTimer"] == started, "烤了 10 秒"
    F.setBlock(UNLIT)
    K.step(2.0)
    assert abs(data["0"]["cookTimer"] - (started + 4.0)) < 0.55, "熄火的 2 秒：凉掉 4 秒的进度，不是烤"
    K.step(10.0)
    assert data["0"]["cookTimer"] == 30 and K.names(data)[0] == BEEF and F.groundItems() == [], "凉到没烤过为止就不动了，东西还在"
    F.setBlock(LIT)
    K.step(5.0)
    assert abs(data["0"]["cookTimer"] - 25.0) < 0.3, "再点着：从凉透了的地方重新烤"
    F.setBlock(UNLIT)
    K.step(0.5)
    cooled = data["0"]["cookTimer"]
    K.step(1000.0)
    assert data["0"]["cookTimer"] == 30 and cooled < 30, "越凉越高，最多回到 30"


def testOnlyWhatWasCookedCoolsAndNothingIsWrittenForTheRest():
    manager, data = F.setup(look=False)
    F.lay(data, 1, timer=12.5)
    F.setBlock(UNLIT)
    before = dict((key, data[key]) for key in ("0", "2", "3", "4", "5"))
    K.step(2.0)
    assert abs(data["1"]["cookTimer"] - 16.5) < 0.55, "2 秒凉掉 4 秒的进度：12.5 -> 16.5"
    assert dict((key, data[key]) for key in before) == before, "空位、没烤过的原封不动"


def testBreakingAnUnlitStoveDropsTheFoodAndForgetsTheStove():
    for blockName in (LIT, UNLIT):
        manager, data = F.setup()
        F.setBlock(blockName)
        F.lay(data, 0, timer=12)
        F.lay(data, 4, name="minecraft:chicken", timer=3)
        K.hand_of().grill.layByHand(4)
        K.tick()
        K.BlockItems.startRecording()
        F.EventRegistry.dispatch("BlockRemoveServerEvent", {"x": K.STOVE[0], "y": K.STOVE[1], "z": K.STOVE[2], "fullName": blockName,
                                                             "auxValue": 0, "dimension": 0}, blockName)
        published = K.BlockItems.stopRecording()
        assert sorted(F.groundItems()) == ["minecraft:beef", "minecraft:chicken"], blockName
        assert all(pos == (10.5, 64.5, 10.5) for _item, _dim, pos in fake.spawned), "在方块中心"
        assert K.HandGrill.peek(0, K.STOVE) is None and K.StoveLook._sent == {}, "手放的进度和广播记录都忘掉"
        assert len(published) == 1 and published[0]["items"] == {} and published[0]["kind"] == "stove", "客户端的展示清掉"


def testACoveredUnlitStoveThrowsItsFoodOutLikeALitOne():
    """FD 的 serverTick：有东西、上面盖了东西，不看 LIT 先全丢出来（shouldDropItems）；生的熟的、手放的 FD 的都一样。"""
    for blockName in (LIT, UNLIT):
        manager, data = F.setup(covered="arris:cooking_pot", look=False)
        F.setBlock(blockName)
        F.lay(data, 1, timer=10)
        F.lay(data, 2, name="minecraft:cooked_beef", timer=30)
        K.step(1.0)
        assert sorted(F.groundItems()) == ["minecraft:beef", "minecraft:cooked_beef"] and K.names(data) == [None] * 6, blockName


def testAStoveThatWasSetByCommandWithoutDataGetsItsDefaultsWhereItIsRead():
    """/setblock、结构放出的熄着的炉灶没走放置事件：用到时补上六个烤位的默认值。"""
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    F.give("a", BEEF, 1)
    F.use()
    assert K.items(fake.blockEntities[F.KEY]) == [(BEEF, 1)] + [None] * 5
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    K.step(1.0)
    assert fake.blockEntities[F.KEY]["5"] == {"itemDict": None, "cookTimer": 30}


def testEveryStoveHandlerIsWiredToBothBlocks():
    """按引擎事件走一遍：放置事件、右键、方块实体 tick、方块移除；不是炉灶的方块什么也不碰。"""
    manager, data = F.setup(look=False)
    F.lay(data, 0, timer=20)
    F.setBlock(UNLIT)
    args = {"dimension": 0, "posX": K.STOVE[0], "posY": K.STOVE[1], "posZ": K.STOVE[2]}
    F.tickEvent(UNLIT)
    F.tickEvent(UNLIT)
    assert data["0"]["cookTimer"] > 20, "熄着的炉灶的 tick 到了处理函数（冷却）"
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    F.EventRegistry.dispatch("ServerPlaceBlockEntityEvent", dict(args, blockName=UNLIT), UNLIT)
    assert fake.blockEntities[F.KEY]["5"] == {"itemDict": None, "cookTimer": 30}, "放置事件：新放的熄着的炉灶补上默认值"
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    F.tickEvent("minecraft:stone")
    F.tickEvent("minecraft:stone")
    assert fake.blockEntities[F.KEY]["5"] is None, "别的方块的 tick 不碰"


# ---------------------------------------------------------------- 热源

def testHeatSourcesAreUnchangedAnUnlitStoveHeatsNothingAbove():
    Heat = K.potfake.load("Server.Helpers.Heat")
    Cooking = K.fdtest.load("Shared.Data.Cooking")
    assert Heat.IsHeatSource(K.STOVE, 0, LIT) is True and Heat.IsHeatSource(K.STOVE, 0, UNLIT) is False
    F.setBlock(UNLIT)
    assert Heat.IsHeatSource(K.STOVE, 0) is False, "读方块名也一样"
    F.setBlock(LIT)
    assert Heat.IsHeatSource(K.STOVE, 0) is True
    data = K.potfake.BEData()
    assert Heat.RefreshHeat(data, (10, 65, 10), K.STOVE, 0, LIT) is True and data["heatEnable"] is True
    assert Heat.RefreshHeat(data, (10, 65, 10), K.STOVE, 0, UNLIT) is False and data["heatEnable"] is False, "熄着的灶上的锅、煎锅不热"
    assert Cooking.CanProvideHeatBlockList.count(LIT) == 1 and UNLIT not in Cooking.CanProvideHeatBlockList and Cooking.StoveList == [LIT]


# ---------------------------------------------------------------- 站点

def testTheStationOpensOnAnUnlitStoveAndFoodLaidByHandDoesNotCook():
    """HoD：站点不看 LIT 都开（StoveStation.opens）；熄着：不烤、不冒热气（StoveBehavior.heat 的 !lit），进度也不凉；点着了接着烤。"""
    manager, data = F.setup()
    F.setBlock(UNLIT)
    fake.give("a", 3, BEEF, 1)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    assert K.names(data)[:2] == [BEEF, None] and K.hand_of().grill.byHand(0), "托盘里 Shift 点的食物放在熄着的炉灶上，一样摆得上去"
    K.step(SIDE * 2, manager=manager)
    grill = K.hand_of().grill
    assert grill.down(0) == 0.0 and grill.up(0) == 0.0 and K.current()["down"][0] == 0.0, "熄着：一点不烤"
    assert data["0"]["cookTimer"] == 30 and F.groundItems() == []
    F.setBlock(LIT)
    K.step(SIDE + 0.5, manager=manager)
    assert grill.waits(0) and K.current()["down"][0] == 1.0, "点着了：烤熟贴灶那面，等着翻"
    F.setBlock(UNLIT)
    K.step(SIDE, manager=manager)
    assert grill.waits(0) and grill.down(0) == 1.0 and grill.up(0) == 0.0, "又熄了：进度不凉（HoD 的手放件冻住），还在等着翻"


def testTurningAndTakingStillWorkOnAnUnlitStove():
    manager, data = F.setup()
    F.setBlock(UNLIT)
    fake.give("a", 3, BEEF, 1)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    manager.tick(0.05)
    assert K.effects() == [("placed", {"places": [0]})]
    fake.world.time += 1.0
    assert K.do(manager, "a", K.custom("turn", place=0)) and K.effects() == [("turned", {"place": 0, "up": 0.0})], "翻面不看 LIT"
    assert K.do(manager, "a", K.custom("take", place=0)) and K.names(data)[0] is None and fake.count("a", BEEF) == 1
    assert K.effects() == [("taken", {"place": 0, "stack": {"newItemName": BEEF, "newAuxValue": 0, "count": 1}})]


def testTheOpensRuleIsTheSameLitOrUnlit():
    """HoD 的 opens：空手、能烤的、食物、刀……开；打火石、铲子、水桶、方块不开（这样才点得着、灭得了、摆得上锅）。服务端复查看的是引擎里的主手。"""
    GrillOpen = K.potfake.load("Compat.Diegesis.GrillOpen")
    for blockName in (LIT, UNLIT):
        manager, data = F.setup()
        F.setBlock(blockName)
        fake.itemTypes["arris:cooking_pot"] = "block"
        for name, opens in ((None, True), (BEEF, True), (EGG, True), ("minecraft:bread", True), (F.FLINT, False), (F.CHARGE, False),
                            (F.SHOVEL, False), (F.WATER, False), ("arris:cooking_pot", False)):
            fake.world.players["a"]["inv"][0] = None
            if name:
                F.give("a", name, 1)
            assert GrillOpen.opensStation("a", 0, K.STOVE) is opens, (blockName, name)
        fake.world.players["a"]["inv"][0] = None
        assert manager.open("a", list(K.STOVE)), blockName


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
