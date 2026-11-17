# -*- coding: utf-8 -*-
# runner: both
"""炉灶在本客户端的场景（Compat/Diegesis 的 StoveScene / StoveScenes / StoveWorld / GrillPieces / GrillGhosts / GrillFx，假引擎）：
服务端广播来了摆出烤架上的东西（客户端掉落物，平躺、每件朝向不同）、落下 / 翻面 / 取走 / 弹回的动作、热浪蒸汽和该翻了的烟，
全程不需要有人开着站点（HoD 的炉灶场景是 idle_visible）；区块晚加载按方块实体数据补、重复加载当重建、方块没了收拾干净、
远处只算画面不放粒子声音、别的维度和别的方块的广播丢掉。六件的位置、动作、粒子声音的位置跟着炉灶方块的朝向转（站点的北面是炉灶的正面，
JE 的 Orientation.BLOCK；FD 自己的渲染器也按 FACING 转），谁站在哪边看都一样。对应 HoD 的 StoveBehavior.refresh / draw / turned / taken / onEffect / heat。"""
from __future__ import print_function

import math
import random

import panclient as C

world = C.install()
Scene = C.load("Compat.Diegesis.StoveScene")
Scenes = C.load("Compat.Diegesis.StoveScenes")
BlockItems = C.load("Client.BlockItems")
State = C.load("Shared.Rules.StoveLookState")
Layout = C.load("Shared.Rules.HandsOn.StoveLayout")
POS = C.POS
DT = 1.0 / 60.0
BEEF, COOKED = "minecraft:beef", "minecraft:cooked_beef"
FRACTIONS = [(0.8, 0.7), (0.5, 0.7), (0.2, 0.7), (0.8, 0.3), (0.5, 0.3), (0.2, 0.3)]      # stove.json 的 piece_0 ~ piece_5（方块内的比例）


class Clock(object):
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


clock = Clock()
Scenes.time = clock


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def slot(name, hand=False, down=0.0, up=0.0):
    return {"item": item(name), "hand": hand, "down": down, "up": up}


def payload(slots=None):
    """服务端的状态广播：slots 是 {位置: slot(...)}。"""
    full = [dict(slots or {}).get(place, {}) for place in range(6)]
    return {"dimensionId": 0, "pos": list(POS), "slots": full}


def event(name, place=None, **data):
    body = {"dimensionId": 0, "pos": list(POS), "event": name}
    if place is not None:
        body["place"] = place
    body.update(data)
    return body


def setup(slots=None, aux=2):
    """干净的假世界、一座炉灶的场景（aux 是方块的朝向状态：0 南 1 西 2 北 3 东，缺省朝北）；给了 slots 就先广播一份并走一帧
    （第一份状态按"刚加载"画，不演落下）。"""
    world.reset()
    world.blocks[POS] = ("arris:stove", aux)
    Scenes._scenes.clear()
    Scenes._state.update(on=False, last=None, tick=0, check=0.0)
    BlockItems._hidden.clear()
    BlockItems._last.clear()
    Scenes.enable()
    random.seed(3)
    scene = Scenes.ensure(0, POS)
    if slots is not None:
        Scenes.OnStoveLook(payload(slots))
        run(scene, DT)
    return scene


def run(scene, seconds, near=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near)


def drops(name=None):
    return [d for d in world.drops.values() if name is None or d["item"]["newItemName"] == name]


def centerOf(drop):
    """掉落物的视觉中心：轴心 + 贴图的"上"方向 * 半边长（R = Rz·Rx·Ry，第二列是 (-sin z cos x, cos z cos x, sin x)）。"""
    x, y, z = [math.radians(angle) for angle in drop["euler"]]
    half = 8.0 / 16.0 * drop["scale"] * 0.5
    up = (-math.sin(z) * math.cos(x), math.cos(z) * math.cos(x), math.sin(x))
    return tuple(drop["pivot"][axis] + up[axis] * half for axis in range(3))


def particles(identifier=None):
    return [p for p in world.particles if identifier is None or p["id"] == identifier]


def sounds(name):
    return [s for s in world.sounds if s["name"] == name]


# ---------------------------------------------------------------- 登记

