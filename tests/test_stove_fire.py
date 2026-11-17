# -*- coding: utf-8 -*-
# runner: both
"""炉灶点火 / 灭火（Server/StoveFire.py + Server/StoveSwap.py，假引擎，事件走真的 EventRegistry）对照 JE 的 AbstractStoveBlock.use / tryToIgnite / tryToExtinguish /
ignite / extinguish（FD AbstractStoveBlock.java:66-164）：点着的先看灭火（铲子、水桶），熄着的先看点火（打火石、火焰弹），用上了就不再放食物；
点火 / 灭火只改 LIT，方块实体不动：烤位上的东西、烤到哪、朝向都在。基岩版点着和熄着是两个方块，所以换方块、数据原样带过去。
引擎事件的先后离线定不了（stovefirekit：sync / late / silent，方块实体 now / later / never），每一种都要兜住：东西不丢、不重复、不被"拆了"的处理丢出来。"""
from __future__ import print_function

import copy

import stovefirekit as F
import stovekit as K
from stovekit import BEEF, fake

F.potfake.load("Server.StoveFire")             # 导入即登记点火 / 灭火的处理函数（ServerItemUseOnEvent，优先级 11）

LIT, UNLIT = F.LIT, F.UNLIT
CHICKEN, COOKED = "minecraft:chicken", "minecraft:cooked_beef"
SCENARIOS = (("sync", "now"), ("late", "now"), ("sync", "later"), ("late", "later"), ("silent", "now"))


def _seed(data, handLaid=True):
    """一座有东西的炉灶：0 号 FD 原样烤了 17.5 秒、2 号手放的（贴灶面烤了一小半）、5 号烤好的成品。返回炉灶自己的键的快照。"""
    F.lay(data, 0, BEEF, timer=12.5)
    F.lay(data, 2, CHICKEN, timer=30)
    F.lay(data, 5, COOKED, timer=30)
    if handLaid:
        hand = K.hand_of()
        hand.grill.layByHand(2)
        hand.grill.grill(2, 0.4)
        K.HandGrill.save(hand, data)
    return F.kept(data)


def _light(creative=None, durability=65, item=F.FLINT):
    F.give("a", item, 1, durability=durability, creative=creative)
    return F.use()


def _sameFood(blockEntityData, before):
    """快照里的东西都在原来的烤位上（点着 / 熄着之后炉灶接着走了几步，计时和手放的进度已经变了一点，所以不逐个键比）。"""
    now = F.kept(blockEntityData)
    assert sorted(now) == sorted(before)
    for place in range(6):
        was, is_ = before.get(str(place)), now.get(str(place))
        assert (was["itemDict"] if was else None) == (is_["itemDict"] if is_ else None), place


# ---------------------------------------------------------------- 点火 / 灭火本身

def testFlintAndSteelLightsAnUnlitStoveAndNothingOnItIsTouched():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    F.facing(3)
    before = _seed(data)
    hand = K.hand_of()
    K.BlockItems.startRecording()
    args, handled = _light()
    published = K.BlockItems.stopRecording()
    assert F.blockName() == LIT and handled is True and args["ret"] is True, "点着了；认领这次点击；引擎自己那一下（放火）不要"
    assert F.kept(F.data()) == before, "六个烤位、手放的进度一样不少地带了过来"
    assert fake.blockAux[F.KEY] == 3 and fake.states[F.KEY]["direction"] == 3, "朝向原样写回去"
    assert F.groundItems() == [] and K.HandGrill.peek(0, K.STOVE) is hand, "没有掉东西，手放的进度对象还是原来那个"
    assert F.held()["durability"] == 64 and F.held()["count"] == 1, "打火石磨损 1 点（hurtAndBreak）"
    assert F.sounds() == ["fire.ignite"] and not fake.tips
    assert published[-1]["kind"] == "stove" and published[-1]["items"]["0"]["newItemName"] == BEEF and published[-1]["items"]["5"]["newItemName"] == COOKED, \
        "客户端的展示按带过来的东西重发"


def testFireChargeLightsItAndIsSpentOutsideCreativeOnly():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    before = _seed(data)
    fake.give("a", 0, F.CHARGE, 3)
    args, handled = F.use()
    assert F.blockName() == LIT and handled and F.held()["count"] == 2 and F.sounds() == ["mob.ghast.fireball"] and F.kept(F.data()) == before
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    F.give("a", F.CHARGE, 3, creative=True)
    F.use()
    assert F.blockName() == LIT and F.held()["count"] == 3, "创造模式不少（JE 的 instabuild）"


