# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点开着的人的那一层（Compat/Diegesis/GrillView.py + GrillPieces.py + GrillSpace.py + GrillGhosts.py + GrillFx.py）：
用前置包客户端的假引擎（dgstation）驱动真的 StationView，从指针点击一路看到发出的动作、摆下的客户端掉落物、放的粒子和声音。
对应 Hands-On Delight 的 StoveBehavior（onEvent / onItemClick / refresh / turned / onEffect）。"""
from __future__ import print_function

import importlib
import math
import random
import sys
import types

import dgstation
import dgtest
import fdtest

world = dgstation.install()
_engine = sys.modules[dgtest.SCRIPTS + ".Client.Engine"]


class Recorder(object):
    def __init__(self):
        self.created, self.variables, self.played = [], [], []

    def Create(self, identifier, pos):
        self.created.append((identifier, tuple(pos)))
        return len(self.created)

    def SetVariable(self, particleId, name, value):
        self.variables.append((particleId, name, value))

    def PlayCustomMusic(self, name, pos, volume, pitch, loop, entity):
        self.played.append((name, tuple(pos), volume, pitch))
        return "id"


class Factory(object):
    """前置包的假引擎再加上粒子和声音的记账。"""

    def __init__(self, inner):
        self.inner, self.recorder = inner, Recorder()

    def CreateParticleSystem(self, _):
        return self.recorder

    def CreateCustomAudio(self, _):
        return self.recorder

    def __getattr__(self, name):
        return getattr(self.inner, name)


factory = Factory(_engine.compFactory)
_engine.compFactory = factory
sys.modules[fdtest.SCRIPTS + ".Client.Engine"] = _engine
_hidden = []
_stub = types.ModuleType(fdtest.SCRIPTS + ".Client.BlockItems")
_stub.hide = lambda dimensionId, pos, hidden: _hidden.append((dimensionId, tuple(pos), hidden))
sys.modules[fdtest.SCRIPTS + ".Client.BlockItems"] = _stub
setattr(importlib.import_module(fdtest.SCRIPTS + ".Client"), "BlockItems", _stub)       # py2 的 from 包 import 子模块要包上有这个属性

GrillView = fdtest.load("Compat.Diegesis.GrillView")
Rules = fdtest.load("Shared.Rules.GrillStation")
Layout = fdtest.load("Shared.Rules.HandsOn.StoveLayout")
Motion = fdtest.load("Shared.Rules.HandsOn.StoveMotion")
Registry = dgstation.load("Client.Registry")
View = dgstation.load("Client.View")
Ports = dgstation.load("Client.Ports")
Schema = dgtest.load("Shared.Schema")
Pick = dgtest.load("Shared.Pick")

STOVE = (10, 64, 10)
BEEF, COOKED = "minecraft:beef", "minecraft:cooked_beef"


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


class Api(object):
    StationBehavior = Registry.StationBehavior
    registerBehavior = staticmethod(Registry.registerBehavior)
    box = staticmethod(View.box)
    API_VERSION = 2
    Schema = Schema


class Book(object):
    pass


def make(yaw=0, pieces=None, data=None):
    """打开着的炉灶站点：yaw 是玩家所在的一侧（0 北、90 东……），pieces 是 {位置: 物品}，data 是站点数据。"""
    world.reset()
    del _hidden[:]
    factory.recorder = Recorder()
    random.seed(3)
    behaviorClass = GrillView.register(Api)
    entry = Registry.getBehavior("arris:stove")
    view = View.StationView(entry, STOVE, 0, yaw, Ports.Ports(lambda: shot(yaw)))
    view.behavior = behaviorClass(view)
    view.opened = True
    view.book = lambda source: setattr(view, "bookSource", source)
    view.refreshBook = lambda: None
    world.camera["pose"], world.camera["fov"] = shot(yaw)[0], 30.0
    for place, stack in (pieces or {}).items():
        view.state.rawSetItem(("grill", place), stack)
    view.data = data or {"down": [0.0] * 6, "up": [0.0] * 6, "hand": [False] * 6}
    view.behavior.onOpen()
    return view


def shot(yaw):
    """JE 的机位：站点像素的 (8, 50.5, -21) 看 (8, 16, 8)，换成世界里的相机位姿 (x, y, z, 偏航, 俯仰向下为正)。"""
    Geometry = dgtest.load("Shared.Geometry")
    toWorld = lambda point: Geometry.stationPointToWorld(yaw, point[0], point[1], point[2], STOVE[0], STOVE[1], STOVE[2])
    x, y, z = toWorld(Layout.CAMERA["pos"])
    tx, ty, tz = toWorld(Layout.CAMERA["target"])
    dx, dy, dz = tx - x, ty - y, tz - z
    return ((x, y, z, math.degrees(math.atan2(-dx, dz)), math.degrees(math.atan2(-dy, math.sqrt(dx * dx + dz * dz)))), 30.0)


def screenOf(view, place):
    """第 place 件的中心在界面上的位置。"""
    x, y, z = view.behavior.space.centers()[place]
    found = view.project((x, y, z))
    return (found[0], found[1])


def click(view, place, button=0, quick=False):
    screen = screenOf(view, place)
    view.pointer("move", screen)
    consumed = view.pointer("down", screen, button, quick)
    view.pointer("up", screen, button, quick)
    return consumed


def actions(raw=None):
    return [(a["name"], a["data"]) for a in world.actions() if a.get("type") == "custom"]


def run(view, seconds, dt=1.0 / 60.0):
    for _ in range(int(round(seconds / dt))):
        view.behavior.frame(dt)


def drops():
    return world.liveDrops()


def center(drop):
    return drop["pos"]


# ---------------------------------------------------------------- 开站

def testTheStationOpensTheJeWayWithoutHintRowOrDrawer():
    view = make()
    behavior = view.behavior
    assert behavior.chrome == "java" and behavior.flightSeconds == 0.4 and behavior.workPlane == 17.0
    assert behavior.camera["pos"] == (8.0, 50.5, -21.0) and behavior.camera["target"] == (8.0, 16.0, 8.0) and behavior.camera["fov"] == 30.0
    assert abs(behavior.camera["keepWidth"] - 16.0 / 9.0) < 1.0e-9
    assert _hidden == [(0, STOVE, True)], "开站期间本端不画世界里的那份"
    assert behavior.usable(item(BEEF)) and not behavior.usable(item("minecraft:egg")) and not behavior.usable(item("minecraft:bread"))
    assert behavior.mayDrop("grill", 0, item(BEEF)) and not behavior.mayDrop("grill", 0, item("minecraft:stick"))
    behavior.onClose()
    assert _hidden[-1] == (0, STOVE, False), "关站还原"
    assert view.bookSource.__class__.__name__ == "GrillSource", "食谱书照旧挂"


def testASixPieceGrillShowsEachPieceWhereTheWorldHasIt():
    view = make(pieces=dict((place, item(BEEF)) for place in range(6)))
    live = drops()
    assert len(live) == 6 and all(drop["item"]["newItemName"] == BEEF for drop in live)
    centers = [view.toWorld(*c) for c in view.behavior.space.centers()]
    assert [(round(x - STOVE[0], 3), round(z - STOVE[2], 3)) for x, _, z in centers] ==         [(0.8, 0.7), (0.5, 0.7), (0.2, 0.7), (0.8, 0.3), (0.5, 0.3), (0.2, 0.3)], "stove.json 的 piece_0 ~ piece_5"
    assert all(abs(d["scale"] - 5.0 / 8.0) < 1.0e-9 for d in live), "一件 5 像素宽"
    assert len(set(tuple(round(v, 3) for v in d["rot"]) for d in live)) == 6, "每件摆得各转一点，没有两件同向"


def testTheSidePlayersOpenFromTurnsTheLayoutWithTheWorld():
    north = make(yaw=0, pieces={0: item(BEEF), 4: item(BEEF)})
    where = sorted((d["pos"], d["rot"]) for d in drops())
    for yaw in (90, 180, 270):
        side = make(yaw=yaw, pieces={0: item(BEEF), 4: item(BEEF)})
        got = sorted((d["pos"], d["rot"]) for d in drops())
        for (pos, rot), (pos2, rot2) in zip(where, got):
            assert max(abs(a - b) for a, b in zip(pos, pos2)) < 1.0e-6, (yaw, pos, pos2)
            assert max(abs(((a - b + 180.0) % 360.0) - 180.0) for a, b in zip(rot, rot2)) < 1.0e-6, (yaw, rot, rot2)
        assert side.behavior.space.centers()[0] != north.behavior.space.centers()[0], "站点空间里的位置随玩家的一侧转"


def testTheYawTheServerSendsAtOpenIsUsedNotTheClientsGuess():
    """Controller 先按客户端猜的一侧建表现，服务端的 Opened 可能改 view.yaw，再调 onOpen：件的坐标和朝向要按改后的算。"""
    reference = make(yaw=90, pieces={0: item(BEEF)})
    want = [(d["pos"], d["rot"]) for d in drops()]
    world.reset()
    behaviorClass = GrillView.register(Api)
    entry = Registry.getBehavior("arris:stove")
    view = View.StationView(entry, STOVE, 0, 0, Ports.Ports(lambda: shot(90)))
    view.behavior = behaviorClass(view)
    view.opened = True
    view.yaw = 90                                         # Opened 里服务端给的朝向
    world.camera["pose"], world.camera["fov"] = shot(90)[0], 30.0
    view.state.rawSetItem(("grill", 0), item(BEEF))
    view.data = {"down": [0.0] * 6, "up": [0.0] * 6, "hand": [False] * 6}
    view.behavior.onOpen()
    got = [(d["pos"], d["rot"]) for d in drops()]
    assert got == want and view.behavior.space.centers() == reference.behavior.space.centers()


# ---------------------------------------------------------------- 手

def testClickingAPieceTurnsItAndSendsTurnAndTheHopStarts():
    view = make(pieces={1: item(BEEF)}, data={"down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [False, True] + [False] * 4})
    before = center(drops()[0])
    assert click(view, 1)
    assert actions() == [("turn", {"place": 1})]
    run(view, 0.145)
    assert view.behavior.pieces.motion[1].pose()[0][1] > 2.5 and center(drops()[0]) != before, "跳起来了：半程升到 3 px"
    assert [name for name, _, _, _ in factory.recorder.played][:1] == ["block.lantern.step"], "翻面起跳的一声"


def testAClickTooSoonAfterATurnIsNotSent():
    view = make(pieces={1: item(BEEF)})
    click(view, 1)
    run(view, 0.2)
    world.calls[:] = []
    assert click(view, 1) and actions() == [], "还在空中：吞掉这一下"
    run(view, 0.3)
    assert click(view, 1) and actions() == [("turn", {"place": 1})], "落下之后又能翻"


def testTheRightButtonTakesAPieceAndADonePieceIsTakenByEitherButton():
    view = make(pieces={0: item(BEEF), 2: item(COOKED)})
    assert click(view, 0, button=1)
    assert click(view, 2, button=0)
    assert click(view, 2, button=1)
    assert actions() == [("take", {"place": 0}), ("take", {"place": 2}), ("take", {"place": 2})]


def testClickingBesideThePiecesDoesNothing():
    view = make(pieces={0: item(BEEF)})
    screen = screenOf(view, 5)
    view.pointer("move", screen)
    assert view.pointer("down", screen, 0, False) is False
    assert view.pointer("down", screen, 1, False) is False and actions() == []


# ---------------------------------------------------------------- 拿着一叠点烤架

def testAStackInTheHandGoesOnEverywhereWithTheLeftButtonAndOnTheNearestFreePlaceWithTheRight():
    view = make(pieces={1: item(BEEF)})
    view.setHand(item(BEEF, 5))
    assert [node.key for node in view.behavior.pickables()] == ["mouth"], "拿着东西时整个烤架面是一块"
    assert click(view, 4)
    assert actions()[-1] == ("place", {}), "左键：每个空位一件"
    assert click(view, 4, button=1)
    assert actions()[-1] == ("place", {"one": True, "place": 4}), "右键：离光标最近的空位"
    assert click(view, 0, button=1)
    assert actions()[-1] == ("place", {"one": True, "place": 0})
    assert click(view, 1, button=1)
    near = actions()[-1][1]["place"]
    assert near in (0, 2, 4) and near != 1, "光标在占着的第 1 件上：最近的空位是它旁边的"


def testRightClickingElsewhereWithAStackInHandIsLeftToTheKernelToPutAway():
    view = make(pieces={1: item(BEEF)})
    view.setHand(item(BEEF, 5))
    assert view.pointer("down", (5.0, 5.0), 1, False) is False, "点在烤架以外：不接，内核放回背包"
    assert world.actions()[-1]["click"] == "PUT_AWAY"


# ---------------------------------------------------------------- 效果

def testANewPieceDropsOnToTheHotGrillAndHisses():
    view = make()
    view.state.rawSetItem(("grill", 2), item(BEEF))
    view.data = {"down": [0.0] * 6, "up": [0.0] * 6, "hand": [False, False, True, False, False, False]}
    view.behavior.onState(None)
    assert view.behavior.pieces.motion[2].pose()[0][1] == 4.0, "从烤架上方 4 px 落下"
    run(view, 0.25)
    assert [p for p in factory.recorder.played if p[0] == "ambient.skillet.addfood"], "落到烤架上：下料的一声"
    assert factory.recorder.created, "冒两口汽"
    assert abs(center(drops()[0])[1] - (STOVE[1] + 1.0 + (16.3 - 16.0) / 16.0)) < 0.02, "落回烤架面"


def testSeveralPiecesLandOneAfterTheOtherComingInFromTheScreensBottom():
    view = make()
    for place in (0, 1, 2):
        view.state.rawSetItem(("grill", place), item(BEEF))
    view.behavior.onState(None)
    pieces = view.behavior.pieces
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, False, False], "后面的先等着"
    offset = pieces.motion[0].pose()[0]
    assert offset[2] < -5.0, "从屏幕下沿那边（离相机近的一侧）飞来"
    run(view, 1.0)
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, True, True]
    assert len(drops()) == 3


def serverTurned(view, place, down=0.0, up=1.0):
    """服务端翻了一件：前置包先发状态（down / up 对调）、后发表现事件（带翻过来之后朝上那面烤到哪）。"""
    data = dict((key, list(values)) for key, values in view.data.items())
    data["down"][place], data["up"][place] = down, up
    view.data = data
    view.behavior.onState(None)
    view.behavior.onEffect("turned", {"place": place, "up": up})


def testAnotherCooksTurnIsShownFromTheStartEvenThoughTheStateComesFirst():
    view = make(pieces={1: item(BEEF)}, data={"down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [False, True] + [False] * 4})
    pieces = view.behavior.pieces
    serverTurned(view, 1)
    assert pieces.turnedAt[1] == pieces.clock, "别人翻的：照样演"
    run(view, 0.1)
    assert drops()[0]["item"]["newItemName"] == BEEF, "翻到一半之前还是生的那面朝上"
    run(view, 0.1)
    assert drops()[0]["item"]["newItemName"] == COOKED, "翻到一半换成熟的那面朝上的样子"
    run(view, 0.3)
    assert drops()[0]["item"]["newItemName"] == COOKED and actions() == [], "效果不发动作"


def testMyOwnTurnIsNotPlayedAgainWhenTheServerSaysSo():
    view = make(pieces={1: item(BEEF)}, data={"down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [False, True] + [False] * 4})
    pieces = view.behavior.pieces
    click(view, 1)
    stamp = pieces.turnedAt[1]
    run(view, 0.05)
    serverTurned(view, 1)
    assert pieces.turnedAt[1] == stamp, "自己刚翻的（0.6 秒内）服务端又说一遍：不重复演"
    run(view, 0.4)
    assert drops()[0]["item"]["newItemName"] == COOKED and len(actions()) == 1


def testALookThatChangesWithoutATurnEffectIsDrawnAfterAShortWait():
    view = make(pieces={1: item(BEEF)}, data={"down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [False, True] + [False] * 4})
    data = dict((key, list(values)) for key, values in view.data.items())
    data["up"][1] = 1.0
    view.data = data
    view.behavior.onState(None)
    assert drops()[0]["item"]["newItemName"] == BEEF, "先等一等：翻面的效果可能紧跟着到"
    run(view, 0.2)
    assert drops()[0]["item"]["newItemName"] == COOKED


def testATurnTheServerRefusedIsLaidBack():
    view = make(pieces={1: item(BEEF)}, data={"down": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [False, True] + [False] * 4})
    pieces = view.behavior.pieces
    click(view, 1)
    run(view, 0.1)
    view.behavior.onEffect("unturned", {"place": 1})
    assert pieces.heldUntil[1] == 0.0
    run(view, 0.4)
    assert drops()[0]["item"]["newItemName"] == BEEF, "服务端的状态里朝上那面还是生的：画回生的"


def testATakenPieceLeavesAGhostAndGoesAtOnce():
    view = make(pieces={3: item(BEEF)})
    assert len(drops()) == 1
    view.state.rawSetItem(("grill", 3), None)            # 前置包先发状态（那一格空了），后发表现事件
    view.behavior.onState(None)
    assert drops() == [], "真的那件马上没了"
    view.behavior.onEffect("taken", {"place": 3, "stack": item(BEEF)})
    assert len(drops()) == 1 and view.behavior.pieces.shown[3] is None, "真的那件马上没了，换成虚影"
    run(view, 0.1)
    assert len(drops()) == 1 and drops()[0]["scale"] < 5.0 / 8.0, "虚影缩小"
    run(view, 0.3)
    assert drops() == [], "虚影走完收掉"


def testARefusedStackBouncesAGhostBack():
    view = make()
    view.behavior.onEffect("refused", {"stack": item(BEEF)})
    assert len(drops()) == 1
    run(view, 0.1)
    assert [p for p in factory.recorder.played if p[0] == "block.lantern.hit"]
    run(view, 0.4)
    assert drops() == []


def testPiecesLaidWhenTheStationOpensFlyInOnceTheCameraIsThere():
    """右键拿着食物开站：摆上去的在第一份状态里就有了；placed 事件带着位置，镜头到位（第一帧）之后才演落下。"""
    view = make(pieces={0: item(BEEF), 1: item(BEEF), 2: item(BEEF)})
    pieces = view.behavior.pieces
    view.behavior.onEffect("placed", {"places": [1, 2]})
    assert pieces.pending == [1, 2]
    run(view, 1.0 / 60.0)
    assert pieces.motion[1].visible and not pieces.motion[2].visible and pieces.motion[0].visible
    run(view, 1.0)
    assert pieces.motion[2].visible


def testAPieceDoneOnBothSidesSteamsAndGlints():
    view = make(pieces={4: item(COOKED)})
    view.behavior.onEffect("grilled", {"place": 4, "stack": item(COOKED)})
    kinds = [identifier for identifier, _ in factory.recorder.created]
    assert kinds.count("arris_diegesis:steam") == 3 and kinds.count("arris_diegesis:glint") == 3
    assert not factory.recorder.played, "叮的一声世界里的广播已经有了，这里不重复"


def testAPieceWaitingToBeTurnedSmokesAndAnotherOneGrillingSteams():
    view = make(pieces={0: item(BEEF), 1: item(BEEF)},
                data={"down": [1.0, 0.3, 0.0, 0.0, 0.0, 0.0], "up": [0.0] * 6, "hand": [True, True] + [False] * 4})
    run(view, 5.0)
    colours = [value for _, name, value in factory.recorder.variables if name == "variable.tint_r"]
    assert any(abs(value - 0xC8 / 255.0) < 1.0e-6 for value in colours), "该翻的那件冒烟（灰白）"
    assert [p for p in factory.recorder.played if p[0] == "ambient.skillet.sizzle" and p[2] > 0.0]
    big = [value for _, name, value in factory.recorder.variables if name == "variable.scale" and value > 2.0]
    assert big, "烟比蒸汽大"


def testNothingHeatsUpWhenNothingIsOnTheGrill():
    view = make()
    run(view, 5.0)
    assert factory.recorder.played == [] and factory.recorder.created == []


def testHoveringAPieceGivesNoFeedbackAsInJava():
    """JE 的烤件不是可交互节点（stove.json 里 piece_N 只有碰撞盒）：悬停不抬起、不描边、没有提示。"""
    view = make(pieces={2: item(BEEF)})
    rest = center(drops()[0])[1]
    view.pointer("move", screenOf(view, 2))
    run(view, 0.6)
    assert abs(center(drops()[0])[1] - rest) < 0.002 and not view.overlay.lines, "悬着什么都不变"
    assert not hasattr(GrillView, "HOVER") and not hasattr(GrillView, "nameOf"), "早先的抬起 + 名字的替代做法已经删掉"


def testAnOldFrontDoorGetsNoBehavior():
    class Old(Api):
        API_VERSION = 1
    Registry.clearAll()
    assert GrillView.register(Old) is None and Registry.getBehavior("arris:stove") is None


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