def testASceneIsOnlyBuiltForAStoveAndHidesTheOldFoodDisplay():
    scene = setup()
    assert scene is not None and Scenes.sceneAt(0, POS) is scene and Scenes.ensure(0, POS) is scene
    assert (0, POS) in BlockItems._hidden, "烤架上的东西从此由场景画，Client/BlockItems 那份不再画"
    world.blocks[(1, 2, 3)] = ("minecraft:stone", 0)
    assert Scenes.ensure(0, (1, 2, 3)) is None and Scenes.ensure(0, (7, 7, 7)) is None


def testAnyBlockInTheStoveListGetsAScene():
    """StoveList 是对外的联动契约：附属包往里追加的炉灶也一样。"""
    Stoves = C.load("Shared.Data.Cooking").StoveList
    setup()
    world.blocks[(3, 3, 3)] = ("addon:big_stove", 0)
    assert Scenes.ensure(0, (3, 3, 3)) is None
    Stoves.append("addon:big_stove")
    try:
        assert Scenes.ensure(0, (3, 3, 3)) is not None
    finally:
        Stoves.remove("addon:big_stove")


# ---------------------------------------------------------------- 画

def testTheBroadcastDrawsEachPieceWhereTheWorldHasItAndNobodyNeedsToOpenTheStation():
    scene = setup(dict((place, slot(BEEF)) for place in range(6)))
    live = drops(BEEF)
    assert len(live) == 6 and all(d["item"]["count"] == 1 for d in live)
    centers = sorted((round(centerOf(d)[0] - POS[0], 3), round(centerOf(d)[2] - POS[2], 3)) for d in live)
    assert centers == sorted(FRACTIONS), "stove.json 的 piece_0 ~ piece_5"
    assert all(abs(centerOf(d)[1] - (POS[1] + 16.3 / 16.0)) < 1.0e-6 for d in live), "躺在烤架面上"
    assert all(abs(d["scale"] - 5.0 / 8.0) < 1.0e-9 for d in live), "一件 5 像素宽"
    assert len(set(tuple(round(v, 3) for v in d["euler"]) for d in live)) == 6, "每件摆得各转一点，没有两件同向"
    assert not scene.focused and all(world.shadows[key] is False for key in world.drops), "没人开站点；掉落物的影子关着"


def testTheLayoutDoesNotTurnWithWhoeverLooksOrOpensTheStation():
    scene = setup({0: slot(BEEF), 4: slot(BEEF)})
    before = sorted((d["pivot"], d["euler"]) for d in drops())
    scene.focus(lambda index, count: None)                      # 有人开了站点（不管他站在哪一侧）：件还是躺在原来的地方
    run(scene, 0.5)
    assert sorted((d["pivot"], d["euler"]) for d in drops()) == before


def testTheFirstStateAppearsAtOnceAndALaterOneFallsOntoTheGrillAndHisses():
    scene = setup({0: slot(BEEF)})
    pieces = scene.pieces
    assert pieces.motion[0].pose()[0][1] == 0.0 and not sounds("ambient.skillet.addfood"), "刚加载：已经在烤架上的不演落下"
    Scenes.OnStoveLook(payload({0: slot(BEEF), 2: slot(BEEF)}))
    run(scene, DT)
    assert pieces.motion[2].pose()[0][1] > 3.0, "新放上来的从烤架上方 4 px 落下"
    run(scene, 0.25)
    assert sounds("ambient.skillet.addfood"), "落到烤架上：下料的一声"
    assert particles("arris_diegesis:steam"), "冒两口汽"
    assert abs(centerOf(drops()[0])[1] - (POS[1] + 16.3 / 16.0)) < 0.02, "落回烤架面"


def testSeveralNewPiecesLandOneAfterTheOtherFromAboveForSomeoneWatchingFromOutside():
    scene = setup({})
    Scenes.OnStoveLook(payload(dict((place, slot(BEEF)) for place in (0, 1, 2))))
    run(scene, DT)
    pieces = scene.pieces
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, False, False], "后面的先等着"
    assert pieces.motion[0].pose()[0][0] == 0.0 and pieces.motion[0].pose()[0][2] == 0.0, "旁观的人没有屏幕：从正上方落下"
    run(scene, 1.0)
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, True, True] and len(drops()) == 3