def testAShovelPutsOutALitStoveAndTheFoodStays():
    manager, data = F.setup(look=False)
    F.facing(1)
    before = _seed(data)
    F.give("a", F.SHOVEL, 1, durability=200)
    args, handled = F.use()
    assert F.blockName() == UNLIT and handled and args["ret"], "灭了"
    assert F.kept(F.data()) == before and fake.blockAux[F.KEY] == 1 and fake.states[F.KEY]["direction"] == 1
    assert F.held()["durability"] == 199 and F.sounds() == ["random.fizz"] and F.groundItems() == []


def testAWaterBucketPutsItOutAndTurnsIntoAnEmptyBucketOutsideCreativeOnly():
    manager, data = F.setup(look=False)
    before = _seed(data)
    F.give("a", F.WATER, 1)
    args, handled = F.use()
    assert F.blockName() == UNLIT and handled and args["ret"] and F.kept(F.data()) == before, "水桶：灭火，引擎自己的倒水不要"
    assert F.held() == {"newItemName": F.BUCKET, "newAuxValue": 0, "count": 1}, "非创造模式换成空桶（getCraftingRemainingItem）"
    manager, data = F.setup(look=False)
    F.give("a", F.WATER, 1, creative=True)
    F.use()
    assert F.blockName() == UNLIT and F.held()["newItemName"] == F.WATER, "创造模式水桶还是满的"


def testCreativeModeWearsNothing():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    _light(creative=True, durability=65)
    assert F.blockName() == LIT and F.held()["durability"] == 65
    F.give("a", F.SHOVEL, 1, durability=200, creative=True)
    F.use()
    assert F.blockName() == UNLIT and F.held()["durability"] == 200


def testAnItemThatCannotBreakIsNotWornOut():
    """网易的物品字典里不会坏的东西耐久是 0：照着减会把它"用坏"。只碰有最大耐久的。"""
    manager, data = F.setup(look=False)
    fake.itemTypes["modded:shovel"] = "shovel"
    F.give("a", "modded:shovel", 1, durability=0)
    F.use()
    assert F.blockName() == UNLIT and F.held() == {"newItemName": "modded:shovel", "newAuxValue": 0, "count": 1, "durability": 0}, "模组的铲子也能灭火，不会坏的不磨"


def testAWornOutFlintBreaksAndTheStoveIsStillLit():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    _light(durability=1)
    assert F.blockName() == LIT and F.held() is None and F.sounds() == ["fire.ignite", "random.break"], "最后一点耐久用掉：破碎声，手空了"


def testTheWrongToolOrTheWrongStateDoesNothingAndFallsThrough():
    for blockName, tool in ((LIT, F.FLINT), (LIT, F.CHARGE), (UNLIT, F.SHOVEL), (UNLIT, F.WATER), (LIT, F.PICK), (UNLIT, F.PICK)):
        manager, data = F.setup(look=False)
        F.setBlock(blockName)
        before = _seed(data)
        fake.itemTypes[F.PICK] = "pickaxe"
        F.give("a", tool, 1, durability=10)
        args, handled = F.use()
        assert F.blockName() == blockName and not handled and not args["ret"] and F.kept(F.data()) == before, (blockName, tool)
        assert F.held()["durability"] == 10 and not F.sounds(), (blockName, tool)


def testSneakingWithAnItemIsTheItemsOwnUseNotTheStoves():
    """原版 useItemOn：潜行拿着东西右键不调方块的 use（shouldSneakBypass）：打火石照样放火、水桶照样倒水，炉灶不点不灭。"""
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    fake.sneaking.add("a")
    args, handled = _light()
    assert F.blockName() == UNLIT and not handled and not args["ret"] and F.held()["durability"] == 65
    fake.sneaking.discard("a")
    args, handled = F.use()
    assert F.blockName() == LIT and handled, "不潜行就点着了"


