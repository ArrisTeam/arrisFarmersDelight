# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点开着的人的那一层（Compat/Diegesis/GrillView.py + GrillSpace.py）：用前置包客户端的假引擎（dgstation）驱动真的 StationView，
从指针点击一路看到发出的动作、场景里摆下的客户端掉落物。烤架上的画面（落下 / 翻面 / 取走的动作、热气、声音）是谁都看得见的场景，
在 test_stove_scene.py 里测；这里测站点这一层和场景的接口：命中盒和场景画的对得上、开站把飞入的起点和方向交给场景、
自己翻的不重复演、被拒的虚影往开站点的人这边弹。对应 Hands-On Delight 的 StoveBehavior（onEvent / onItemClick）。"""
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


def _addDropItem(item, dimensionId, pos):
    """Client/Engine.addDropItem 的替身：建掉落物、关影子。"""
    entityId = factory.CreateItem(None).AddDropItemToWorld(item, dimensionId, pos, 0, 0)
    factory.CreateModel(entityId).SetEntityShadowShow(False)
    return entityId


_engine.addDropItem = _addDropItem
_engine.unwrapDeep = lambda value: value
_engine.blockEntityExData = lambda pos: {}
sys.modules[fdtest.SCRIPTS + ".Client.Engine"] = _engine
_hidden = []
_stub = types.ModuleType(fdtest.SCRIPTS + ".Client.BlockItems")
_stub.hide = lambda dimensionId, pos, hidden: _hidden.append((dimensionId, tuple(pos), hidden))
_stub.release = lambda dimensionId, pos: _hidden.append((dimensionId, tuple(pos), "released"))
sys.modules[fdtest.SCRIPTS + ".Client.BlockItems"] = _stub
setattr(importlib.import_module(fdtest.SCRIPTS + ".Client"), "BlockItems", _stub)       # py2 的 from 包 import 子模块要包上有这个属性
_qu = fdtest.SCRIPTS + ".QuModLibs"
_package = types.ModuleType(_qu)
_package.__path__ = []
_client = types.ModuleType(_qu + ".Client")
_client.Listen = lambda name: (lambda fn: fn)
_client.AllowCall = lambda fn: fn
sys.modules[_qu], sys.modules[_qu + ".Client"] = _package, _client

GrillView = fdtest.load("Compat.Diegesis.GrillView")
Scenes = fdtest.load("Compat.Diegesis.StoveScenes")
Rules = fdtest.load("Shared.Rules.GrillStation")
Layout = fdtest.load("Shared.Rules.HandsOn.StoveLayout")
State = fdtest.load("Shared.Rules.StoveLookState")
Registry = dgstation.load("Client.Registry")
View = dgstation.load("Client.View")
Ports = dgstation.load("Client.Ports")
Schema = dgtest.load("Shared.Schema")
Pick = dgtest.load("Shared.Pick")

STOVE = (10, 64, 10)
BEEF, COOKED = "minecraft:beef", "minecraft:cooked_beef"
DT = 1.0 / 60.0


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


class Api(object):
    StationBehavior = Registry.StationBehavior
    registerBehavior = staticmethod(Registry.registerBehavior)
    box = staticmethod(View.box)
    API_VERSION = 2
    Schema = Schema


def lookOf(pieces, data):
    """场景要的样子：pieces 是 {位置: 物品}，data 是 down / up / hand 三个长 6 的列表。"""
    data = data or {"down": [0.0] * 6, "up": [0.0] * 6, "hand": [False] * 6}
    slots = [{"item": pieces[place], "hand": data["hand"][place], "down": data["down"][place], "up": data["up"][place]}
             if place in (pieces or {}) else {} for place in range(6)]
    return State.decode({"slots": slots})


def make(yaw=0, pieces=None, data=None):
    """打开着的炉灶站点：yaw 是玩家所在的一侧（0 北、90 东……），pieces 是 {位置: 物品}，data 是两面烤到哪。场景已经画好（走了一帧）。"""
    world.reset()
    del _hidden[:]
    Scenes._scenes.clear()
    Scenes.enable()
    factory.recorder = Recorder()
    random.seed(3)
    world.blocks[STOVE] = "arris:stove"
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
    view.behavior.onOpen()
    view.behavior.scene.applyLook(lookOf(pieces, data))
    run(view, DT)
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


def run(view, seconds, dt=DT):
    """场景自己每个渲染帧走（StoveScenes.OnRenderTick）；这里直接推它。"""
    for _ in range(int(round(seconds / dt))):
        view.behavior.scene.frame(dt, True)


def drops():
    return world.liveDrops()


def center(drop):
    return drop["pos"]


def centerOf(drop):
    """掉落物的视觉中心：轴心 + 贴图的"上"方向 * 半边长。"""
    x, y, z = [math.radians(angle) for angle in drop["rot"]]
    half = 8.0 / 16.0 * drop["scale"] * 0.5
    up = (-math.sin(z) * math.cos(x), math.cos(z) * math.cos(x), math.sin(x))
    return tuple(drop["pos"][axis] + up[axis] * half for axis in range(3))


def serverEvent(name, place=None, **data):
    body = {"dimensionId": 0, "pos": list(STOVE), "event": name}
    if place is not None:
        body["place"] = place
    body.update(data)
    Scenes.OnStoveLook(body)


# ---------------------------------------------------------------- 开站

def testTheStationOpensTheJeWayWithoutHintRowOrDrawer():
    view = make()
    behavior = view.behavior
    assert behavior.chrome == "java" and behavior.flightSeconds == 0.4 and behavior.workPlane == 17.0
    assert behavior.camera["pos"] == (8.0, 50.5, -21.0) and behavior.camera["target"] == (8.0, 16.0, 8.0) and behavior.camera["fov"] == 30.0
    assert abs(behavior.camera["keepWidth"] - 16.0 / 9.0) < 1.0e-9
    assert _hidden == [(0, STOVE, True)], "烤架上的东西由场景画，本端不画世界里的那份（场景建好时就藏了，不是开站才藏）"
    assert behavior.usable(item(BEEF)) and not behavior.usable(item("minecraft:egg")) and not behavior.usable(item("minecraft:bread"))
    assert behavior.mayDrop("grill", 0, item(BEEF)) and not behavior.mayDrop("grill", 0, item("minecraft:stick"))
    assert view.bookSource.__class__.__name__ == "GrillSource", "食谱书照旧挂"
    behavior.onClose()
    assert _hidden == [(0, STOVE, True)], "关站不动世界里的那份：场景还在画，谁都看得见"
    assert behavior.scene is None and Scenes.sceneAt(0, STOVE) is not None, "站点这一层放手了，场景留着"


def testTheStationHandsItsHandToTheSceneAndTakesItBackWhenItCloses():
    view = make(pieces={0: item(BEEF)})
    scene = Scenes.sceneAt(0, STOVE)
    assert view.behavior.scene is scene and scene.focused, "本人开着站点"
    assert scene.space.starts == view.behavior.space.fromPlayerInWorld and scene.space.turner == view.behavior.space.turn
    view.behavior.onClose()
    assert not scene.focused and scene.space.starts is None and scene.space.turner is None
    assert len(drops()) == 1, "站点关了，烤架上的东西还在场景里"


def testWithoutAStoveBlockThereIsNoSceneAndThePickBoxesAreEmpty():
    world.reset()
    del _hidden[:]
    Scenes._scenes.clear()
    behaviorClass = GrillView.register(Api)
    view = View.StationView(Registry.getBehavior("arris:stove"), STOVE, 0, 0, Ports.Ports(lambda: shot(0)))
    view.behavior = behaviorClass(view)
    view.behavior.onOpen()                                      # world.blocks 里那里是空气
    assert view.behavior.scene is None and view.behavior.pickables() == []


# ---------------------------------------------------------------- 命中盒和场景对得上

def testThePickBoxesSitWhereTheSceneDrawsThePiecesWhicheverSideThePlayerOpensFrom():
    for yaw in (0, 90, 180, 270):
        view = make(yaw=yaw, pieces=dict((place, item(BEEF)) for place in range(6)))
        scene = view.behavior.scene
        for place in range(6):
            station = view.toWorld(*view.behavior.space.centers()[place])
            there = scene.space.toWorld(*scene.space.centers()[place])
            assert max(abs(a - b) for a, b in zip(station, there)) < 1.0e-6, (yaw, place, station, there)
        assert sorted(node.payload for node in view.behavior.pickables()) == list(range(6)), "六件各有一个盒子"
        for place in range(6):
            world.actions()
            assert click(view, place), (yaw, place)
            assert actions()[-1] == ("turn", {"place": place}), (yaw, place)
            view.behavior.scene.pieces.turnedAt[place] = -10.0          # 不管 0.3 秒的冷却，下一件接着点
            del world.calls[:]


def testTheYawTheServerSendsAtOpenIsUsedNotTheClientsGuess():
    """Controller 先按客户端猜的一侧建表现，服务端的 Opened 可能改 view.yaw，再调 onOpen：坐标要按改后的算。"""
    reference = make(yaw=90, pieces={0: item(BEEF)})
    want = reference.behavior.space.centers()
    world.reset()
    del _hidden[:]
    Scenes._scenes.clear()
    world.blocks[STOVE] = "arris:stove"
    behaviorClass = GrillView.register(Api)
    entry = Registry.getBehavior("arris:stove")
    view = View.StationView(entry, STOVE, 0, 0, Ports.Ports(lambda: shot(90)))
    view.behavior = behaviorClass(view)
    view.opened = True
    view.yaw = 90                                         # Opened 里服务端给的朝向
    world.camera["pose"], world.camera["fov"] = shot(90)[0], 30.0
    view.state.rawSetItem(("grill", 0), item(BEEF))
    view.behavior.onOpen()
    assert view.behavior.space.centers() == want


# ---------------------------------------------------------------- 手

def waiting(place=1):
    down, hand = [0.0] * 6, [False] * 6
    down[place], hand[place] = 1.0, True
    return {"down": down, "up": [0.0] * 6, "hand": hand}


def testClickingAPieceTurnsItAndSendsTurnAndTheHopStarts():
    view = make(pieces={1: item(BEEF)}, data=waiting())
    before = center(drops()[0])
    del factory.recorder.played[:]                            # 建的那一帧里热气已经嗞过一声
    assert click(view, 1)
    assert actions() == [("turn", {"place": 1})]
    run(view, 0.145)
    assert view.behavior.scene.pieces.motion[1].pose()[0][1] > 2.5 and center(drops()[0]) != before, "跳起来了：半程升到 3 px"
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


def testMyOwnTurnIsNotPlayedAgainWhenTheServerSaysSo():
    """自己点的那一下马上演了；服务端的 turned（广播给附近所有人，开着站点的人也收到）0.6 秒内不重复。"""
    view = make(pieces={1: item(BEEF)}, data=waiting())
    pieces = view.behavior.scene.pieces
    click(view, 1)
    stamp = pieces.turnedAt[1]
    run(view, 0.05)
    serverEvent("turned", 1, up=1.0)
    assert pieces.turnedAt[1] == stamp, "自己刚翻的服务端又说一遍：不重复演"
    assert len(actions()) == 1


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


def testTheFreePlacesAreTheStationsStateNotWhatIsDrawn():
    """服务端说空的就算空：画面还在演取走的动作时，那个位置已经能放了。"""
    view = make(pieces={1: item(BEEF)})
    view.state.rawSetItem(("grill", 1), None)                 # 前置包先发状态（那一格空了），场景那边的事件还没到
    view.setHand(item(BEEF, 5))
    assert view.behavior.scene.pieces.shown[1] is not None
    assert view.behavior._free() == [True] * 6


def testRightClickingElsewhereWithAStackInHandIsLeftToTheKernelToPutAway():
    view = make(pieces={1: item(BEEF)})
    view.setHand(item(BEEF, 5))
    assert view.pointer("down", (5.0, 5.0), 1, False) is False, "点在烤架以外：不接，内核放回背包"
    assert world.actions()[-1]["click"] == "PUT_AWAY"


# ---------------------------------------------------------------- 开着站点才有的演法

def testSeveralPiecesTheCookLaysFlyInFromTheScreensBottomOneAfterTheOther():
    view = make()
    scene = view.behavior.scene
    scene.apply({"dimensionId": 0, "pos": list(STOVE), "slots": [{"item": item(BEEF), "hand": True, "down": 0.0, "up": 0.0}] * 3 + [{}] * 3})
    run(view, DT)
    pieces = scene.pieces
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, False, False], "后面的先等着"
    offset = pieces.motion[0].pose()[0]
    assert offset[2] < -5.0, "从屏幕下沿那边（离相机近的一侧）飞来"
    run(view, 1.0)
    assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, True, True] and len(drops()) == 3


def testARefusedStackBouncesTowardTheCookWhicheverSideHeStandsOn():
    for yaw in (0, 90, 180, 270):
        view = make(yaw=yaw)
        serverEvent("refused", stack=item(BEEF))
        scene = view.behavior.scene
        middle = scene.space.toWorld(*scene.space.middle())
        run(view, 0.3)
        assert len(drops()) == 1
        here = centerOf(drops()[0])
        back = (view.toWorld(0.0, 0.0, -6.0)[0] - view.toWorld(0.0, 0.0, 0.0)[0], view.toWorld(0.0, 0.0, -6.0)[2] - view.toWorld(0.0, 0.0, 0.0)[2])
        moved = (here[0] - middle[0], here[2] - middle[2])
        assert abs(moved[0] - back[0] * 0.95) < 0.03 and abs(moved[1] - back[1] * 0.95) < 0.03, (yaw, moved, back)
        run(view, 0.4)
        assert drops() == []


def testAnOnlookerWithoutTheStationSeesTheRefusedStackBounceNorth():
    view = make()
    view.behavior.onClose()
    serverEvent("refused", stack=item(BEEF))
    scene = Scenes.sceneAt(0, STOVE)
    middle = scene.space.toWorld(*scene.space.middle())
    for _ in range(18):
        scene.frame(DT, True)
    here = centerOf(drops()[0])
    assert abs(here[0] - middle[0]) < 0.03 and here[2] - middle[2] < -0.3, "没有开站点的人没有自己这边可言：往 -z（北）弹"


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