def testSeveralNewPiecesFlyInFromTheScreensBottomForTheCookWhoHasTheStationOpen():
    scene = setup({})
    scene.focus(lambda index, count: (10.0 * index, -20.0))
    Scenes.OnStoveLook(payload(dict((place, slot(BEEF)) for place in (0, 1, 2))))
    run(scene, DT)
    pieces = scene.pieces
    assert abs(pieces.motion[0].pose()[0][2] + 20.0) < 0.1 and pieces.motion[0].fromOffset == (0.0, -20.0), "从屏幕下沿那边飞来"
    run(scene, 0.3)
    assert pieces.motion[1].fromOffset == (10.0, -20.0), "第 index 件起点在屏幕下沿的第 index 个位置"
    scene.blur()
    assert scene.focused is False and scene.space.starts is None


# ---------------------------------------------------------------- 翻面

def waiting():
    return {1: slot(BEEF, True, 1.0, 0.0)}


def turned(scene, up=1.0):
    """服务端翻了一件：先发表现事件（带翻过来之后朝上那面烤到哪），再发状态（down / up 对调）。"""
    Scenes.OnStoveLook(event("turned", 1, up=up))
    Scenes.OnStoveLook(payload({1: slot(BEEF, True, 0.0, up)}))


def testAnotherCooksTurnIsShownFromTheStartWhicheverArrivesFirst():
    for stateFirst in (False, True):
        scene = setup(waiting())
        pieces = scene.pieces
        if stateFirst:
            Scenes.OnStoveLook(payload({1: slot(BEEF, True, 0.0, 1.0)}))
            Scenes.OnStoveLook(event("turned", 1, up=1.0))
        else:
            turned(scene)
        assert pieces.turnedAt[1] == pieces.clock, "别人翻的：照样演（不用开着站点）"
        run(scene, 0.1)
        assert drops()[0]["item"]["newItemName"] == BEEF, "翻到一半之前还是生的那面朝上"
        run(scene, 0.1)
        assert drops()[0]["item"]["newItemName"] == COOKED, "翻到一半换成熟的那面朝上的样子"
        run(scene, 0.3)
        assert drops()[0]["item"]["newItemName"] == COOKED
        assert sounds("block.lantern.step"), "起跳的一声"


def testTheCooksOwnTurnIsNotPlayedAgainWhenTheServerSaysSoButAnOnlookersIs():
    scene = setup(waiting())
    scene.focus(None)
    pieces = scene.pieces
    pieces.turned(1)                                         # 开着站点的人点了一下（GrillView）
    stamp = pieces.turnedAt[1]
    run(scene, 0.05)
    turned(scene)
    assert pieces.turnedAt[1] == stamp, "自己刚翻的（0.6 秒内）服务端又说一遍：不重复演"
    run(scene, 0.5)
    assert drops()[0]["item"]["newItemName"] == COOKED
    scene.blur()
    pieces.turned(1)
    stamp = pieces.turnedAt[1]
    run(scene, 0.05)
    Scenes.OnStoveLook(event("turned", 1, up=1.0))
    assert pieces.turnedAt[1] == pieces.clock != stamp, "没开站点的人：别人翻的当然演"


def testALookThatChangesWithoutATurnEffectIsDrawnAfterAShortWait():
    scene = setup(waiting())
    Scenes.OnStoveLook(payload({1: slot(BEEF, True, 1.0, 1.0)}))
    run(scene, DT)
    assert drops()[0]["item"]["newItemName"] == BEEF, "先等一等：翻面的效果可能紧跟着到"
    run(scene, 0.2)
    assert drops()[0]["item"]["newItemName"] == COOKED


def testATurnTheServerRefusedIsLaidBack():
    scene = setup(waiting())
    scene.pieces.turned(1)
    run(scene, 0.1)
    Scenes.OnStoveLook(event("unturned", 1))
    assert scene.pieces.heldUntil[1] == 0.0
    run(scene, 0.4)
    assert drops()[0]["item"]["newItemName"] == BEEF, "服务端的状态里朝上那面还是生的：画回生的"


# ---------------------------------------------------------------- 取走、弹回、烤好