def testADownstreamStoveHasNoTwinSoItNeitherGoesOutNorGetsTouched():
    """下游往 StoveList 追加的炉灶没有熄着的孪生方块：照旧只有点着的，铲子、水桶什么也不发生（原来怎样还怎样）。"""
    Cooking = K.fdtest.load("Shared.Data.Cooking")
    Cooking.StoveList.append("addon:big_stove")
    try:
        manager, data = F.setup(look=False)
        F.setBlock("addon:big_stove")
        before = _seed(data)
        F.give("a", F.SHOVEL, 1, durability=10)
        args, handled = F.use()
        assert F.blockName() == "addon:big_stove" and not handled and not args["ret"] and F.kept(F.data()) == before
        assert F.held()["durability"] == 10 and not fake.tips, "拿的是炉灶自己的工具：不提示不能烹饪，也不拦"
        F.give("a", BEEF, 1)
        F.use()
        assert K.names(data).count(BEEF) == 2, "放食物照旧（Stove.py 的处理认下游的炉灶）"
    finally:
        Cooking.StoveList.remove("addon:big_stove")


def testHoldingTheButtonDoesNotToggleItAgain():
    """按住右键引擎每刻重发：冷却里的重发也要取消引擎自己那一下，但不会再点、再灭。"""
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    F.give("a", F.FLINT, 1, durability=65)
    args, handled = F.use()
    assert F.blockName() == LIT
    F.setBlock(UNLIT)
    args, handled = F.use(cooldown=True)
    assert F.blockName() == UNLIT and handled and args["ret"] and F.held()["durability"] == 64, "冷却里：认领了，什么也不做，不磨损"


def testAnUnloadedStoveIsNeitherChangedNorChargedFor():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    before = _seed(data)
    fake.failSet = True
    args, handled = _light()
    assert F.blockName() == UNLIT and handled and F.kept(F.data()) == before and F.held()["durability"] == 65 and not F.sounds()
    assert F.StoveSwap._swaps == {}, "没换成：不留记录"


def testTheFoodStillGoesOnAfterTheToolWasNotTheirs():
    """优先级：点火 / 灭火（11）在放食物（10）前面；拿着食物就是放食物。"""
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    F.give("a", BEEF, 2)
    args, handled = F.use()
    assert F.blockName() == UNLIT and K.names(data)[0] == BEEF and F.held()["count"] == 1
    order = [name for _module, name in F.EventRegistry.handlerNames("ServerItemUseOnEvent")]
    assert order.index("OnStoveFire") < order.index("OnServerStoveItemUse"), "点火 / 灭火先于放食物"


# ---------------------------------------------------------------- 引擎事件的先后

def testEveryOrderOfTheEngineEventsKeepsTheFood():
    """sync / late / silent 的事件、方块实体 now / later：换方块的东西一份不少、不重复，旧方块的移除事件不把它们丢到地上、不忘掉手放的进度。"""
    for events, entity in SCENARIOS:
        for start, tool, goal in ((UNLIT, F.FLINT, LIT), (LIT, F.SHOVEL, UNLIT)):
            manager, data = F.setup(events=events, entity=entity, look=False)
            F.setBlock(start)
            F.facing(2)
            before = _seed(data)
            hand = K.hand_of()
            fake.itemTypes[F.SHOVEL] = "shovel"
            F.give("a", tool, 1, durability=65)
            F.use()
            F.flush()
            where = (events, entity, start)
            assert F.blockName() == goal, where
            assert F.kept(F.data()) == before, where
            assert F.groundItems() == [] and K.HandGrill.peek(0, K.STOVE) is hand, where
            assert fake.blockAux[F.KEY] == 2, where
            F.runTimers()
            assert F.groundItems() == [] and F.StoveSwap._swaps == {}, "到期收拾：记录没了，东西也没有被丢出来（%r）" % (where,)


