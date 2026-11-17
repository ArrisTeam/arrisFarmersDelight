# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点的服务端逻辑（Compat/Diegesis/GrillLogic.py + Server/HandGrill.py + Server/Helpers/StoveSlots.py + Server/Stove.py，
前置包的 Manager 是真的）：槽规则、摆上烤架、翻面、取下、开站时摆主手的食物、两面烤好的收尾、FD 原样的件。
对应 Hands-On Delight 的 StoveTests（aPieceGrillsInHalvesAndWaitsToBeTurned、onlyFoodGoesOnAnOpenGrill、anEggStaysOffTheGrill、
piecesLaidByHandGoFarmersDelightsWay、farmersDelightsWayStaysItsOwn）。引擎是 potfake.py 里的假的。"""
from __future__ import print_function

import math

import stovekit as K
from stovekit import BEEF, EGG, STICK, fake

Protocol = K.Protocol
SIDE = 10.0                        # 一面 30 / 1.5 / 2 = 10 秒


def beef(count=1):
    return {"newItemName": BEEF, "newAuxValue": 0, "count": count}


def testOpeningBindsTheSixPlacesToTheBlockAndTheStationSendsNoPicturesOfItsOwn():
    """烤架上的画面（两面烤到哪、动作）是谁都看得见的世界场景，靠 StoveLook 的广播；站点自己只管六个烤位里是什么。"""
    manager, data = K.setup()
    data["1"] = {"itemDict": beef(), "cookTimer": 30}
    payload = K.opened(manager)
    state = payload["state"]
    assert sorted(state["slots"]) == ["grill"] and len(state["slots"]["grill"]) == 6
    assert state["slots"]["grill"]["1"]["newItemName"] == BEEF and state["slots"]["grill"]["0"] == {}
    assert not state["data"], "站点不再带两面烤到哪的数据：画面照世界外观广播"
    assert payload["hand"] is None
    assert K.names(data)[:2] == [None, BEEF], "站点读的就是方块实体数据"


def testAStackInTheHandGoesOnEveryFreePlaceOnePieceEach():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 4)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    fake.world.take()
    assert K.do(manager, "a", K.custom("place"))
    assert K.items(data) == [(BEEF, 1)] * 4 + [None, None], "一个位置一件"
    assert manager.sessions["a"].hand is None and fake.world.players["a"]["inv"][3] is None
    assert [K.hand_of().grill.byHand(place) for place in range(6)] == [True] * 4 + [False] * 2, "手放的，从此两面分开烤"
    assert ("placed", {"places": [0, 1, 2, 3]}) in K.effects(), "效果里带着摆上去的位置（开站时摆的，客户端靠它演落下）"


def testASixthOfTenGoesOnAndTheRestStaysInTheHand():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 10)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("place"))
    assert K.items(data) == [(BEEF, 1)] * 6 and manager.sessions["a"].hand["count"] == 4, "six places, six pieces"
    assert K.do(manager, "a", K.custom("place")), "满了：不接，也不丢"
    assert manager.sessions["a"].hand["count"] == 4
    assert [name for name, _ in K.effects()][-1] == "refused"


def testOnePieceOntoTheChosenPlace():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 3)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("place", one=True, place=4))
    assert K.names(data) == [None, None, None, None, BEEF, None] and manager.sessions["a"].hand["count"] == 2
    K.effects()
    assert K.do(manager, "a", K.custom("place", one=True, place=4))
    assert K.items(data).count((BEEF, 1)) == 1 and manager.sessions["a"].hand["count"] == 2, "那个位置有东西了：弹回，不换"
    assert K.effects() == [("refused", {"stack": {"newItemName": BEEF, "newAuxValue": 0, "count": 1}})]
    assert K.do(manager, "a", K.custom("place", one=True, place=-1)), "没有最近的空位（客户端发 -1）：当作每个空位一件"
    assert K.items(data).count((BEEF, 1)) == 3 and manager.sessions["a"].hand is None


def testAStackInTheInventoryGoesOnWithoutTakingItToTheHand():
    manager, data = K.setup()
    fake.give("a", 5, BEEF, 8)
    K.opened(manager)
    assert K.do(manager, "a", K.custom("place", **{"from": 5}))
    assert K.items(data) == [(BEEF, 1)] * 6 and fake.world.players["a"]["inv"][5]["count"] == 2
    assert manager.sessions["a"].hand is None
    assert K.do(manager, "a", K.custom("place", **{"from": 99})) and fake.world.players["a"]["inv"][5]["count"] == 2, "格号越界：什么也不做"
    assert K.do(manager, "a", K.custom("place", **{"from": 6})), "空格：什么也不做"


def testOnlyFoodThatStaysOnTheBarsGoesOn():
    """onlyFoodGoesOnAnOpenGrill / anEggStaysOffTheGrill：棍子、蛋放不上去，弹回手里；蛋有营火配方，但炉灶不收。"""
    manager, data = K.setup()
    fake.give("a", 0, STICK, 2)
    fake.give("a", 1, EGG, 3)
    K.opened(manager)
    for slotIndex, count in ((0, 2), (1, 3)):
        assert K.do(manager, "a", K.click(K.inv(slotIndex)))
        K.effects()
        assert K.do(manager, "a", K.custom("place"))
        assert K.names(data) == [None] * 6 and manager.sessions["a"].hand["count"] == count
        assert [name for name, _ in K.effects()] == ["refused"]
        assert K.do(manager, "a", K.click(K.inv(slotIndex), kind="PUT_AWAY"))
    assert not K.do(manager, "a", K.click(K.inv(1), kind="QUICK_MOVE")), "Shift 点托盘里的蛋：槽不收"
    assert fake.world.players["a"]["inv"][1]["count"] == 3


def testAnEggOrAFullGrillShiftClickedFromTheTrayBouncesBackAndFoodGoesOnAndIsAnnounced():
    """前置包的 onInventoryShiftClick 钩子让表现发 place {from: 背包格号}（JE 的写法）：蛋（有营火配方但烤架不收）、满了都回 refused，
    放得上去的回 placed，那一叠留在背包里剩下的。"""
    manager, data = K.setup()
    fake.give("a", 1, EGG, 3)
    fake.give("a", 2, BEEF, 9)
    K.opened(manager)
    K.effects()
    assert K.do(manager, "a", K.custom("place", **{"from": 1}))
    assert K.names(data) == [None] * 6 and fake.world.players["a"]["inv"][1]["count"] == 3, "蛋留在那一格"
    assert K.effects() == [("refused", {"stack": {"newItemName": EGG, "newAuxValue": 0, "count": 1}})]
    assert K.do(manager, "a", K.custom("place", **{"from": 2}))
    assert K.items(data) == [(BEEF, 1)] * 6 and fake.world.players["a"]["inv"][2]["count"] == 3, "每个空位一件，剩下的留在背包"
    assert K.effects() == [("placed", {"places": [0, 1, 2, 3, 4, 5]})]
    assert K.do(manager, "a", K.custom("place", **{"from": 2}))
    assert K.effects() == [("refused", {"stack": {"newItemName": BEEF, "newAuxValue": 0, "count": 1}})], "满了：弹回"
    assert fake.world.players["a"]["inv"][2]["count"] == 3


def testNothingGoesOntoAStoveWithAPotOnTop():
    """开站时就盖着锅的炉灶服务端不让开（test_grill_station_open）；这里是站点开着的时候，有人在上面摆了口锅：槽规则照样挡。"""
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 3)
    K.opened(manager)
    fake.world.blocks[(0, (K.STOVE[0], K.STOVE[1] + 1, K.STOVE[2]))] = "arris:cooking_pot"
    K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.custom("place")) and K.names(data) == [None] * 6
    assert not K.do(manager, "a", K.click(K.slot(2))), "内核的点击也放不进去"
    assert manager.sessions["a"].hand["count"] == 3


def testAPotSetOnTheStoveThrowsEverythingOffTheGrillAsFarmersDelightDoes():
    """FD 的 serverTick：上面盖了东西，烤架上的东西全丢出来（生的、熟的、手放的、FD 原样的都一样）；站点和世界里的展示跟着空了。"""
    manager, data = K.setup()
    data["4"] = {"itemDict": beef(), "cookTimer": 30}
    fake.give("a", 3, BEEF, 2)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3)))
    K.do(manager, "a", K.custom("place"))
    K.step(11.0)
    K.do(manager, "a", K.custom("turn", place=0))
    assert [name for name in K.names(data) if name] == [BEEF, BEEF, BEEF] and K.hand_of().grill.byHand(0)
    K.BlockItems.startRecording()
    K.step(0.5)
    assert not fake.spawned, "上面是空气：什么也不丢"
    fake.world.blocks[(0, (K.STOVE[0], K.STOVE[1] + 1, K.STOVE[2]))] = "arris:cooking_pot"
    K.step(0.25)
    sent = K.BlockItems.stopRecording()
    assert K.names(data) == [None] * 6, "全丢出来了"
    assert sorted(item["newItemName"] for item, _, _ in fake.spawned) == [BEEF] * 3, "一件一个掉落物，不分手放的还是 FD 原样的"
    assert all(K.droppedInside(entry) for entry in fake.spawned), "每件从方块里随机一点掉出来（ItemUtils.dropItems），不是都叠在方块中心"
    assert not any(K.hand_of().grill.byHand(place) for place in range(6)) and K.hand_of().grill.up(0) == 0.0, "手放的进度作废"
    assert sent and sent[-1]["kind"] == "stove" and all(not entry for entry in sent[-1]["items"].values()), "世界里的展示清空"
    K.step(5.0)
    assert len(fake.spawned) == 3, "只丢一回"


def testNoThingIsThrownOffWhileWaterOrAirIsOnTop():
    manager, data = K.setup()
    data["0"] = {"itemDict": beef(), "cookTimer": 30}
    fake.world.blocks[(0, (K.STOVE[0], K.STOVE[1] + 1, K.STOVE[2]))] = "minecraft:water"
    K.step(1.0)
    assert K.names(data)[0] == BEEF and not fake.spawned, "水不算盖住（FD 里液体没有方块形状）"


def testShiftClickOnTheTrayLaysTheStackOnAndTheWorldIsToldOnce():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 10)
    K.opened(manager)
    K.BlockItems.startRecording()
    assert K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    manager.tick(0.05)
    sent = K.BlockItems.stopRecording()
    assert K.items(data) == [(BEEF, 1)] * 6 and fake.world.players["a"]["inv"][3]["count"] == 4, "每个空位一件，剩下的留在背包"
    assert all(K.hand_of().grill.byHand(place) for place in range(6)), "内核点击摆上去的也是手放的"
    assert len(sent) == 1 and sent[0]["kind"] == "stove" and sent[0]["items"]["5"]["newItemName"] == BEEF, "世界里的展示只广播一次"
    assert not K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE")), "没有空位了"


def testAPieceOnTheGrillCannotBePickedUpByTheKernelsClicks():
    """左键点一件是翻面、右键是取下，不是拿起来：mayTake 假，双击聚拢也不会把它们收走。"""
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 2)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    fake.give("a", 5, BEEF, 3)
    assert not K.do(manager, "a", K.click(K.slot(0))), "空手点一件：不拿起"
    assert not K.do(manager, "a", K.click(K.slot(0), button=1))
    assert not K.do(manager, "a", K.click(K.slot(0), kind="QUICK_MOVE"))
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert not K.do(manager, "a", K.click(K.slot(0), kind="PICKUP_ALL")), "背包里没有别的牛肉可收，站点里的不让收"
    assert K.names(data)[:2] == [BEEF, BEEF] and manager.sessions["a"].hand["count"] == 3


def testTheKernelsOwnPickupWithAStackPutsOnePieceOnThatPlace():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 3)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3)))
    assert K.do(manager, "a", K.click(K.slot(4)))
    assert K.names(data)[4] == BEEF and manager.sessions["a"].hand["count"] == 2 and K.hand_of().grill.byHand(4)


def testAPieceGrillsInHalvesWaitsToBeTurnedThenIsDone():
    """aPieceGrillsInHalvesAndWaitsToBeTurned：一面 10 秒，熟了等着翻；翻一下，另一面 10 秒；两面都熟了换成成品、留在烤架上。"""
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 2)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    K.effects()
    K.step(SIDE - 0.5, manager=manager)
    shared = K.current()
    assert 0.9 < shared["down"][0] < 1.0 and shared["up"][0] == 0.0 and shared["hand"][:2] == [True, True]
    K.step(1.0, manager=manager)
    shared = K.current()
    grill = K.hand_of().grill
    assert shared["down"][0] == 1.0 and shared["up"][0] == 0.0 and grill.waits(0) and grill.waits(1), "贴烤架那面熟了：等着翻"
    K.step(5.0, manager=manager)
    assert K.names(data)[0] == BEEF and grill.up(0) == 0.0 and grill.waits(0), "不翻就永远只熟一面"
    assert K.do(manager, "a", K.custom("turn", place=0))
    assert ("turned", {"place": 0, "up": 1.0}) in K.effects(), "翻面的效果带着翻过来之后朝上那面烤到哪"
    assert grill.up(0) >= 1.0 and grill.down(0) == 0.0 and grill.waits(1)
    K.step(SIDE + 0.5, manager=manager)
    assert K.names(data)[0] == "minecraft:cooked_beef" and K.names(data)[1] == BEEF, "翻过的熟了；另一件还在等着翻"
    done = [(name, body) for name, body in K.effects() if name == "grilled"]
    assert done and done[0][1]["place"] == 0 and done[0][1]["stack"]["newItemName"] == "minecraft:cooked_beef"
    assert grill.byHand(0) and not grill.waits(0), "烤好的留在烤架上，等人取"
    assert not [c for c in fake.calls if c[1] == "OnPlaySound"], "烤好了的叮一声现在由客户端的场景放（谁都听得见），服务端不再广播声音"


def testAPieceThatIsDoneWhileNobodyHasTheStationOpenIsAnnouncedToEveryoneNearby():
    """JE 的炉灶场景 idle_visible：烤好的那一下（一团汽、金光、叮）32 格内的人都看得见，不用有人开着站点；站点后来再开也不重复。"""
    manager, data = K.setup()
    data["0"] = {"itemDict": beef(), "cookTimer": 30}
    K.hand_of().grill.layByHand(0)
    K.step(SIDE + 0.5)
    assert K.hand_of().grill.toss(0, fake.world.time)           # 厨师翻了一下就走了
    K.step(SIDE + 0.5)
    assert K.names(data)[0] == "minecraft:cooked_beef", "没人开站点：照样烤好了"
    assert K.hand_of().just == [], "烤好了的当场告诉附近的人，不留着等站点来取"
    done = K.broadcasts("grilled")
    assert len(done) == 1 and done[0][1]["place"] == 0 and sorted(done[0][2]) == ["a", "b"], "两个玩家都在 32 格内：都收到"
    assert done[0][1]["stack"]["newItemName"] == "minecraft:cooked_beef"
    del fake.calls[:]
    K.opened(manager)
    K.step(0.5, manager=manager)
    assert K.effects() == [] and not [c for c in fake.calls if c[1] == "OnPlaySound"], "站点开了不再补一遍"


def testTheStationMakesNoWorldSoundsOfItsOwnTheScenesPlayThem():
    """放上去、取下、烤好的声音是 JE 的灯笼放置声 / 拾取声，在每个客户端的场景里放（StoveFx.placed / taken / grilled）；服务端不再放原版的皮革声和 pop。"""
    manager, data = K.setup()
    fake.give("a", 0, BEEF, 8)
    K.opened(manager)                                           # 开站：主手的食物摆上去
    fake.give("a", 3, BEEF, 1)
    K.do(manager, "a", K.custom("take", place=0))
    K.do(manager, "a", K.custom("place", **{"from": 3}))
    assert not [c for c in fake.calls if c[1] == "OnPlaySound"]
    assert [name for name, _, _ in K.broadcasts()].count("placed") >= 2 and "taken" in [name for name, _, _ in K.broadcasts()]


def testTheStationSendsNoEffectsOfItsOwnTheNearbyBroadcastCarriesThemAll():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 8)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3)))
    K.do(manager, "a", K.custom("place"))
    K.do(manager, "a", K.custom("turn", place=0))
    K.do(manager, "a", K.custom("take", place=1))
    assert fake.world.take("a", Protocol.EP_EFFECT) == [], "内核的效果通道不用了"
    names = [name for name, _, _ in K.broadcasts()]
    assert names == ["placed", "turned", "taken"] or names == ["placed", "unturned", "taken"], names
    assert all(sorted(players) == ["a", "b"] for _, _, players in K.broadcasts()), "站点里的人和站点外附近的人收到同样的一份"


def testTheHandGrillingIsSavedWithTheStoveAndPicksUpAfterARestart():
    """JE 的 Grill 存在炉灶自己的方块实体里（StoveBlockEntityMixin）：重启后手放的进度还在，不会变成 FD 原样的件。"""
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 2)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    K.step(SIDE + 0.5, manager=manager)
    saved = data["handGrill"]
    assert saved["byHand"] == [1, 1, 0, 0, 0, 0] and saved["down"][0] == 1.0 and saved["up"][0] == 0.0, "烤到一面熟了：存着"
    manager.close("a")
    K.HandGrill._hands.clear()                    # 重启：内存里的没了，方块实体数据还在
    K.step(0.5)
    grill = K.hand_of().grill
    assert grill.byHand(0) and grill.byHand(1) and grill.waits(0) and grill.down(0) == 1.0, "第一次 tick 接上"
    assert data["0"]["cookTimer"] == 30, "FD 的计时没动：没有被当成 FD 原样的件弹出去"
    K.step(40.0)
    assert K.names(data)[:2] == [BEEF, BEEF], "等着翻就一直等着翻，不会被 FD 弹出"
    K.opened(manager)
    assert K.current()["down"][:2] == [1.0, 1.0] and K.current()["hand"][:2] == [True, True], "进度和手放的记号都接上了"
    assert K.do(manager, "a", K.custom("turn", place=0))
    K.step(SIDE + 0.5, manager=manager)
    assert K.names(data)[0] == "minecraft:cooked_beef", "接着翻、接着烤"
    assert data["handGrill"]["byHand"][2:] == [0, 0, 0, 0], "没碰过的位置不是手放的"


def testAStoveNobodyHandGrilledOnWritesNothingExtra():
    manager, data = K.setup()
    data["1"] = {"itemDict": beef(), "cookTimer": 30}
    K.opened(manager)
    K.step(2.0, manager=manager)
    assert data["handGrill"] is None, "没有手放的件：不写存档"


def testTheProgressIsToldInThirtySecondsOfASide():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 1)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    K.step(2.0, manager=manager)
    shared = K.current()
    exact = K.hand_of().grill.down(0)
    assert 0.15 < exact <= 0.2 and shared["down"][0] == math.floor(exact * 32) / 32.0, "向下取到 1/32 的整数倍"
    assert shared["down"][1:] == [0.0] * 5 and shared["hand"] == [True] + [False] * 5


def testATurnTooSoonAfterTheLastIsTurnedDownAndSoIsATurnOfNothing():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 1)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    K.step(SIDE + 0.3, manager=manager)
    K.effects()
    assert K.do(manager, "a", K.custom("turn", place=0)) and K.effects() == [("turned", {"place": 0, "up": 1.0})]
    fake.world.time += 0.1
    assert K.do(manager, "a", K.custom("turn", place=0)) and K.effects() == [("unturned", {"place": 0})], "还在空中"
    assert K.hand_of().grill.up(0) >= 1.0, "没有翻第二次"
    fake.world.time += 0.25
    assert K.do(manager, "a", K.custom("turn", place=0)) and K.effects() == [("turned", {"place": 0, "up": 0.0})], "6 刻之后可以再翻"
    for bad in (3, -1, 6, 99, True, "0", None, 1.5):
        assert K.do(manager, "a", K.custom("turn", place=bad))
        assert K.effects() == [("unturned", {"place": bad if isinstance(bad, int) and not isinstance(bad, bool) and 0 <= bad < 6 else -1})], bad


def testADonePieceCannotBeTurnedAnyMore():
    manager, data = K.setup()
    data["0"] = {"itemDict": {"newItemName": "minecraft:cooked_beef", "newAuxValue": 0, "count": 1}, "cookTimer": 30}
    K.opened(manager)
    K.hand_of().grill.layByHand(0)
    assert K.do(manager, "a", K.custom("turn", place=0)) and K.effects() == [("unturned", {"place": 0})], "已经烤好：没有什么可翻的"


def testTakingARawHalfDoneOrDonePieceGivesItBackAndTheGrillStartsOver():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 2)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))
    manager.tick(0.05)
    K.effects()
    K.BlockItems.startRecording()
    assert K.do(manager, "a", K.custom("take", place=1))
    manager.tick(0.05)
    sent = K.BlockItems.stopRecording()
    assert K.names(data)[:2] == [BEEF, None] and fake.count("a", BEEF) == 1, "生的取下来进背包"
    assert not K.hand_of().grill.byHand(1) and K.hand_of().grill.byHand(0), "那个位置从头开始"
    assert K.effects() == [("taken", {"place": 1, "stack": {"newItemName": BEEF, "newAuxValue": 0, "count": 1}})]
    assert len(sent) == 1 and sent[0]["items"]["1"] == {}, "世界里的展示也少了一件"
    assert K.do(manager, "a", K.custom("take", place=1)) and K.effects() == [], "空位：什么也不发生"
    for bad in (-1, 6, True, "0", None):
        assert K.do(manager, "a", K.custom("take", place=bad)) and K.names(data)[0] == BEEF, bad


def testAFullInventoryDropsWhatIsTaken():
    manager, data = K.setup()
    data["2"] = {"itemDict": beef(), "cookTimer": 30}
    for index in range(36):
        fake.give("a", index, "arris:wheat", 64)
    K.opened(manager)
    assert K.do(manager, "a", K.custom("take", place=2))
    assert K.names(data)[2] is None and [item for _, _, item in fake.world.dropped if item["newItemName"] == BEEF], "放不下掉在脚下"


def testOpeningWithFoodInTheMainHandLaysItOnAtOnce():
    """JE 的 onOpen：右键时主手拿着烤得了的食物，整叠摆到每个空位上，剩下的留在手里（不比不开站点慢）。"""
    manager, data = K.setup()
    fake.give("a", 0, BEEF, 8)
    payload = K.opened(manager)
    assert K.items(data) == [(BEEF, 1)] * 6 and fake.world.players["a"]["inv"][0]["count"] == 2
    assert payload["state"]["slots"]["grill"]["5"]["newItemName"] == BEEF, "第一份状态里就有"
    assert all(K.hand_of().grill.byHand(place) for place in range(6))
    assert ("placed", {"places": [0, 1, 2, 3, 4, 5]}) in K.effects()
    fake.give("b", 0, BEEF, 1)
    K.opened(manager, "b")
    assert fake.world.players["b"]["inv"][0]["count"] == 1, "没有空位了：留在手里"


def testComingOverFromANeighbouringStationLaysNothingFromTheMainHand():
    """JE 的 StoveBehavior.onOpen:110-113 先看 view.openedByUse()：从相邻的站点走过来的，主手里的东西不是给这座灶的。"""
    manager, data = K.setup()
    fake.give("a", 0, BEEF, 8)
    assert manager.open("a", list(K.STOVE), False)
    assert K.items(data) == [None] * 6 and fake.world.players["a"]["inv"][0]["count"] == 8
    assert not [effect for effect in K.effects() if effect[0] == "placed"]


def testOpeningWithAnEggOrANonFoodThingLaysNothing():
    manager, data = K.setup()
    fake.give("a", 0, EGG, 5)
    K.opened(manager)
    assert K.names(data) == [None] * 6 and fake.world.players["a"]["inv"][0]["count"] == 5
    assert K.effects() == [], "不弹，不响：蛋留在手里，不拦着开站点"
    manager.close("a")
    fake.give("a", 0, STICK, 1)
    K.opened(manager)
    assert K.names(data) == [None] * 6 and fake.world.players["a"]["inv"][0]["count"] == 1


def testACreativePlayerSpendsWhatHeLaysOnToo():
    manager, data = K.setup(creative=True)
    fake.give("a", 0, BEEF, 3)
    K.opened(manager)
    assert K.items(data)[:3] == [(BEEF, 1)] * 3 and fake.world.players["a"]["inv"][0] is None, "JE 不分创造：手上的一件件摆上去"


def testAPieceFarmersDelightLaidItsOwnWayIsTurnedFromRawAndStaysTheCooks():
    """farmersDelightsWayStaysItsOwn：右键放上去的不是手放的；翻它一下，从此归厨师、从生开始算；烤架上它旁边手放的互不相干。"""
    manager, data = K.setup()
    data["2"] = {"itemDict": beef(), "cookTimer": 30}
    K.opened(manager)
    assert K.current()["hand"] == [False] * 6
    K.step(5.0)
    assert not K.hand_of().grill.byHand(2) and K.names(data)[2] == BEEF
    assert data["2"]["cookTimer"] < 30, "FD 自己的 30 秒在倒数"
    assert K.do(manager, "a", K.custom("turn", place=2))
    grill = K.hand_of().grill
    assert grill.byHand(2) and grill.down(2) == 0.0 and grill.up(2) == 0.0, "从生开始"
    manager.close("a")
    K.opened(manager)
    assert grill.byHand(2) and K.names(data)[2] == BEEF, "站点关了再开：东西和进度还在"


def testAPieceFarmersDelightLaidItsOwnWayPopsOffAfterThirtySeconds():
    manager, data = K.setup()
    data["3"] = {"itemDict": beef(), "cookTimer": 30}
    K.opened(manager)
    K.effects()
    fake.world.take("a", Protocol.EP_STATE)
    K.step(31.0, manager=manager)
    assert K.names(data)[3] is None and [item for item, _, _ in fake.spawned if item["itemName"] == "minecraft:cooked_beef"]
    seen = [m[2]["state"]["slots"]["grill"] for m in fake.world.take("a", Protocol.EP_STATE) if "slots" in m[2]["state"]]
    assert seen and seen[-1]["3"] == {}, "站点里那一格也空了（前置包发现外面的变化）"


def testTheGrillKeepsItsPiecesWhenTheCookWalksAwayAndTheCursorStackGoesBack():
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 9)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3)))
    K.do(manager, "a", K.custom("place"))
    assert manager.sessions["a"].hand["count"] == 3
    manager.close("a")
    assert K.items(data) == [(BEEF, 1)] * 6, "站点关了，东西留在炉灶上"
    assert fake.count("a", BEEF) == 3, "手上剩的放回背包"
    K.step(SIDE + 0.5)
    assert K.hand_of().grill.waits(0), "他走开了也接着烤：烤到一面熟了就等着翻"
    K.opened(manager)
    assert K.current()["down"][0] == 1.0 and K.current()["hand"] == [True] * 6


def testAnotherCookAtTheSameStoveSeesTheChangesAsTheyHappen():
    manager, data = K.setup()
    fake.give("a", 0, BEEF, 2)
    fake.give("b", 0, STICK, 1)
    K.opened(manager, "b")
    K.opened(manager, "a")
    K.step(0.1, manager=manager)
    seen = fake.world.take("b", Protocol.EP_STATE)
    assert seen and seen[-1][2]["state"]["slots"]["grill"]["1"]["newItemName"] == BEEF, "a 开站时摆上去的，b 也看到"
    assert K.do(manager, "b", K.custom("take", place=0)) and K.names(data)[0] is None
    assert fake.count("b", BEEF) == 1


def testAnOldFrontDoorWithoutTheCursorStackGetsNoStove():
    assert K.GrillLogic.register(type("OldApi", (), {"API_VERSION": 1})) is None


def testTheStationStillOpensWhenTheBlockHasNoEntityDataYet():
    """/setblock、结构放出的炉灶没走放置事件：开站时补上六个烤位的默认值。"""
    manager, data = K.setup()
    fake.blockEntities[(0, K.STOVE)] = K.potfake.BEData()
    payload = K.opened(manager)
    assert payload["state"]["slots"]["grill"]["0"] == {}
    assert K.fake.blockEntities[(0, K.STOVE)]["5"] == {"itemDict": None, "cookTimer": 30}


def testPlacingOnAStoveWhoseBlockEntityIsGoneKeepsTheStackInTheHand():
    """方块实体不在（换方块的那几刻、没加载）时写烤位不能悄悄返回：站点里放下了、手上扣了、存储却没写，东西就没了。抛：动作作废，手上的还在。"""
    manager, data = K.setup()
    fake.give("a", 3, BEEF, 4)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3)))
    fake.world.take()
    del fake.blockEntities[(0, K.STOVE)]
    assert not K.do(manager, "a", K.custom("place")), "动作作废"
    hand = manager.sessions["a"].hand
    assert hand["newItemName"] == BEEF and hand["count"] == 4, "光标栈上的四块牛肉一块没少"
    assert len(fake.world.errors) == 1 and "block entity missing" in fake.world.errors[0]
    assert K.effects() == [], "没有放下去的表现"
    fake.blockEntities[(0, K.STOVE)] = data                    # 方块实体回来了：同一个动作照常放上去
    assert K.do(manager, "a", K.custom("place"))
    assert K.items(data).count((BEEF, 1)) == 4 and manager.sessions["a"].hand is None


def testStoveSlotsRefuseToWriteWhereThereIsNoBlockEntity():
    slots = K.potfake.load("Server.Helpers.StoveSlots").StoveSlots(0, (99, 64, 99), 6, 30)
    assert slots.get(0) is None, "读：空"
    try:
        slots.set(0, beef())
    except RuntimeError as error:
        assert "block entity missing" in str(error)
    else:
        raise AssertionError("悄悄吞了")


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