def testATakenPieceLeavesAGhostAndGoesAtOnceWhicheverArrivesFirst():
    for eventFirst in (True, False):
        scene = setup({3: slot(BEEF)})
        assert len(drops()) == 1
        gone, took = payload({}), event("taken", 3, stack=item(BEEF))
        for body in ((took, gone) if eventFirst else (gone, took)):
            Scenes.OnStoveLook(body)
        run(scene, DT)
        assert len(drops()) == 1 and scene.pieces.shown[3] is None, "真的那件马上没了，换成虚影"
        run(scene, 0.1)
        assert len(drops()) == 1 and drops()[0]["scale"] < 5.0 / 8.0, "虚影缩小"
        run(scene, 0.3)
        assert drops() == [], "虚影走完收掉"


def testARefusedStackBouncesAGhostBackAndTheGrillHits():
    scene = setup({})
    Scenes.OnStoveLook(event("refused", stack=item(BEEF)))
    assert len(drops()) == 1
    run(scene, 0.1)
    assert [(s["volume"], s["pitch"]) for s in sounds("block.lantern.hit")] == [(0.4, 1.3)]
    run(scene, 0.4)
    assert drops() == []


def testLayingOnPlaysTheLanternSoundOncePerEventWhateverTheNumberOfPieces():
    """JE 的 EFFECT_PLACED：灯笼放下 0.4 / 1.1，一回一声；基岩版的 block.lantern.place 自带 1.1 倍音调，所以传 1.0 才是 JE 的 1.1。"""
    scene = setup({})
    Scenes.OnStoveLook(event("placed", places=[0, 1, 2, 3]))
    heard = sounds("block.lantern.place")
    assert len(heard) == 1 and abs(heard[0]["volume"] - 0.4) < 1.0e-9 and abs(heard[0]["pitch"] - 1.0) < 1.0e-9
    assert abs(heard[0]["pos"][0] - (POS[0] + 0.5)) < 0.01 and abs(heard[0]["pos"][2] - (POS[2] + 0.5)) < 0.01, "在烤架中心"


def testTakingOffMakesTheLittlePickUpSoundAndAMalformedTakeMakesNone():
    scene = setup({3: slot(BEEF)})
    Scenes.OnStoveLook(event("taken", 3, stack=item(BEEF)))
    assert [(s["name"], s["volume"], s["pitch"]) for s in world.sounds if s["name"] == "random.pop"] == [("random.pop", 0.3, 1.5)]
    del world.sounds[:]
    Scenes.OnStoveLook(event("taken", 4))
    assert [s for s in world.sounds if s["name"] == "random.pop"] == [], "没有东西的取走（JE 的 taken 里栈是空的直接返回）：不响"


def testAPieceDoneOnBothSidesSteamsGlintsAndChimesForEveryoneNearby():
    scene = setup({4: slot(COOKED, True, 1.0, 1.0)})
    del world.sounds[:]
    Scenes.OnStoveLook(event("grilled", 4, stack=item(COOKED)))
    kinds = [p["id"] for p in world.particles]
    assert kinds.count("arris_diegesis:steam") == 3 and kinds.count("arris_diegesis:glint") == 3
    assert [(s["name"], s["volume"], s["pitch"]) for s in world.sounds] == [("random.pop", 0.3, 1.3)], "烤好的一声（ITEM_PICKUP 0.3 / 1.3）"


# ---------------------------------------------------------------- 热气、烟、声音

def testAPieceWaitingToBeTurnedSmokesAndAnotherOneGrillingSteamsWithNobodyAtTheStation():
    scene = setup({0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0)})
    run(scene, 5.0)
    assert not scene.focused, "站点没人开着，烟照样冒"
    tints = [p["vars"].get("variable.tint_r") for p in particles("arris_diegesis:steam")]
    assert any(abs(value - 0xC8 / 255.0) < 1.0e-6 for value in tints if value is not None), "该翻的那件冒烟（灰白）"
    assert [s for s in sounds("ambient.skillet.sizzle") if s["volume"] > 0.0]
    big = [p for p in particles("arris_diegesis:steam") if p["vars"].get("variable.scale", 0.0) > 2.0]
    assert big, "烟比蒸汽大"
    assert all(abs(p["pos"][0] - (POS[0] + 0.8)) < 0.2 and abs(p["pos"][2] - (POS[2] + 0.7)) < 0.2 for p in big), "烟只从那一件（第 0 件）的边上冒"