def testTheRemovalOfTheOldBlockIsTheSwapsAndARealBreakAfterwardsStillDrops():
    manager, data = F.setup(events="silent")                  # 引擎的事件不发：自己来问 claims
    F.setBlock(UNLIT)
    _seed(data)
    _light()
    now = fake.world.time
    assert F.StoveSwap.claims(0, K.STOVE, "minecraft:stone", now) is False and F.StoveSwap.claims(0, (1, 2, 3), LIT, now) is False, "别的名字、别的位置不认"
    assert F.StoveSwap.claims(0, K.STOVE, LIT, now) is False, "新方块的名字从来不是换方块自己的（实机换一次只发一次移除事件，名字是旧方块的）"
    assert F.StoveSwap.claims(0, K.STOVE, UNLIT, now) is True and F.StoveSwap.claims(0, K.STOVE, UNLIT, now) is False, "旧方块的那一次，只认一次"
    manager, data = F.setup(events="silent")
    F.setBlock(UNLIT)
    _seed(data)
    _light()                                                  # 刚点着（半秒之内）就被真的拆了：创造模式、爆炸、命令
    F.EventRegistry.dispatch("BlockRemoveServerEvent", {"x": K.STOVE[0], "y": K.STOVE[1], "z": K.STOVE[2], "fullName": LIT, "auxValue": 0, "dimension": 0}, LIT)
    assert sorted(F.groundItems()) == sorted([BEEF, CHICKEN, COOKED]), "烤架上的东西照样掉出来（原来被当成换方块的那一次吞掉，东西跟着方块实体没了）"
    manager, data = F.setup(events="silent")
    F.setBlock(UNLIT)
    _seed(data)
    _light()
    assert F.StoveSwap.claims(0, K.STOVE, UNLIT, fake.world.time + 0.6) is False, "过了 GUARD_SECONDS：是真的拆"
    fake.world.time += 1.0
    F.EventRegistry.dispatch("BlockRemoveServerEvent", {"x": K.STOVE[0], "y": K.STOVE[1], "z": K.STOVE[2], "fullName": LIT, "auxValue": 0, "dimension": 0}, LIT)
    assert sorted(F.groundItems()) == sorted([BEEF, CHICKEN, COOKED]), "过了一会儿拆了：照旧把烤架上的东西全丢出来"


def testWhenTheNewBlockEntityIsLateTheFirstStepWritesTheFoodIn():
    manager, data = F.setup(events="silent", entity="never", look=False)
    F.setBlock(UNLIT)
    before = _seed(data)
    _light()
    assert F.blockName() == LIT and F.data() is None and set(F.StoveSwap._swaps) == {F.KEY}, "方块实体还没有：快照等着"
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    K.step(0.6)
    assert F.StoveSwap._swaps[F.KEY].data is None, "炉灶的第一步把它写进去"
    _sameFood(F.data(), before)
    F.runTimers()
    assert F.groundItems() == [] and F.StoveSwap._swaps == {}


def testIfTheNewBlockEntityNeverComesTheFoodIsDroppedNotLost():
    manager, data = F.setup(events="silent", entity="never", look=False)
    F.setBlock(UNLIT)
    _seed(data)
    _light()
    K.step(1.0)
    assert F.groundItems() == [], "还在等"
    F.runTimers()
    assert sorted(F.groundItems()) == sorted([BEEF, CHICKEN, COOKED]) and F.StoveSwap._swaps == {}, "到期：丢在炉灶位置，不让它们凭空没了"
    assert all(pos == (10.5, 64.5, 10.5) for _item, _dim, pos in fake.spawned)


def testStaleRecordsArePrunedWhenManyPileUpAndTheirFoodIsDroppedNotLost():
    """定时器没跑（热重载、出错）时记录不能一直攒着：攒到 LIMIT 条，下一次换方块先把早该到期的按到期处理，该丢的东西照丢。"""
    manager, data = F.setup(events="silent", look=False)
    F.setBlock(UNLIT)
    for index in range(F.StoveSwap.LIMIT):
        stale = F.StoveSwap.Swap(UNLIT, LIT, {"0": {"itemDict": {"newItemName": BEEF, "newAuxValue": 0, "count": 1}, "cookTimer": 30}},
                                 fake.world.time - 100.0)
        F.StoveSwap._swaps[(0, (100 + index, 64, 100))] = stale
    fresh = F.StoveSwap.Swap(UNLIT, LIT, {}, fake.world.time)
    F.StoveSwap._swaps[(0, (999, 64, 999))] = fresh
    _light()
    assert F.blockName() == LIT
    assert sorted(F.StoveSwap._swaps) == sorted([F.KEY, (0, (999, 64, 999))], key=repr), "过期的都收了，没过期的别的位置的记录、这次的新记录还在"
    assert F.groundItems() == [BEEF] * F.StoveSwap.LIMIT, "还没写进去的快照里的东西丢在各自的炉灶位置"
    assert all(pos[1] == 64.5 for _item, _dim, pos in fake.spawned)


def testTwoSwapsInARowCarryTheSameFood():
    """点着又马上灭（快照还没写进新方块实体）：第二次接着用第一次的快照，不是拍一份空的。"""
    manager, data = F.setup(events="silent", entity="never", look=False)
    F.setBlock(UNLIT)
    before = _seed(data)
    _light()
    assert F.data() is None
    F.give("a", F.SHOVEL, 1, durability=10)
    F.use()
    assert F.blockName() == UNLIT and F.StoveSwap._swaps[F.KEY].data == before
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    K.step(0.6)
    _sameFood(F.data(), before)


