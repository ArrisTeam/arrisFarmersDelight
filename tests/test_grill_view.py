# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点开着的人的那一层（Compat/Diegesis/GrillView.py + GrillSpace.py）：用前置包客户端的假引擎（dgstation）驱动真的 StationView，
从指针点击一路看到发出的动作、场景里摆下的客户端掉落物。烤架上的画面（落下 / 翻面 / 取走的动作、热气、声音）是谁都看得见的场景，
在 test_stove_scene.py 里测；这里测站点这一层和场景的接口：命中盒和场景画的对得上、开站把飞入的起点和方向交给场景、
自己翻的不重复演、被拒的虚影往炉灶的正面弹；站点的北面是炉灶的正面（前置包的朝向钩子），所以站点空间就是炉灶朝向的空间，场景文件里的像素坐标直接用。
对应 Hands-On Delight 的 StoveBehavior（onEvent / onItemClick）和 StoveStation（Orientation.BLOCK）。"""
from __future__ import print_function

import importlib
import math
import random
import sys
import types

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgstation
import dgtest
import fdtest
import linkkit

linkkit.link()        # 站点按装了前置包算：HandsOnOptions 没联动时说 HoD 不在（Shared/Rules/HandsOnMode）
world = dgstation.install()
_engine = sys.modules[dgtest.SCRIPTS + ".Client.Engine"]


class Recorder(object):
    def __init__(self):
        self.created, self.variables, self.played, self.ui = [], [], [], []

    def Create(self, identifier, pos):
        self.created.append((identifier, tuple(pos)))
        return len(self.created)

    def SetVariable(self, particleId, name, value):
        self.variables.append((particleId, name, value))

    def PlayCustomMusic(self, name, pos, volume, pitch, loop, entity):
        self.played.append((name, tuple(pos), volume, pitch))
        return "id"

    def PlayCustomUIMusic(self, name, volume, pitch, loop):
        self.ui.append((name, volume, pitch))                 # 内核自己的拿放声（没人接的右键放回背包）
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
    FACING_HOOK = True                            # 这一版的前置包认站点的朝向钩子（Shared/Protocol.FACING_HOOK）
    Schema = Schema


def lookOf(pieces, data):
    """场景要的样子：pieces 是 {位置: 物品}，data 是 down / up / hand 三个长 6 的列表。"""
    data = data or {"down": [0.0] * 6, "up": [0.0] * 6, "hand": [False] * 6}
    slots = [{"item": pieces[place], "hand": data["hand"][place], "down": data["down"][place], "up": data["up"][place]}
             if place in (pieces or {}) else {} for place in range(6)]
    return State.decode({"slots": slots})


FRONT = {0: (0.0, 1.0), 1: (-1.0, 0.0), 2: (0.0, -1.0), 3: (1.0, 0.0)}     # direction 状态 -> 炉灶的正面朝哪（世界 (dx, dz)）
YAW_OF_AUX = {0: 180, 1: 270, 2: 0, 3: 90}                                   # 站点的北面转到炉灶的正面那一侧（度）
SIDES = {0: (10.5, 64.0, 5.0), 90: (15.0, 64.0, 10.5), 180: (10.5, 64.0, 15.0), 270: (5.0, 64.0, 10.5)}     # 玩家站在炉灶的北 / 东 / 南 / 西


def make(aux=2, pieces=None, data=None, look=True):
    """打开着的炉灶站点：aux 是炉灶方块的朝向状态（0 南 1 西 2 北 3 东，缺省朝北）；站点的北面是炉灶的正面，开站的人站在哪一侧不影响。
    pieces 是 {位置: 物品}，data 是两面烤到哪。场景已经画好（走了一帧）；look=False：服务端的样子还没到（开站早于它），场景不知道样子。"""
    yaw = YAW_OF_AUX[aux]
    world.reset()
    del _hidden[:]
    Scenes._scenes.clear()
    Scenes.enable()
    factory.recorder = Recorder()
    random.seed(3)
    world.blocks[STOVE] = "arris:stove"
    world.blockAux[STOVE] = aux
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
    if look:
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
    assert scene.space.starts == view.behavior.space.fromPlayer
    view.behavior.onClose()
    assert not scene.focused and scene.space.starts is None
    assert len(drops()) == 1, "站点关了，烤架上的东西还在场景里"


# ---------------------------------------------------------------- 站点朝哪（JE 的 Orientation.BLOCK）

def testTheStationIsRegisteredWithTheBlockFacingHookThatSaysWhereTheStovesFrontIs():
    make()
    entry = Registry.getBehavior("arris:stove")
    assert entry.facing is GrillView.facingOf
    for aux, yaw in sorted(YAW_OF_AUX.items()):
        world.blockAux[STOVE] = aux
        assert entry.facing(STOVE, 0) == yaw, aux
    del world.blockAux[STOVE]
    assert entry.facing(STOVE, 0) == 180, "读到的 aux 是 0：引擎的缺省状态朝南"


def testTheCameraIsAtTheStovesFrontWhicheverSideThePlayerOpensFrom():
    """前置包取朝向时问登记的钩子：炉灶朝哪，镜头就在哪一面（JE 的 StoveStation 是 Orientation.BLOCK），玩家从背面、侧面右键都一样。"""
    Facing, Shot = dgstation.load("Client.Facing"), dgtest.load("Client.Shot")
    for aux, front in sorted(FRONT.items()):
        view = make()
        world.blockAux[STOVE] = aux
        entry = Registry.getBehavior("arris:stove")
        for foot in SIDES.values():
            world.foot = foot
            assert Facing.yawOf(entry, STOVE, 0) == YAW_OF_AUX[aux], (aux, foot)
        pose = Shot.stationShot(view.behavior.camera, YAW_OF_AUX[aux], STOVE)[0]
        cam = (pose[0] - (STOVE[0] + 0.5), pose[2] - (STOVE[2] + 0.5))
        assert abs(cam[0] - front[0] * 29.0 / 16.0) < 1.0e-6 and abs(cam[1] - front[1] * 29.0 / 16.0) < 1.0e-6, (aux, cam)


def testAnOlderFrontDoorWithoutTheFacingHookGetsNoBehaviorAndTheStoveStaysClassic():
    """FACING_HOOK 是新版前置包才有的名字（老版本的 registerBehavior 也不认 facing 参数，传了会 TypeError）。炉灶的场景、命中盒、世界里的展示
    都按"站点的北面是炉灶的正面"写，站点朝着玩家站的那一侧就对不上：老版本上什么也不登记，炉灶照旧走经典玩法（和 API 太旧时一样）。"""
    asked = []

    def oldRegister(stationId, blocks, factory=None, schema=None, sneakFallback=True, canOpen=None):
        asked.append(stationId)
        return Registry.registerBehavior(stationId, blocks, factory, schema, sneakFallback, canOpen)

    class OldApi(object):
        StationBehavior, box, API_VERSION, Schema = Registry.StationBehavior, staticmethod(View.box), 3, Schema
        registerBehavior = staticmethod(oldRegister)

    Registry.clearAll()
    assert GrillView.register(OldApi) is None and asked == [] and Registry.getBehavior("arris:stove") is None


def testOpeningBeforeTheLookArrivesKeepsTheOldDisplayAndTheBoxesComeWithTheLook():
    """服务端的样子丢了 / 还没到时开站点：场景建出来了但不知道烤架上有什么，这时不能把世界里原来的展示收掉（不然烤架上什么都没有），也没有命中盒；
    样子一到，场景画出来、原来的展示收掉、命中盒有了（开站那一刻服务端还会单发一份当前的样子，GrillLogic.onOpen）。"""
    view = make(look=False)
    scene = view.behavior.scene
    assert not scene.known and _hidden == [] and view.behavior.pickables() == []
    scene.apply({"dimensionId": 0, "pos": list(STOVE), "slots": [{"item": item(BEEF), "hand": True, "down": 0.0, "up": 0.0}] + [{}] * 5})
    assert _hidden == [], "样子来了，下一帧才画"
    run(view, DT)
    assert _hidden == [(0, STOVE, True)] and [node.payload for node in view.behavior.pickables()] == [0]


def testWithoutAStoveBlockThereIsNoSceneAndThePickBoxesAreEmpty():
    world.reset()
    del _hidden[:]
    Scenes._scenes.clear()
    behaviorClass = GrillView.register(Api)
    view = View.StationView(Registry.getBehavior("arris:stove"), STOVE, 0, 180, Ports.Ports(lambda: shot(180)))      # 空气的 aux 是 0：引擎的缺省朝南
    view.behavior = behaviorClass(view)
    view.behavior.onOpen()                                      # world.blocks 里那里是空气
    assert view.behavior.scene is None and view.behavior.pickables() == []


# ---------------------------------------------------------------- 命中盒和场景对得上

def testThePickBoxesSitWhereTheSceneDrawsThePiecesWhicheverWayTheStoveFaces():
    """站点空间和场景各用各的换算到世界（站点：前置包的 view.toWorld，朝向是钩子给的；场景：StoveFacing 按炉灶的朝向转），炉灶朝哪都落在同一点。"""
    for aux in range(4):
        view = make(aux=aux, pieces=dict((place, item(BEEF)) for place in range(6)))
        scene = view.behavior.scene
        assert view.yaw == YAW_OF_AUX[aux] == scene.yaw == scene.space.yaw
        for place in range(6):
            station = view.toWorld(*view.behavior.space.centers()[place])
            there = scene.space.toWorld(*scene.space.centers()[place])
            assert max(abs(a - b) for a, b in zip(station, there)) < 1.0e-6, (aux, place, station, there)
        assert sorted(node.payload for node in view.behavior.pickables()) == list(range(6)), "六件各有一个盒子"
        for place in range(6):
            world.actions()
            assert click(view, place), (aux, place)
            assert actions()[-1] == ("turn", {"place": place}), (aux, place)
            view.behavior.scene.pieces.turnedAt[place] = -10.0          # 不管 0.3 秒的冷却，下一件接着点
            del world.calls[:]


def testThePickBoxesAreTheSceneFilesPixelsAsTheyAreSinceTheStationSpaceIsTheStovesOwn():
    """站点空间就是炉灶朝向的空间：命中盒、六件的落点用 HoD 场景里的像素坐标，不用按玩家这一侧换（件的中心高度是实机标定的 16.3）。"""
    view = make(aux=1, pieces=dict((place, item(BEEF)) for place in range(6)))
    assert view.behavior.space.centers() == [(x, 16.3, z) for x, z in Layout.PIECE_AT]
    boxes = dict((node.payload, node) for node in view.behavior.pickables())
    for place in range(6):
        lo, hi = Layout.pieceBox(place)
        assert tuple(boxes[place].box) == tuple(lo) + tuple(hi), place
    view.setHand(item(BEEF, 5))
    mouth, = view.behavior.pickables()
    assert mouth.key == "mouth" and tuple(mouth.box) == tuple(Layout.MOUTH_BOX[0]) + tuple(Layout.MOUTH_BOX[1])


def testAStationThatDoesNotFaceTheStovesFrontIsRefusedAtOpenInsteadOfLayingThePiecesWrong():
    """站点的坐标按炉灶朝向写：Opened 里服务端给的朝向（view.yaw）要是和炉灶方块的不一样（前置包没按朝向钩子开站），onOpen 抛错，
    Controller 的 _guard 记下并关站——关站比把命中盒摆错了强。朝向对得上就照常。"""
    view = make(aux=2)                                    # 炉灶朝北：站点朝向 0
    behaviorClass = type(view.behavior)
    for wrong in (90, 180, 270):
        stray = View.StationView(view.entry, STOVE, 0, wrong, Ports.Ports(lambda: shot(wrong)))
        stray.behavior = behaviorClass(stray)
        try:
            stray.behavior.onOpen()
        except RuntimeError as error:
            assert str(wrong) in str(error) and "0" in str(error)
        else:
            raise AssertionError("朝向 %s 和炉灶的 0 对不上，应该拒绝" % wrong)
        assert stray.behavior.scene is None, "没来得及接场景，也没把手交给它"
    assert view.behavior.scene is not None and view.behavior.space is not None


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


def testOnTouchTheOwnFlipAndTakeBuzzAtOnceAndThePlacedAndRefusedResultsBuzzThroughTheScene():
    """触屏的轻震：自己的翻面 / 取下点下去这一刻就震（不等服务端）；服务端回的放上去 / 放不上去，场景交给本人开着的站点（feel）震。"""
    Haptics = dgtest.load("Shared.Haptics")
    view = make(pieces={0: item(BEEF), 2: item(COOKED)}, data=waiting(0))
    view.input = "touch"
    assert click(view, 0) and actions() == [("turn", {"place": 0})]
    assert world.vibrations == [Haptics.BUZZ_MS["flip"]], "翻面"
    assert click(view, 2) and world.vibrations == [Haptics.BUZZ_MS["flip"], Haptics.BUZZ_MS["pick"]], "取下熟的"
    del world.vibrations[:]
    serverEvent("placed")
    serverEvent("refused", stack=item(BEEF))
    serverEvent("grilled", 2)
    assert world.vibrations == [Haptics.BUZZ_MS["put"], Haptics.BUZZ_MS["refuse"]], "放上去、被拒；烤好了不是本人的动作"
    del world.vibrations[:]
    view.input = "mouse"
    serverEvent("placed")
    assert world.vibrations == [], "键鼠：视图不震"
    view.behavior.onClose()
    view.input = "touch"
    serverEvent("placed")
    assert world.vibrations == [], "关了站点：场景不再替这个视图震（旁观的人没有站点视图）"


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
    flew = []
    view.flyIn = lambda at=None: flew.append(at)
    assert [node.key for node in view.behavior.pickables()] == ["mouth"], "拿着东西时整个烤架面是一块"
    assert click(view, 4)
    assert actions()[-1] == ("place", {}), "左键：每个空位一件"
    assert len(flew) == 1, "有空位：触屏点选的那一叠从托盘里它那一格飞过来（前置包的 view.flyIn，键鼠时它什么都不画）"
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


def testShiftClickOnTheTrayAsksTheBehaviorFirstAndAFoodStackGoesOnWithAPlaceFromTheSlot():
    """前置包的 onInventoryShiftClick 钩子（空手 Shift 点托盘里的一叠先问表现）：有营火配方的发 place {from: 背包格号}，返回真（蛋也发，
    JE 是这么写的，服务端再弹回）；没有配方的返回假、什么也不发（内核照旧）。"""
    view = make()
    behavior = view.behavior
    assert behavior.onInventoryShiftClick(7, item(BEEF, 8)) is True
    assert actions()[-1] == ("place", {"from": 7})
    assert behavior.onInventoryShiftClick(3, item("minecraft:egg", 4)) is True and actions()[-1] == ("place", {"from": 3})
    assert behavior.onInventoryShiftClick(5, item("minecraft:stick")) is False and behavior.onInventoryShiftClick(5, None) is False
    assert len(actions()) == 2


def testRightClickingElsewhereWithAStackInHandIsLeftToTheKernelToPutAway():
    view = make(pieces={1: item(BEEF)})
    view.setHand(item(BEEF, 5))
    assert view.pointer("down", (5.0, 5.0), 1, False) is False, "点在烤架以外：不接，内核放回背包"
    assert world.actions()[-1]["click"] == "PUT_AWAY"


# ---------------------------------------------------------------- 开着站点才有的演法

def testSeveralPiecesTheCookLaysFlyInFromTheScreensBottomOneAfterTheOther():
    """从屏幕下沿飞来：站点空间就是炉灶朝向的空间，镜头永远在炉灶的正面（-z），所以炉灶朝哪，起点都在件的 -z 一侧。"""
    for aux in range(4):
        view = make(aux=aux)
        scene = view.behavior.scene
        scene.apply({"dimensionId": 0, "pos": list(STOVE), "slots": [{"item": item(BEEF), "hand": True, "down": 0.0, "up": 0.0}] * 3 + [{}] * 3})
        run(view, DT)
        pieces = scene.pieces
        assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, False, False], "后面的先等着"
        offset = pieces.motion[0].pose()[0]
        assert offset[2] < -5.0, (aux, "从屏幕下沿那边（离相机近的一侧）飞来")
        run(view, 1.0)
        assert [pieces.motion[place].visible for place in (0, 1, 2)] == [True, True, True] and len(drops()) == 3


def _bounce(view):
    """被拒的一件虚影弹开 0.3 秒后离烤架中心多远（世界的 (dx, dz)），和"炉灶的正面方向走 6 像素"（站点 -z 方向）的世界位移。"""
    serverEvent("refused", stack=item(BEEF))
    scene = Scenes.sceneAt(0, STOVE)
    middle = scene.space.toWorld(*scene.space.middle())
    for _ in range(int(round(0.3 / DT))):
        scene.frame(DT, True)
    assert len(drops()) == 1
    here = centerOf(drops()[0])
    return (here[0] - middle[0], here[2] - middle[2])


def testARefusedStackBouncesTowardTheStovesFrontWhicheverWayItFacesAndWhoeverLooks():
    """HoD 的 REFUSED：虚影往 -z（站点的北面，炉灶的正面）弹 6 像素。站点空间就是炉灶朝向的空间，所以谁看都往炉灶的正面弹：
    开着站点的人和旁观的人（没开站点）看到的一样，不再是"自己这边 / 北"两样。"""
    for aux, front in sorted(FRONT.items()):
        for watching in (True, False):
            view = make(aux=aux)
            if not watching:
                view.behavior.onClose()
            moved = _bounce(view)
            assert abs(moved[0] - front[0] * 6.0 / 16.0 * 0.95) < 0.03 and abs(moved[1] - front[1] * 6.0 / 16.0 * 0.95) < 0.03, (aux, watching, moved)
            scene = Scenes.sceneAt(0, STOVE)
            for _ in range(int(round(0.4 / DT))):
                scene.frame(DT, True)
            assert drops() == [], "弹完收掉"


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


# ---------------------------------------------------------------- 触屏长按（onHold）：右键 / Shift 点击的变体，只给和点一下不一样的

HoldMenu = fdtest.load("Compat.Diegesis.HoldMenu")


def testHoldingAStackOverTheGrillOffersPutHereWhereMoreThanOnePlaceIsFree():
    """点一下：每个空位摆一件（先摆第一个空位）；右键：只摆离光标最近的空位那一件——空位不止一个，选哪一格才有区别（东西只有一个也一样）。"""
    view = make(pieces={1: item(BEEF)})
    view.setHand(item(BEEF, 5))
    assert view.holdOf(screenOf(view, 4)) == {"menu": [HoldMenu.PUT_HERE]} and HoldMenu.PUT_HERE == {"label": "只放这一格", "button": 1, "quick": False}
    assert click(view, 4) and actions()[-1] == ("place", {})
    assert click(view, 4, button=1) and actions()[-1] == ("place", {"one": True, "place": 4}), "点一下和右键真的不一样"
    view.setHand(item(BEEF, 1))
    assert view.holdOf(screenOf(view, 4)) == {"menu": [HoldMenu.PUT_HERE]}, "手上只有一个：选哪一格照样有区别"
    assert view.holdOf((5.0, 5.0)) is None, "点在烤架以外：不接，没有变体"
    view = make(pieces=dict((place, item(BEEF)) for place in range(5)))
    view.setHand(item(BEEF, 5))
    assert view.holdOf(screenOf(view, 5)) is None, "只剩一个空位：左键右键放在同一处"


def testEmptyHandOverARawPieceOffersTakeWhereATapWouldTurnIt():
    view = make(pieces={0: item(BEEF)})
    assert view.holdOf(screenOf(view, 0)) == {"menu": [HoldMenu.TAKE_PIECE]} and HoldMenu.TAKE_PIECE == {"label": "取下", "button": 1, "quick": False}
    assert click(view, 0) and actions()[-1] == ("turn", {"place": 0}), "点一下：翻面"
    assert click(view, 0, button=1) and actions()[-1] == ("take", {"place": 0}), "右键：取下"


def testADonePieceOneStillInTheAirOrNoPieceHasNoMenuSoTheTapActsAtOnce():
    view = make(pieces={0: item(COOKED)})
    assert view.holdOf(screenOf(view, 0)) is None, "烤好了：点一下就是取下"
    view = make(pieces={0: item(BEEF)})
    click(view, 0)
    assert view.holdOf(screenOf(view, 0)) is None, "刚翻过、还在空中：点一下什么也不做，不等"
    run(view, 1.0)
    assert view.holdOf(screenOf(view, 0)) == {"menu": [HoldMenu.TAKE_PIECE]}, "落下来了：又是点一下翻面"
    assert view.holdOf((5.0, 5.0)) is None, "别处"
    view.behavior.scene = None
    assert view.holdOf(screenOf(view, 0)) is None


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