def testAnEmptyLitGrillOnlyShimmersWithHeat():
    """JE 的 heat()：点着的烤架不管有没有东西都一阵阵热浪（每秒 1.6 个，煎锅那个 arris:pan_heat 粒子）；没有东西就没有蒸汽、烟和嗞嗞声。"""
    scene = setup({})
    run(scene, 5.0)
    assert world.sounds == []
    kinds = [p["id"] for p in world.particles]
    assert 6 <= len(kinds) <= 10 and set(kinds) == {"arris:pan_heat"}, kinds
    values = world.particles[0]["vars"]
    assert values["variable.scale"] == 3.5 and abs(values["variable.alpha"] - 0x48 / 255.0) < 1.0e-9
    assert 0.8 <= values["variable.life"] <= 1.3 and values["variable.speed_set"] == 1.0
    assert all(POS[1] + 1.0 + 1.9 / 16.0 <= p["pos"][1] <= POS[1] + 1.0 + 4.1 / 16.0 for p in world.particles), "高出烤架面 2~4 像素"


def testAFarAwaySceneIsDrawnButMakesNoParticlesOrSounds():
    scene = setup({0: slot(BEEF, True, 1.0, 0.0)})
    del world.particles[:], world.sounds[:]                   # 建的那一帧是近的，热气的第一声已经响过了
    run(scene, 3.0, near=False)
    assert world.particles == [] and world.sounds == [] and len(drops()) == 1
    scene.pieces.turned(0)
    run(scene, 0.1, near=False)
    assert drops()[0]["pivot"][1] > POS[1] + 16.3 / 16.0 + 0.05, "翻起来的动作还在算（回到近处时位置是对的）"
    assert world.sounds == [], "离得远：连翻面起跳的一声也不放"


# ---------------------------------------------------------------- 加载、重建、收拾

def saved(**kinds):
    """区块晚加载时方块实体里存着的东西：六个烤位 "0".."5" 和手放的进度 handGrill。"""
    data = {"handGrill": None}
    for place in range(6):
        data[str(place)] = {"itemDict": None, "cookTimer": 30}
    data.update(kinds)
    return data