def testTheDirectionSurvivesEveryRoundTrip():
    for direction in range(4):
        manager, data = F.setup(look=False)
        F.setBlock(UNLIT)
        F.facing(direction)
        _light()
        assert fake.blockAux[F.KEY] == direction and F.blockName() == LIT
        F.give("a", F.SHOVEL, 1, durability=10)
        F.use()
        assert fake.blockAux[F.KEY] == direction and F.blockName() == UNLIT


def testAnEmptyStoveOrOneWithoutDataGoesAcrossToo():
    manager, data = F.setup(look=False)
    F.setBlock(UNLIT)
    fake.blockEntities[F.KEY] = K.potfake.BEData()
    _light()
    assert F.blockName() == LIT and F.data()["5"] is None, "/setblock 放出来、没有数据的炉灶：什么也没带，用到时补默认值"
    K.step(1.0)
    assert F.data()["5"] == {"itemDict": None, "cookTimer": 30}


def testTheSnapshotIsACopyAndOnlyHoldsPlainData():
    snapshot = F.StoveSwap.snapshot(K.potfake.BEData())
    assert snapshot == {}
    data = K.potfake.BEData()
    data["0"] = {"itemDict": {"newItemName": BEEF, "newAuxValue": 0, "count": 1, "enchantData": [(16, 1)]}, "cookTimer": 9.5}
    data["handGrill"] = {"byHand": [1, 0, 0, 0, 0, 0], "down": [0.5] + [0.0] * 5, "up": [0.0] * 6}
    data["displayEntityId"] = 77
    taken = F.StoveSwap.snapshot(data)
    assert sorted(taken) == ["0", "handGrill"], "只带炉灶自己的键（旧版的展示实体键不带）"
    assert taken["0"]["itemDict"]["enchantData"] == [[16, 1]], "元组换成列表：方块实体数据只收这些"
    taken["0"]["cookTimer"] = 1.0
    assert data["0"]["cookTimer"] == 9.5, "是一份拷贝"


# ---------------------------------------------------------------- 广播和站点

def testAfterTheSwapTheLookAndTheWorldDisplayAreSentAgainForAWhile():
    """客户端的方块实体在换方块时重建、场景跟着重建，先到的广播可能被盖掉：换完的这一秒里每一步重发世界外观和展示，之后不再发。"""
    manager, data = F.setup()
    F.setBlock(UNLIT)
    _seed(data)
    K.step(0.6)
    K.looks()
    del fake.calls[:]
    K.BlockItems.startRecording()
    _light()
    K.step(0.6)
    shown = K.BlockItems.stopRecording()
    sent = [payload for payload, players in K.looks() if "a" in players]
    assert len(shown) >= 2 and len(sent) >= 2, "展示和世界外观都发了不止一遍"
    assert all(payload["slots"][0]["item"]["newItemName"] == BEEF for payload in sent)
    K.step(2.0)
    del fake.calls[:]
    K.BlockItems.startRecording()
    K.step(2.0)
    assert len(K.BlockItems.stopRecording()) == 0, "过了这一秒：展示不再重发"
    assert F.StoveSwap.settling(0, K.STOVE, fake.world.time) is False


def testTheStationStaysOpenForAnotherCookWhenSomeoneLightsOrPutsOutTheStove():
    """JE：点火 / 灭火只改 LIT，站点不受影响（ActiveStation.canStay 问 type.matches，点着的和熄着的是同一种站点的方块）。内核按站点类型认方块
    （Upkeep.stillValid 的 station.type.binds），不按方块名：正开着炉灶站点的另一位厨师不被请走，站点还是同一个实例（C05，另见 test_diegesis_block_swap）。"""
    manager, data = F.setup()
    F.setBlock(UNLIT)
    K.opened(manager, "b")
    assert "b" in manager.sessions
    station = manager.stations[F.KEY]
    fake.give("a", 0, F.FLINT, 1)
    F.use()
    assert F.blockName() == LIT
    K.step(2.0, manager=manager)
    assert "b" in manager.sessions and manager.stations[F.KEY] is station, "点着了：另一位厨师还在站点里，还是同一个实例"
    fake.give("a", 1, F.WATER, 1)
    F.use(slot=1)
    assert F.blockName() == UNLIT
    K.step(2.0, manager=manager)
    assert "b" in manager.sessions and manager.stations[F.KEY] is station, "又浇灭了：照样在"


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