def load(blockData):
    world.exData[POS] = blockData
    Scenes.OnBlockEntityLoaded({"blockName": "arris:stove", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    return Scenes.sceneAt(0, POS)


def testALateLoadedChunkDrawsTheStoveFromTheSavedDataWithoutFalling():
    setup()
    blockData = saved(**{"1": {"itemDict": item(BEEF), "cookTimer": 30}, "handGrill": {"byHand": [0, 1, 0, 0, 0, 0], "down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                                                                                            "up": [0.0] * 6}})
    scene = load(blockData)
    run(scene, DT)
    assert len(drops(BEEF)) == 1 and scene.pieces.motion[1].pose()[0][1] == 0.0, "加载时就躺在烤架上"
    run(scene, 4.0)
    tints = [p["vars"].get("variable.tint_r") for p in particles("arris_diegesis:steam")]
    assert any(abs(value - 0xC8 / 255.0) < 1.0e-6 for value in tints if value is not None), "存着的进度：一面熟了等着翻，烟照冒"


def testARepeatedLoadEventRebuildsTheSceneWithoutReplayingTheFalls():
    setup()
    blockData = saved(**{"0": {"itemDict": item(BEEF), "cookTimer": 30}, "2": {"itemDict": item(BEEF), "cookTimer": 30}})
    scene = load(blockData)
    run(scene, 0.5)
    first = set(world.drops)
    scene = load(blockData)
    run(scene, DT)
    assert len(drops(BEEF)) == 2 and not (first & set(world.drops)), "旧的收掉、新的重建"
    assert all(piece.pose()[0][1] == 0.0 for piece in scene.pieces.motion), "重建不演落下"
    assert not sounds("ambient.skillet.addfood")


def testTheBlockEntityGoingAwayClearsEverythingAndReleasesTheHiddenMark():
    scene = setup({0: slot(BEEF), 1: slot(BEEF)})
    Scenes.OnStoveLook(event("taken", 1, stack=item(BEEF)))
    assert drops()
    Scenes.OnBlockEntityRemoved({"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert Scenes.sceneAt(0, POS) is None and drops() == [], "件和虚影都收了"
    assert (0, POS) not in BlockItems._hidden, "以后别的方块放在这个位置不会被当成还在隐藏"


def testTheBlockGoingAwayIsNoticedEvenWithoutARemoveEvent():
    setup({0: slot(BEEF)})
    del world.blocks[POS]
    for _ in range(30):
        clock.now += 0.1
        Scenes.OnRenderTick()
    assert Scenes.sceneAt(0, POS) is None and drops() == [] and (0, POS) not in BlockItems._hidden


def testLeavingTheDimensionClearsAllScenes():
    setup({0: slot(BEEF)})
    Scenes.OnDimensionChange()
    assert Scenes._scenes == {} and drops() == []


# ---------------------------------------------------------------- 谁的广播收

def testBroadcastsOfAnotherDimensionOrAnotherBlockOrBadShapeAreDropped():
    scene = setup()
    other = payload({0: slot(BEEF)})
    other["dimensionId"] = 1
    Scenes.OnStoveLook(other)
    other = payload({0: slot(BEEF)})
    other["pos"] = [1, 2, 3]
    Scenes.OnStoveLook(other)
    for bad in (None, [], "x", {"dimensionId": 0}, dict(payload(), pos=[1, 2]), dict(payload(), pos=["a", 1, 1]), dict(payload(), pos=[1.5, 2, 3]),
                dict(payload(), pos=[True, 2, 3])):
        Scenes.OnStoveLook(bad)
    assert Scenes._scenes == {(0, POS): scene} and not scene.known, "什么也没画：别的维度、不是炉灶的位置、形状不对的都丢"
    Scenes._state["on"] = False
    Scenes.OnStoveLook(payload({0: slot(BEEF)}))
    assert not scene.known, "没装前置包（没启用）时什么都不做"


def testMalformedItemsAndEventsInAGoodBroadcastAreIgnoredItemByItem():
    scene = setup()
    body = payload()
    body["slots"][0] = {"item": {"newItemName": 5, "count": 1}}
    body["slots"][1] = {"item": {"newItemName": BEEF, "count": -1}}
    body["slots"][2] = {"item": item(BEEF), "down": "x", "up": float("nan"), "hand": 1}
    body["slots"][3] = "not a dict"
    body["slots"][4] = slot(BEEF, True, 7.0, -3.0)
    Scenes.OnStoveLook(body)
    run(scene, DT)
    assert [place for place in range(6) if scene.pieces.shown[place] is not None] == [2, 4], "只有两件是好的"
    assert scene.view.data["down"][4] == 1.0 and scene.view.data["up"][4] == 0.0 and scene.view.data["hand"][2] is False
    for bad in (dict(event("taken", 99, stack=item(BEEF))), dict(event("turned", -1)), dict(event("turned", True)), dict(event("grilled", "0")),
                dict(event("nonsense", 1)), dict(event("refused", stack="x")), dict(event("placed", places="x"))):
        Scenes.OnStoveLook(bad)


# ---------------------------------------------------------------- 每帧调度

def tick(seconds=DT):
    clock.now += seconds
    Scenes.OnRenderTick()


def testNearbyScenesRunEveryFrameFarOnesEveryFourthWithoutSoundsAndTheFarthestNotAtAll():
    scene = setup({0: slot(BEEF, True, 1.0, 0.0)})
    tick()                                                    # 第一帧只记时间
    before = scene.pieces.clock
    for _ in range(8):
        tick()
    assert abs(scene.pieces.clock - before - 8 * DT) < 1.0e-9, "离得近：每帧算"
    world.foot = (POS[0] + 0.5 + 35.0, 64.0, POS[2] + 0.5)
    del world.particles[:], world.sounds[:]
    before = scene.pieces.clock
    for _ in range(8):
        tick()
    assert abs(scene.pieces.clock - before - 8 * DT) < 1.0e-9, "离得远（24~48 格）：隔 4 帧算一次、每次补 4 帧的时间"
    assert world.particles == [] and world.sounds == [], "远处不放粒子和声音"
    world.foot = (POS[0] + 0.5 + 60.0, 64.0, POS[2] + 0.5)
    before = scene.pieces.clock
    for _ in range(8):
        tick()
    assert scene.pieces.clock == before, "再远不算"
    scene.focus(None)
    for _ in range(4):
        tick()
    assert scene.pieces.clock > before, "开着站点的永远每帧算"


def testASceneThatNeverGotAStateStaysBlank():
    scene = setup()
    for _ in range(10):
        tick()
    assert scene.frame(DT, True) is False and drops() == [] and world.particles == [], "第一份状态来之前不画、不冒热浪"


# ---------------------------------------------------------------- 炉灶朝哪，六件跟着转

AUX_YAW = {0: 180, 1: 270, 2: 0, 3: 90}                         # 方块的朝向状态 0 南 1 西 2 北 3 东 -> 站点朝向（度）
FRONT = {0: (0.0, 1.0), 1: (-1.0, 0.0), 2: (0.0, -1.0), 3: (1.0, 0.0)}      # 炉灶的正面朝哪（世界的 (dx, dz)）
Pose = C.load("Shared.Rules.ItemPose")


def turnedFraction(yaw, x, z):
    """方块里的一点（比例，炉灶朝北那一份）绕方块中心转到炉灶朝 yaw 时的位置：朝东 (1 - z, x)、朝南 (1 - x, 1 - z)、朝西 (z, 1 - x)。"""
    return {0: (x, z), 90: (1.0 - z, x), 180: (1.0 - x, 1.0 - z), 270: (z, 1.0 - x)}[yaw]


def uAxis(drop):
    """掉落物贴图横向（u 轴）在世界里指向哪：引擎的欧拉角还原成 R = Rz·Rx·Ry，第一列。"""
    x, y, z = drop["euler"]
    r = Pose._mul(Pose._rz(z), Pose._mul(Pose._rx(x), Pose._ry(y)))
    return (r[0][0], r[1][0], r[2][0])


def testTheSixPiecesLieWhereTheStovesFacingPutsThemAndNobodyNeedsToOpenTheStation():
    for aux, yaw in sorted(AUX_YAW.items()):
        scene = setup(dict((place, slot(BEEF)) for place in range(6)), aux=aux)
        assert scene.yaw == yaw and not scene.focused
        centers = sorted((round(centerOf(d)[0] - POS[0], 3), round(centerOf(d)[2] - POS[2], 3)) for d in drops(BEEF))
        assert centers == sorted((round(a, 3), round(b, 3)) for a, b in (turnedFraction(yaw, x, z) for x, z in FRACTIONS)), aux
        assert all(abs(centerOf(d)[1] - (POS[1] + 16.3 / 16.0)) < 1.0e-6 for d in drops(BEEF)), "高度和朝向无关：躺在烤架面上"


def testEachPieceKeepsItsOwnAngleToTheStovesFrontWhateverWayItFaces():
    """每件摆得各转一点（HoD 的 yaw）：件的 u 轴和炉灶正面的夹角是它自己的，炉灶朝哪都不变（整座一起转）。"""
    for aux, yaw in sorted(AUX_YAW.items()):
        scene = setup(dict((place, slot(BEEF)) for place in range(6)), aux=aux)
        pieces = dict((place, scene.pieces.props[place][1].entityId) for place in range(6))
        for place, entityId in pieces.items():
            u = uAxis(world.drops[entityId])
            front, turn = FRONT[aux], math.radians(Layout.yawOf(place))
            assert abs(u[1]) < 1.0e-9, "平躺"
            assert abs(u[0] * front[0] + u[2] * front[1] - math.sin(turn)) < 1.0e-6, (aux, place, u)


def testSmokeAndSteamComeFromThePieceWhereverTheStoveFaces():
    for aux, yaw in sorted(AUX_YAW.items()):
        scene = setup({0: slot(BEEF, True, 1.0, 0.0)}, aux=aux)
        del world.particles[:]
        run(scene, 5.0)
        big = [p for p in particles("arris_diegesis:steam") if p["vars"].get("variable.scale", 0.0) > 2.0]
        assert big, aux
        x, z = turnedFraction(yaw, FRACTIONS[0][0], FRACTIONS[0][1])
        assert all(abs(p["pos"][0] - (POS[0] + x)) < 0.2 and abs(p["pos"][2] - (POS[2] + z)) < 0.2 for p in big), (aux, "烟只从那一件的边上冒")


def testTheGrillCentreDoesNotMoveWhenTheStoveTurns():
    for aux in range(4):
        scene = setup({}, aux=aux)
        del world.sounds[:]
        Scenes.OnStoveLook(event("placed", places=[0]))
        heard, = sounds("block.lantern.place")
        assert abs(heard["pos"][0] - (POS[0] + 0.5)) < 1.0e-6 and abs(heard["pos"][2] - (POS[2] + 0.5)) < 1.0e-6, aux


def testTheSceneReadsTheStovesFacingWhenItIsBuilt():
    scene = setup(aux=3)
    assert scene.yaw == 90 and scene.space.yaw == 90 and scene.view.yaw == 90 and scene.view.props.yaw == 90
    world.blocks[(3, 64, 3)] = ("arris:stove", 1)
    assert Scenes.ensure(0, (3, 64, 3)).yaw == 270


def testAReloadedBlockEntityThatFacesAnotherWayRedrawsEverythingTurnedAndWithoutFalling():
    """区块重新加载时方块的朝向和建场景时不一样（换了个方向的炉灶放在同一处没收到移除事件）：件按新朝向重摆，样子还在，不演落下。"""
    scene = setup({0: slot(BEEF)}, aux=2)
    first = centerOf(drops()[0])
    world.blocks[POS] = ("arris:stove", 3)
    del world.sounds[:]
    scene = load(saved(**{"0": {"itemDict": item(BEEF), "cookTimer": 30}}))
    run(scene, DT)
    assert scene.yaw == 90 and len(drops(BEEF)) == 1
    x, z = turnedFraction(90, FRACTIONS[0][0], FRACTIONS[0][1])
    assert abs(centerOf(drops()[0])[0] - (POS[0] + x)) < 1.0e-6 and abs(centerOf(drops()[0])[2] - (POS[2] + z)) < 1.0e-6
    assert (centerOf(drops()[0])[0], centerOf(drops()[0])[2]) != (first[0], first[2])
    assert scene.pieces.motion[0].pose()[0][1] == 0.0 and not sounds("ambient.skillet.addfood"), "重建不演落下"


def testTurningTheSceneInPlaceKeepsTheLookAndIsANoOpForTheSameFacing():
    scene = setup({0: slot(BEEF), 4: slot(BEEF)})
    before = sorted((d["pivot"], d["euler"]) for d in drops())
    scene.turn(0)
    assert sorted((d["pivot"], d["euler"]) for d in drops()) == before and scene.known
    scene.turn(180)
    run(scene, DT)
    assert len(drops(BEEF)) == 2 and scene.known and sorted((d["pivot"], d["euler"]) for d in drops()) != before
    assert scene.yaw == scene.space.yaw == scene.view.yaw == 180


def testTheDisplayWithoutTheSceneIsDrawnWhereTheScenesPiecesWouldBe():
    """没开站点、也没装前置包时世界里的展示（Client/BlockItems 按 Shared/Rules/BlockDisplay 摆）和场景里的画面是同一套：炉灶朝哪，
    六件的水平位置和每件的朝向都一样（高度差一点点：展示是 FD 的 1.015 格，场景是实机标定的 16.3 像素）。"""
    for aux in range(4):
        world.reset()
        world.blocks[POS] = ("arris:stove", aux)
        Scenes._scenes.clear()
        BlockItems._hidden.clear()
        BlockItems._last.clear()
        BlockItems._shown.clear()
        BlockItems.show(0, POS, "stove", dict((str(place), item(BEEF)) for place in range(6)))
        displayed = sorted((round(centerOf(d)[0], 4), round(centerOf(d)[2], 4), tuple(round(v, 3) for v in d["euler"])) for d in drops(BEEF))
        assert len(displayed) == 6
        BlockItems.clear(0, POS)
        assert drops() == []
        Scenes.enable()
        scene = Scenes.ensure(0, POS)
        Scenes.OnStoveLook(payload(dict((place, slot(BEEF)) for place in range(6))))
        run(scene, DT)
        drawn = sorted((round(centerOf(d)[0], 4), round(centerOf(d)[2], 4), tuple(round(v, 3) for v in d["euler"])) for d in drops(BEEF))
        assert drawn == displayed, aux


if __name__ == "__main__":
    raise SystemExit(C.dgtest.run(globals()))
