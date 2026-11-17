# -*- coding: utf-8 -*-
# runner: both
"""砧板站点的客户端表现（Compat/Diegesis/BoardView + BoardDraw + BoardCutter + BoardFx，假引擎和假视图见 boardclient.py）：
登记、开站关站、托盘、点板、落刀（吸附 / 敲一声 / 发 chop）、取回、做成、插工具、服务端事件、板上东西的画法。
"""
from __future__ import print_function

import math

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")
Dashes = fdtest.load("Shared.Rules.HandsOn.BoardDashes")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
ItemPose = fdtest.load("Shared.Rules.ItemPose")

KNIFE = "arris:iron_knife"


def _open(board=None, layers=(), data=None, hand=None, aux=None, yaw=0):
    """开站。aux 给了就是板的朝向（方块的 aux，缺省朝北），yaw 是站点转到哪一侧（玩家站的那边）。"""
    behavior, view, api = C.station()
    if aux is not None:
        C.engine.block = ("arris:cutting_board", aux)
    view.yaw = yaw
    view.state.board, view.state.layers = board, list(layers)
    view.data, view.hand = dict(data or {}), hand
    behavior.onOpen()
    return behavior, view


def _across(count=2, name="arris:cabbage"):
    """一件等着切的东西和它的一刀：返回 (板上的东西, 站点数据)。"""
    return C.item(name, count), {"plan": 1, "marks": 0, "style": "across", "spots": [0.5], "angles": [0.0], "stroke": "cut", "dish": ""}


def _cursorOn(behavior, offset):
    """光标放在食物上、离食物中心偏移 (x, z) 的地方：返回射线；并让表现收到一次移动事件。"""
    draw = behavior.draw
    ray = C.rayTo((draw.cx + offset[0], draw.surface(), draw.cz + offset[1]))
    behavior.onPointer(C.Event("move", "surface", ray))
    return ray


def _frames(behavior, count=40, dt=1.0 / 60.0):
    for _ in range(count):
        behavior.frame(dt)


def _lineOf(name="arris:cabbage", count=2):
    """这件东西这一刀的线（离食物中心）。"""
    icon = Marks.iconOf(name)
    return Marks.markOf(Marks.axisOf(icon), "across", [0.5], [0.0], 0, 1), icon


def _live(view, name=None):
    return [prop for prop in view.props.live() if name is None or prop.item["newItemName"] == name]


def testRegistrationGivesTheSchemaTheJavaChromeAndTheJavaCamera():
    behavior, view, api = C.station()
    stationId, blocks, factory, schema, canOpen = api.registered
    assert stationId == "arris:cutting_board" and list(blocks) == ["arris:cutting_board"]
    assert schema.groupNames == ["board", "layers"] and canOpen is None
    assert behavior.chrome == "java" and behavior.flightSeconds == 0.4 and behavior.workPlane == 3.0
    assert behavior.camera["pos"] == (7.5, 35.5, -21.0) and behavior.camera["target"] == (7.5, 1.0, 8.0) and behavior.camera["fov"] == 30.0
    assert behavior.pickables()[0].key == "surface", "空手：点板面"
    view.hand = C.item("arris:cabbage", 3)
    assert behavior.pickables()[0].key == "mouth", "拿着东西：整块板是接东西的口"
    assert behavior.carrySize == 4.5 and behavior.carryLift == 2.5, "光标栈上的东西：Diegesis 的缺省大小"


def testAnOldPrerequisiteGetsNoBoardStation():
    api = C.FakeApi()
    api.API_VERSION = 2                         # 没有输入方式（api.TOUCH）和半透明悬着的东西：砧板要 API 3
    assert C.BoardView.register(api) is None and api.registered is None
    api.API_VERSION = 3
    assert C.BoardView.register(api) is not None and api.registered[0] == "arris:cutting_board"


def testOpeningHidesTheBlockItemsAndClosingShowsThemAgain():
    board, data = _across()
    behavior, view = _open(board, data=data)
    assert (0, C.STATION_POS) in C.BlockItems._hidden, "开站期间 BlockItems 不画这块板"
    assert _live(view, "arris:cabbage"), "开站那一刻板上就有东西：内核要镜头到位才调 frame，飞行的 0.4 秒里不能是空板"
    _frames(behavior, 3)
    assert _live(view, "arris:cabbage"), "本端自己画板上的东西"
    behavior.onClose()
    assert (0, C.STATION_POS) not in C.BlockItems._hidden
    assert behavior.draw is None and behavior.cutter is None
    assert not view.props.live(), "道具都收了"


def testTheTrayShowsWhatTheBoardUsesAndAnswersFromACache():
    behavior, view, api = C.station()
    for name in ("arris:cabbage", "minecraft:bread", KNIFE, "minecraft:iron_axe"):
        assert behavior.usable(C.item(name)), name
    assert not behavior.usable(C.item("minecraft:dirt"))
    C.engine.GetItemBasicInfo = lambda name, aux=0: (_ for _ in ()).throw(AssertionError("缓存了：不该再问"))
    try:
        assert behavior.usable(C.item("arris:cabbage")) and not behavior.usable(C.item("minecraft:dirt"))
    finally:
        del C.engine.GetItemBasicInfo


def testShiftClickOnTheTrayPlacesTheWholeSlotButNeverATool():
    behavior, view = _open()
    C.engine.inventory[4] = C.item("arris:cabbage", 7)
    C.engine.inventory[5] = C.item(KNIFE)
    C.engine.inventory[6] = C.item("minecraft:dirt", 3)
    behavior.onTrayClick(4, 0, True)
    behavior.onTrayClick(5, 0, True)
    behavior.onTrayClick(6, 0, True)
    behavior.onTrayClick(4, 0, False)
    behavior.onTrayClick(-1, 0, True)
    assert view.sent == [("place", {"from": 4})], view.sent


def testTheStackHeldAsTheStationOpensIsPlacedByUseUnlessItIsATool():
    C.station()
    C.engine.inventory[3] = C.item("arris:cabbage", 4)
    C.engine.selected = 3
    behavior, view, api = C.station()
    C.engine.inventory[3], C.engine.selected = C.item("arris:cabbage", 4), 3
    behavior.onOpen()
    assert view.sent == [("place", {"from": 3, "by_use": True})]
    behavior, view, api = C.station()
    C.engine.inventory[3], C.engine.selected = C.item(KNIFE), 3
    behavior.onOpen()
    assert view.sent == [], "刀留在原来的格子里：它是手上这一下要切的刀"
    behavior, view, api = C.station()
    behavior.onOpen()
    assert view.sent == [], "空手"
    behavior, view, api = C.station()
    C.engine.inventory[3], C.engine.selected = C.item("arris:cabbage", 4), 3
    view.openedByUse = False
    behavior.onOpen()
    assert view.sent == [], "从相邻的站点走过来的（BoardBehavior:365 的 openedByUse）：主手上的东西不是给这块板的"


def testTheBoardIsOutlinedWhileWhatIsCarriedCanBeLaidOnIt():
    """手上这叠服务端会收、光标在板上：板描一圈亮边（variable.mod_board_lit）。工具、板不收的、光标不在板上都不描；触屏拿着就描。"""
    behavior, view = _open(hand=C.item("arris:cabbage", 4))
    lit = lambda: C.engine.molang.get("variable.mod_board_lit")       # noqa: E731
    behavior.frame(0.02)
    assert lit() == 0.0, "光标还没到板上"
    behavior.onPointer(C.Event("move", "mouth", C.rayTo((8.0, 1.0, 8.0))))
    behavior.frame(0.02)
    assert lit() == 1.0, "卷心菜放得上空板"
    view.hand = C.item(KNIFE)
    behavior.frame(0.02)
    assert lit() == 0.0, "刀是工具，不是往板上放的"
    view.hand = C.item("arris:cabbage", 4)
    view.state.board = C.item("minecraft:oak_log", 1)
    behavior.frame(0.02)
    assert lit() == 0.0, "板上有别的东西：这叠板不收"
    view.state.board = None
    behavior.onPointer(C.Event("move", None, C.rayTo((40.0, 1.0, 8.0))))
    behavior.frame(0.02)
    assert lit() == 0.0, "光标离开了板"
    view.input = "touch"
    behavior.frame(0.02)
    assert lit() == 1.0, "触屏没有悬停：手上拿着放得上的东西就描"
    behavior.onClose()
    assert lit() == 0.0, "关站收掉"


def testAFlowerAndAWildCropLieFlatOnTheBoardThoughTheEngineCallsThemBlocks():
    """JE（HoD 的 ItemVoxels.icon、FD 的 isGui3d）：模型是一张贴图的方块类物品像食物一样平躺；引擎的 itemType 对它们也是 block，按名字认（Data/FlatBlockItems）。
    原木这样的真方块照旧立着；蘑菇丛的掉落物是方块模型缩小的立体小蘑菇（3.10 实机），不是一张贴图，也立着。"""
    for name in ("minecraft:poppy", "arris:wild_cabbages"):
        assert C.engine.GetItemBasicInfo(name)["itemType"] == "block"
        behavior, view = _open(C.item(name, 1))
        _frames(behavior, 2)
        assert behavior.draw.kindOf(C.item(name)) == "flat" and not behavior.draw.isBlock(C.item(name)), name
        props = _live(view, name)
        assert len(props) == 1 and props[0].flat and abs(props[0].scale - 1.25) < 1e-6, "和食物一样：10 像素的图标平躺，缩放 1.25（%s）" % name
        behavior, view = _open(C.item(name, 5))
        _frames(behavior, 2)
        assert len(_live(view, name)) == 2 and all(prop.flat for prop in _live(view, name)), "一叠：底下再垫一张（%s）" % name
    behavior, view = _open(C.item("minecraft:oak_log", 1))
    _frames(behavior, 2)
    assert behavior.draw.kindOf(C.item("minecraft:oak_log")) == "block" and not _live(view, "minecraft:oak_log")[0].flat, "原木是真的方块：立着"
    behavior, view = _open(C.item("arris:red_mushroom_colony", 1))
    _frames(behavior, 2)
    assert behavior.draw.kindOf(C.item("arris:red_mushroom_colony")) == "block" and not _live(view, "arris:red_mushroom_colony")[0].flat, "蘑菇丛：立着"


def testAFlatFlowerSitsOnTheBoardLikeFoodAndDoesNotFloatAboveIt():
    """实机（3.10）：花、野生作物的掉落物引擎照方块物品的规矩整体抬高 0.2 格（3.2 像素）、轴心在离贴图底边 5/16 处；照贴图物品的规矩摆会浮在板上
    （用户报的"浮空了"）。交给前置包的中心先反着挪：按引擎的画法算回去，画出来的中心和同样摆着的食物是同一个点。食物自己不挪。"""
    Pose = ItemPose
    for count in (1, 5):
        behavior, view = _open(C.item("arris:cabbage", count))
        _frames(behavior, 2)
        foods = sorted(_live(view, "arris:cabbage"), key=lambda prop: prop.center[1])
        behavior, view = _open(C.item("minecraft:poppy", count))
        _frames(behavior, 2)
        flowers = sorted(_live(view, "minecraft:poppy"), key=lambda prop: prop.center[1])
        assert len(flowers) == len(foods)
        for flower, food in zip(flowers, foods):
            assert abs(food.center[1] - flower.center[1] - Pose.BLOCK_LIFT) < 1e-6, "平躺：交出去的中心比食物低 3.2 像素"
            up = [row[1] for row in flower.matrix]                       # 贴图自己的上方向（站点空间）
            reach = (Pose.ITEM_SPAN / 2.0 - Pose.RAISED_PIVOT) * flower.scale
            pivot = [c - u * Pose.ITEM_SPAN / 2.0 * flower.scale for c, u in zip(flower.center, up)]      # 前置包照贴图物品的规矩算的轴心
            drawn = (pivot[0] + up[0] * reach, pivot[1] + Pose.BLOCK_LIFT + up[1] * reach, pivot[2] + up[2] * reach)   # 引擎画出来的中心
            assert all(abs(a - b) < 1e-6 for a, b in zip(drawn, food.center)), (count, drawn, food.center)


def testTheKnifeLinesOnAFlowerFollowItsOutlineNotTheSquareOfABlock():
    """平躺的花刀口线按它图标的轮廓走（掩码）：几何里有图标、不是方块；原木才是方形刀口。"""
    board, data = _across(2, "minecraft:poppy")
    behavior, view = _open(board, data=data, hand=C.item(KNIFE))
    _frames(behavior, 2)
    icon, isBlock, axis, marks = behavior.cutter._geometry()
    assert icon is not None and icon is Marks.iconOf("minecraft:poppy") and not isBlock and marks == 1
    assert axis.elongation > 1.0 and axis.elongation != Marks.axisOf(None, True).elongation, "有轮廓的轴，不是方块的正方形"
    board, data = _across(2, "minecraft:oak_log")
    behavior, view = _open(board, data=data, hand=C.item("minecraft:iron_axe"))
    _frames(behavior, 2)
    icon, isBlock, axis, marks = behavior.cutter._geometry()
    assert icon is None and isBlock, "原木：方块，方形刀口"


def testALoneItemIsDrawnFlatAndAPileGetsASecondOneUnderIt():
    behavior, view = _open(C.item("arris:cabbage", 1))
    _frames(behavior, 2)
    props = _live(view, "arris:cabbage")
    assert len(props) == 1 and props[0].flat and abs(props[0].scale - 1.25) < 1e-6, "10 像素的图标：缩放 1.25"
    assert abs(props[0].center[0] - behavior.draw.cx) < 1e-6 and abs(props[0].center[2] - behavior.draw.cz) < 1e-6
    behavior, view = _open(C.item("arris:cabbage", 5))
    _frames(behavior, 2)
    pile = _live(view, "arris:cabbage")
    assert len(pile) == 2 and sorted(prop.center[1] for prop in pile)[1] - sorted(prop.center[1] for prop in pile)[0] > 0.5, "一叠：上面一张抬高 0.65"


def testTheBoardsCenterFollowsTheBlocksFacing():
    behavior, view, api = C.station()
    spots = {}
    for aux in (0, 1, 2, 3):
        C.engine.block = ("arris:cutting_board", aux)
        spots[aux] = behavior.center()
    assert len(set(spots.values())) == 4, spots
    for x, z in spots.values():
        assert abs(math.hypot(x - 8.0, z - 8.0) - 1.5) < 1e-6, "离方块中心 1.5 像素（底座中间，不是柄那边）"
    C.engine.block = ("arris:cutting_board", 2)
    assert all(abs(a - b) < 1e-6 for a, b in zip(behavior.center(), (6.5, 8.0))), "朝北：(6.5, 8)"


def testTheBlockItemsOffsetPutsTheFoodWhereTheStationDrawsIt():
    """没开站时 Client/BlockItems 画的板上东西，和开站后本端画的在同一个点（开站、关站不跳）。"""
    behavior, view, api = C.station()
    for aux in (0, 1, 2, 3):
        C.engine.block = ("arris:cutting_board", aux)
        cx, cz = behavior.center()
        world = view.toWorld(cx, 0.0, cz)
        offset = C.BlockItems._boardOffset(C.STATION_POS)
        assert abs(world[0] - (C.STATION_POS[0] + 0.5 + offset[0])) < 1e-6, aux
        assert abs(world[2] - (C.STATION_POS[2] + 0.5 + offset[1])) < 1e-6, aux


def _stationPlaces(view):
    """站点里画着的道具，换成方块里的格（离方块西北下角），按高度排。"""
    places = []
    for prop in view.props.live():
        world = view.toWorld(*prop.center)
        places.append((round(world[1] - C.STATION_POS[1], 4), round(world[0] - C.STATION_POS[0], 4), round(world[2] - C.STATION_POS[2], 4), round(prop.scale, 4)))
    return sorted(places)


def _blockPlaces(items):
    placed = C.BlockItems._layoutOf(C.BlockItems.BlockDisplay.KIND_BOARD, items, C.STATION_POS)
    return sorted((round(p.center[1], 4), round(p.center[0], 4), round(p.center[2], 4), round(p.scale, 4)) for p in placed)


def testTheStationAndTheBlockItemsPutEverythingAtTheSamePlaceAndSize():
    """开站、关站板上的东西不跳：食物、一叠、方块、插着的工具、摆盘的层，站点里画的和 Client/BlockItems 画的是同一个位置同一个大小。"""
    cases = [({"0": C.item("arris:cabbage", 1)}, C.item("arris:cabbage", 1), []),
             ({"0": C.item("arris:cabbage", 5)}, C.item("arris:cabbage", 5), []),
             ({"0": C.item("minecraft:oak_log", 2)}, C.item("minecraft:oak_log", 2), []),
             ({"0": C.item("minecraft:poppy", 1)}, C.item("minecraft:poppy", 1), []),
             ({"0": C.item("arris:wild_cabbages", 5)}, C.item("arris:wild_cabbages", 5), []),
             ({"0": C.item("arris:iron_knife")}, C.item("arris:iron_knife"), []),
             ({"L0": C.item("minecraft:bread", 2), "L1": C.item("arris:beef_patty", 2), "L2": C.item("arris:tomato", 2)}, None,
              [C.item("minecraft:bread", 2), C.item("arris:beef_patty", 2), C.item("arris:tomato", 2)])]
    for items, board, layers in cases:
        behavior, view = _open(board, layers=layers)
        _frames(behavior, 3)
        station, outside = _stationPlaces(view), _blockPlaces(items)
        assert len(station) == len(outside) and station, (items, station, outside)
        for here, there in zip(station, outside):
            assert all(abs(a - b) < 0.004 for a, b in zip(here, there)), (items, here, there)


STUCK = ("arris:iron_knife", "minecraft:iron_pickaxe", "minecraft:iron_hoe", "minecraft:iron_axe", "minecraft:iron_shovel", "minecraft:shears", "minecraft:trident")


def _worldDirection(view, prop):
    """站点里一个立着的道具的贴图正面朝哪，换成世界方向（ItemProp 就是这样换的）。"""
    x, y, z = prop.center
    a, b = view.toWorld(x, y, z), view.toWorld(x + prop.facing[0], y, z + prop.facing[1])
    length = math.hypot(b[0] - a[0], b[2] - a[2])
    return ((b[0] - a[0]) / length, (b[2] - a[2]) / length)


def testAStuckToolIsDrawnInTheMiddleOfTheBlockTurnedWithTheBoardAndLooksTheSameWhetherTheStationIsOpenOrNot():
    """插着的工具（FD 的 renderItemCarved）：方块正中心、贴图平行于板的正面、按类型转（镐 / 锄 225、三叉戟 135、别的 180）；站点里（BoardDraw）和没开站时
    世界里摆的（Client/BlockItems）是同一个位置、朝向、角度、大小，板朝哪、玩家站在哪一侧都一样，开站关站不跳。"""
    C.TYPES["minecraft:iron_hoe"], C.TYPES["minecraft:trident"] = "hoe", "trident"
    try:
        for aux in (0, 1, 2, 3):
            for yaw in (0, 90, 180, 270):
                for name in STUCK:
                    behavior, view = _open(C.item(name), aux=aux, yaw=yaw)
                    _frames(behavior, 3)
                    props = _live(view, name)
                    outside, = C.BlockItems._layoutOf("board", {"0": C.item(name)}, C.STATION_POS)
                    assert len(props) == 1 and not props[0].flat and not outside.flat, (aux, yaw, name)
                    here = view.toWorld(*props[0].center)
                    assert all(abs(a - b) < 0.004 for a, b in zip((here[0] - C.STATION_POS[0], here[1] - C.STATION_POS[1], here[2] - C.STATION_POS[2]), outside.center)), (aux, yaw, name)
                    assert abs(props[0].scale - outside.scale) < 1e-9 and props[0].roll == outside.roll, (aux, yaw, name)
                    front = _worldDirection(view, props[0])
                    assert abs(front[0] - outside.direction[0]) < 1e-6 and abs(front[1] - outside.direction[1]) < 1e-6, (aux, yaw, name, front, outside.direction)
                    behavior.onClose()
    finally:
        C.TYPES.pop("minecraft:iron_hoe"), C.TYPES.pop("minecraft:trident")


def testAStuckToolSitsWhereFarmersDelightPutsItAndIsTurnedByItsKind():
    """CuttingBoardRenderer.renderItemCarved：translate(0.5, 0.23, 0.5)——方块中心，不是板底座的中间；贴图正面朝板 FACING 的反方向；类型决定在贴图平面里转多少度。"""
    C.TYPES["minecraft:iron_hoe"], C.TYPES["minecraft:trident"] = "hoe", "trident"
    try:
        for name, turn in ((KNIFE, 180.0), ("minecraft:iron_axe", 180.0), ("minecraft:iron_pickaxe", 225.0), ("minecraft:iron_hoe", 225.0),
                           ("minecraft:shears", 180.0), ("minecraft:trident", 135.0)):
            behavior, view = _open(C.item(name), aux=2)
            _frames(behavior, 3)
            prop, = _live(view, name)
            world = view.toWorld(*prop.center)
            assert abs(world[0] - (C.STATION_POS[0] + 0.5)) < 1e-6 and abs(world[2] - (C.STATION_POS[2] + 0.5)) < 1e-6 and abs(world[1] - (C.STATION_POS[1] + 0.23)) < 0.004, name
            assert prop.roll == turn and abs(prop.scale - 1.2) < 1e-6, name
            assert abs(_worldDirection(view, prop)[0]) < 1e-6 and abs(_worldDirection(view, prop)[1] - 1.0) < 1e-6, "朝北的板（FACING 朝北）：贴图的正面朝南"
            behavior.onClose()
    finally:
        C.TYPES.pop("minecraft:iron_hoe"), C.TYPES.pop("minecraft:trident")


def testShearsAndATridentOnTheBoardAreDrawnAsStuckToolsNotLyingFlat():
    """原来站点里只有五种类型当插着的工具画：剪刀平躺在板上、三叉戟插不进去。现在两样都是插着的工具（JE 的 canStick）。"""
    C.TYPES["minecraft:trident"] = "trident"
    try:
        behavior, view = _open(C.item("minecraft:shears"))
        assert behavior.draw.kindOf(C.item("minecraft:shears")) == "tool" and behavior.draw.kindOf(C.item("minecraft:trident")) == "tool"
        assert behavior.env.isCarving(C.item("minecraft:shears")) and behavior.env.canStick(C.item("minecraft:trident"))
        _frames(behavior, 3)
        assert not _live(view, "minecraft:shears")[0].flat
        behavior.onClose()
        behavior, view = _open(hand=C.item("minecraft:trident"))
        assert behavior.onPointer(C.Event("down", "mouth", button=0, quick=True)) and view.sent == [("carve", {})], "Shift 点空板：三叉戟插得进"
    finally:
        C.TYPES.pop("minecraft:trident")


def testAStuckToolPulledOutRisesFromTheSamePlaceWithTheSamePose():
    """拔出来的虚影（HoD 的 pulledOut）画在插着时的位置、同一个朝向和角度，往上升着缩没。"""
    for name, turn in ((KNIFE, 180.0), ("minecraft:iron_pickaxe", 225.0)):
        behavior, view = _open(C.item(name), aux=1)
        _frames(behavior, 3)
        resting, = _live(view, name)
        pose = (resting.center, resting.facing, resting.roll)
        view.state.board = None
        behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
        behavior.onEffect("taken", {"stack": C.item(name), "at": -1, "carved": True})
        behavior.frame(0.0)                                      # 道具在每帧里建
        ghost, = _live(view, name)
        assert ghost.facing == pose[1] and ghost.roll == pose[2] == turn and all(abs(a - b) < 1e-6 for a, b in zip(ghost.center, pose[0])), name
        _frames(behavior, 6)
        assert _live(view, name)[0].center[1] > pose[0][1] + 1.0, "往上拔"
        _frames(behavior, 40)
        assert not _live(view, name)
        behavior.onClose()


def testLayersAreStackedEachWithItsOwnTurnAndTheFirstIsTheBigOne():
    layers = [C.item("minecraft:bread", 2), C.item("arris:beef_patty", 2), C.item("arris:tomato", 2)]
    behavior, view = _open(layers=layers)
    _frames(behavior, 3)
    props = view.props.live()
    assert len(props) == 3
    heights = [prop.center[1] for prop in props]
    assert heights == sorted(heights) and heights[1] - heights[0] > 0.5
    assert abs(props[0].scale - 1.25) < 1e-6 and abs(props[1].scale - 9.0 / 8.0) < 1e-6, "第 0 层 10 像素，以后的 9 像素"
    for index, prop in enumerate(props):
        want = ItemPose.lyingMatrix(-Scene.layerPose(index)["turn"])          # 平躺的东西按姿态矩阵摆：每层转自己的角度（和没开站时 BlockDisplay 的 along = (cos, sin) 一个朝向）
        assert all(abs(a - b) < 1.0e-9 for row, wrow in zip(prop.matrix, want) for a, b in zip(row, wrow)), index
    assert len(set(round(prop.matrix[0][1], 3) for prop in props)) == 3, "每层转的角度不同"


def testLeftClickWithAStackPlacesAllAndRightClickPlacesOne():
    behavior, view = _open(hand=C.item("arris:cabbage", 5))
    assert behavior.onPointer(C.Event("down", "mouth", button=0))
    assert behavior.onPointer(C.Event("down", "mouth", button=1))
    assert view.sent == [("place", {"one": False}), ("place", {"one": True})]
    assert not behavior.onPointer(C.Event("down", "surface")), "手上拿着东西：板面不是接东西的口"
    assert not behavior.onPointer(C.Event("down", None, button=1)), "点在板外：内核把手上的放回背包"


def testAKnifeOnTheCursorOnlyCutsWhenItIsOnTheDashedLine():
    board, data = _across()
    behavior, view = _open(board, data=data, hand=C.item(KNIFE))
    cut, icon = _lineOf()
    ray = _cursorOn(behavior, (cut.x, cut.z))
    _frames(behavior)
    assert behavior.cutter.knife.overMark == 0, "光标就在线上：吸附"
    assert behavior.onPointer(C.Event("down", "mouth", ray, button=0))
    assert view.sent[0][0] == "chop" and view.sent[0][1]["mark"] == 0 and view.sent[0][1]["yaw"] == 0
    assert 0.0 <= view.sent[0][1]["at"] <= 16.0 and 0.0 <= view.sent[0][1]["at_x"] <= 16.0
    assert behavior.cutter.pending.count == 1, "等服务端回话"
    _frames(behavior, 20)
    view.sent[:] = []
    off = _cursorOn(behavior, (cut.x + 3.5 * -cut.normalX(), cut.z + 3.5 * -cut.normalZ()))
    _frames(behavior)
    behavior.cutter.pending.reset()
    _frames(behavior, 30)
    assert behavior.cutter.knife.overMark == -1
    assert behavior.onPointer(C.Event("down", "mouth", off, button=0)) and view.sent == [], "没吸附上：只敲一声，什么也不发"
    assert C.engine.played and C.engine.played[-1][0] == "hit.wood"


def testTheKnockOfATapThatFoundNothingToCutBuzzesAsARefusedAction():
    board, data = _across()
    behavior, view = _open(board, data=dict(data, marks=1), hand=C.item(KNIFE))        # 一刀已经切完：没有下一刀
    view.input = "touch"
    draw = behavior.draw
    ray = C.rayTo((draw.cx, draw.surface(), draw.cz))
    assert behavior.onPointer(C.Event("down", "mouth", ray, button=0)) and view.sent == []
    assert view.buzzes == ["refuse"], "刀点在食物上、没有下一刀：敲一声，也轻震一下（被拒）"
    behavior, view = _open(C.item("minecraft:cobblestone", 2), data=dict(_across()[1], stroke="chop"), hand=C.item("arris:iron_knife"))
    ray = C.rayTo((behavior.draw.cx, behavior.draw.surface(), behavior.draw.cz))
    assert behavior.onPointer(C.Event("down", "mouth", ray, button=0)) and view.buzzes == ["refuse"], "刀切不了的东西：敲一声也震"


def testTheKnifeOnTheCursorIsDrawnOverTheFoodAndTheKernelsCopyOnTheCursorIsHiddenMeanwhile():
    board, data = _across()
    behavior, view = _open(board, data=data, hand=C.item(KNIFE))
    _frames(behavior, 5)
    assert behavior.carrySize == 4.5 and not _live(view, KNIFE), "光标还没到食物上：和任何一叠一样画在光标上"
    cut, icon = _lineOf()
    _cursorOn(behavior, (cut.x, cut.z))
    _frames(behavior, 5)
    knife = _live(view, KNIFE)
    assert len(knife) == 1 and not knife[0].flat and knife[0].roll == 135.0, "光标栈上的刀也由板画：立着、刀尖朝下"
    assert behavior.carrySize < 0.1, "板画着刀：内核画在光标上的那份缩成一个点（setCarriedHidden）"
    _cursorOn(behavior, (14.0, 14.0))
    _frames(behavior, 5)
    assert behavior.carrySize == 4.5 and not _live(view, KNIFE), "光标移出食物：刀收起来，光标上的那份回来"
    behavior.onClose()
    assert behavior.carrySize == 4.5


def testAStackInHandIsNeverHiddenButABouncingOneIsUntilItIsBack():
    board, data = _across()
    behavior, view = _open(board, data=data, hand=C.item("arris:cabbage", 3))
    _cursorOn(behavior, (0.0, 0.0))
    _frames(behavior, 5)
    assert behavior.carrySize == 4.5, "不是工具：光标栈上的就是它自己"
    behavior.onEffect("refused", {"stack": C.item("arris:cabbage", 3)})
    _frames(behavior, 2)
    assert behavior.carrySize < 0.1, "板不收：弹回手上的这一下，光标栈上的先收起来"
    _frames(behavior, 30)
    assert behavior.carrySize == 4.5


def testAToolInHandIsDrawnOverTheFoodToo():
    board, data = _across()
    data = dict(data, stroke="chop")
    behavior, view = _open(C.item("minecraft:oak_log", 3), data=data, hand=C.item("minecraft:iron_axe"))
    _cursorOn(behavior, (0.0, 0.0))
    _frames(behavior, 5)
    assert _live(view, "minecraft:iron_axe") and behavior.carrySize < 0.1
    _cursorOn(behavior, (14.0, 14.0))
    _frames(behavior, 5)
    assert not _live(view, "minecraft:iron_axe") and behavior.carrySize == 4.5


def testWithAnEmptyHandTheKnifeInTheBagIsOfferedAndLeftClickCutsRightClickTakesBack():
    board, data = _across()
    behavior, view = _open(board, data=data)
    C.engine.inventory[8] = C.item(KNIFE)
    cut, icon = _lineOf()
    ray = _cursorOn(behavior, (cut.x, cut.z))
    _frames(behavior)
    tools = C.engine.liveParticles("arris:board_tool")
    assert len(tools) == 1 and not _live(view, KNIFE), "借来的刀是半透明的粒子（BoardStand），不是掉落物"
    assert tools[0]["vars"]["variable.turn"] == -135.0, "立着、刀尖朝下：图标在平面里顺时针转 135 度（掉落物的 roll 135，粒子的 rotation 逆时针为正）"
    assert behavior.onPointer(C.Event("down", "surface", ray, button=0)) and view.sent[0][0] == "chop"
    view.sent[:] = []
    assert behavior.onPointer(C.Event("down", "surface", ray, button=1)) and view.sent == [("take", {})]
    C.engine.inventory[8] = None
    view.sent[:] = []
    _frames(behavior, 10)
    assert behavior.onPointer(C.Event("down", "surface", ray, button=0)) and view.sent == [("take", {})], "没有刀的左键：取回"
    assert not C.engine.liveParticles("arris:board_tool"), "没有刀了：刀也收起来"


def testTheDashedLineIsOnlyTheNextCutAndOnlyShownWhileThereIsAToolToCutWith():
    board, data = _across()
    behavior, view = _open(board, data=data)
    _frames(behavior, 30)
    assert not C.engine.liveParticles("arris:board_mark"), "没有工具：不显示线"
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 30)
    cut, icon = _lineOf()
    ends = Marks.dashOf(cut, icon)
    length = math.hypot(ends[1][0] - ends[0][0], ends[1][1] - ends[0][1])
    dashes = C.engine.liveParticles("arris:board_mark")
    assert len(dashes) == len(Dashes.dashes(length)) > 1, "有刀：下一刀的线（一次一条，长度照图标的实心像素，每段一颗粒子）"
    assert not [prop for prop in view.props.live() if prop.line], "粒子建得出来：不用掉落物的虚线"
    view.data = dict(data, marks=1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: False})())
    _frames(behavior, 30)
    assert not C.engine.liveParticles("arris:board_mark"), "只有一刀：切完了就没有线"


def testOnlyAKnifeThatCutsWhatIsOnTheBoardIsOffered():
    board, data = _across()
    behavior, view = _open(board, data=data)
    C.engine.inventory[3] = C.item("minecraft:iron_axe")
    _frames(behavior, 30)
    assert not _live(view, "minecraft:iron_axe") and not C.engine.liveParticles(), "斧头切不了卷心菜：没有借来的工具，也没有虚线"
    assert behavior.toolOf() == (None, False)
    C.engine.inventory[3] = None
    C.engine.offhand = C.item(KNIFE)
    assert behavior.toolOf()[1] is True and behavior.toolOf()[0]["newItemName"] == KNIFE, "副手的刀也行"
    view.hand = C.item("arris:cabbage")
    assert behavior.toolOf() == (None, False), "手上拿着别的东西：不借背包里的刀"


def testAReadyDishIsFinishedWithLeftAndTheTopLayerTakenWithRight():
    layers = [C.item("minecraft:bread", 2), C.item("arris:beef_patty", 2)]
    behavior, view = _open(layers=layers, data={"dish": "arris:hamburger"})
    assert behavior.onPointer(C.Event("down", "surface", button=0)) and view.sent == [("assemble", {})]
    view.sent[:] = []
    assert behavior.onPointer(C.Event("down", "surface", button=1)) and view.sent == [("take", {})]
    view.data = {"dish": ""}
    view.sent[:] = []
    assert behavior.onPointer(C.Event("down", "surface", button=0)) and view.sent == [("take", {})], "还凑不成：拿最上一层"
    view.hand = C.item(KNIFE)
    view.data = {"dish": "arris:hamburger"}
    view.sent[:] = []
    assert behavior.onPointer(C.Event("down", "mouth", button=0)) and view.sent == [("assemble", {})], "刀落在凑成菜的层上：做成"


def testShiftWithAToolOnABareBoardSticksItInAndACarvedOneComesOutWithAClick():
    behavior, view = _open(hand=C.item(KNIFE))
    assert behavior.onPointer(C.Event("down", "mouth", button=0, quick=True)) and view.sent == [("carve", {})]
    behavior, view = _open(C.item(KNIFE))
    _frames(behavior, 3)
    assert _live(view, KNIFE) and not _live(view, KNIFE)[0].flat, "插着的刀立着"
    assert behavior.onPointer(C.Event("down", "surface", button=0)) and view.sent == [("take", {})], "插着的刀：任一键拔出来"
    view.sent[:] = []
    assert behavior.onPointer(C.Event("down", "surface", button=1)) and view.sent == [("take", {})]


def testAToolOfAnotherKindOnlyKnocksWhenItHasNothingToCut():
    behavior, view = _open(hand=C.item("minecraft:iron_axe"))
    assert behavior.onPointer(C.Event("down", "mouth", button=0)) and view.sent == [], "板上没有东西：敲一声"
    assert C.engine.played[-1][0] == "hit.wood"
    assert not behavior.onPointer(C.Event("down", "mouth", button=1)), "右键：放回背包（内核做）"


def testTheServersChopEffectFliesDustInTheFoodsColourAndTheLastOneSendsTheFoodAway():
    board, data = _across()
    behavior, view = _open(board, data=data)
    behavior.onEffect("chopped", {"at": 8.0, "at_x": 6.5, "spot": 0.5, "angle": 0.0, "tool": KNIFE, "item": "arris:cabbage", "yaw": 0})
    assert len(C.engine.particles) == 1 and C.engine.particles[0]["id"] == "arris:board_dust"
    puff = C.engine.particles[0]
    assert puff["vars"]["variable.count"] == 4 and puff["vars"]["variable.tint_set"] == 1.0, "刀：4 颗，染食物的颜色"
    assert abs(puff["vars"]["variable.vy"] - 0.25) < 1e-9 and puff["vars"]["variable.vx"] == 0.0 and abs(puff["vars"]["variable.spread"] - 0.075) < 1e-9,         "初速 (0, 4, 0) 像素每秒、散布 1.2 像素，换成格"
    station = view.toStation(*puff["pos"])
    assert abs(station[0] - 6.5) < 1e-6 and abs(station[1] - 1.625) < 1e-6 and abs(station[2] - 8.0) < 1e-6, "碎屑落在刀刃的位置、食物顶面（平躺的图标：板面 + 0.625）"
    view.state.board = None
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("chopped", {"at": 8.0, "tool": KNIFE, "item": "arris:cabbage", "yaw": 0, "count": 2, "done": True})
    _frames(behavior, 5)
    gone = _live(view, "arris:cabbage")
    assert len(gone) == 1, "切开的食物往上飘"
    _frames(behavior, 20)
    assert not _live(view, "arris:cabbage"), "缩没"


def testTheServersEffectsBuzzOnTouchLikeTheyMakeTheirSoundsAndAnOldKernelWithoutBuzzSkipsThem():
    """落一刀、被拒、取走、放下、插工具：声音在哪放，触屏的轻震就在哪（view.buzz 只在触屏、sounds 没关时真的震，内核管）；做成一道菜不震。"""
    board, data = _across()
    behavior, view = _open(board, data=data)
    behavior.onEffect("chopped", {"at": 8.0, "at_x": 6.5, "spot": 0.5, "angle": 0.0, "tool": KNIFE, "item": "arris:cabbage", "yaw": 0})
    behavior.onEffect("refused", {})
    behavior.onEffect("taken", {"stack": C.item("arris:cabbage", 1), "at": -1, "carved": False})
    behavior.onEffect("placed", {"at": 0, "item": "arris:cabbage"})
    behavior.onEffect("carved", {})
    behavior.onEffect("assembled", {"layers": [], "finish": None})
    assert view.buzzes == ["cut", "refuse", "pick", "put", "put"], view.buzzes
    behavior, view = _open(board, data=data)
    view.buzz = None                                              # 老版本的前置包：没有 buzz
    behavior.onEffect("refused", {})


def testADustPositionFromAnotherSideIsTurnedToMine():
    board, data = _across()
    behavior, view = _open(board, data=data)
    behavior.onEffect("chopped", {"at": 12.0, "at_x": 8.0, "tool": KNIFE, "item": "arris:cabbage", "yaw": 180})
    sx, sy, sz = view.toStation(*C.engine.particles[0]["pos"])
    assert abs(sx - 8.0) < 1e-6 and abs(sz - 4.0) < 1e-6, "对面的人在 z = 12 落刀：从我这边看在 z = 4"
    C.engine.particles[:] = []
    behavior.onEffect("chopped", {"at": 12.0, "at_x": 8.0, "tool": "minecraft:iron_axe", "item": "minecraft:oak_log", "yaw": 180, "stroke": "strip",
                                  "block": True, "yields": ["minecraft:stripped_oak_log"]})
    vars = C.engine.particles[0]["vars"]
    assert abs(vars["variable.vz"] - 3.0 / 16.0) < 1e-9 and abs(vars["variable.vy"] - 1.0 / 16.0) < 1e-9 and abs(vars["variable.vx"]) < 1e-9,         "削皮的碎屑往他身前（站点里 -z）飘：对面的人在南边，世界里就是往南"


def testARefusedStackBouncesAndAnUnansweredChopIsTakenBack():
    board, data = _across()
    behavior, view = _open(board, data=data, hand=C.item(KNIFE))
    cut, icon = _lineOf()
    ray = _cursorOn(behavior, (cut.x, cut.z))
    _frames(behavior)
    behavior.onPointer(C.Event("down", "mouth", ray, button=0))
    assert behavior.cutter.pending.count == 1
    behavior.onEffect("refused", {"stack": C.item("arris:tomato")})
    assert behavior.cutter.pending.count == 0, "服务端不收：撤回"
    _frames(behavior, 2)
    ghost = _live(view, "arris:tomato")
    assert len(ghost) == 1, "弹回的东西落在板上又弹回手上"
    _frames(behavior, 40)
    assert not _live(view, "arris:tomato")
    assert C.engine.played[-1][0] == "hit.wood"


def testWhatIsTakenLiftsAwayAndALayerComesOutOfThePile():
    layers = [C.item("minecraft:bread", 2), C.item("arris:tomato", 2)]
    behavior, view = _open(layers=layers)
    _frames(behavior, 3)
    view.state.layers = layers[:1]
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: False})())
    behavior.onEffect("taken", {"stack": C.item("arris:tomato", 2), "at": 1, "carved": False})
    _frames(behavior, 3)
    assert len(_live(view, "arris:tomato")) == 1 and len(_live(view, "minecraft:bread")) == 1, "拿走的那层是替身在抬，下面的还在"
    _frames(behavior, 40)
    assert not _live(view, "arris:tomato") and len(_live(view, "minecraft:bread")) == 1


def testAssemblingMeltsTheLayersAndPopsTheDishUp():
    layers = [C.item("minecraft:bread", 1), C.item("arris:egg", 1)]
    behavior, view = _open(layers=layers)
    _frames(behavior, 3)
    view.state.layers = []
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("assembled", {"layers": [C.item("minecraft:bread"), C.item("arris:egg")], "finish": "press", "block": False})
    _frames(behavior, 5)
    assert len(_live(view, "minecraft:bread")) == 1 and len(_live(view, "arris:egg_sandwich")) == 1, "层往里沉，菜同一刻弹出来（JE 的 pop）"
    assert view.dust and view.dust[-1][0] == "arris_diegesis:glint"
    _frames(behavior, 40)
    assert not _live(view, "minecraft:bread") and len(_live(view, "arris:egg_sandwich")) == 1, "层沉完收起来，只剩菜"


def testAStackLetGoLandsFromAboveTheCursor():
    behavior, view = _open()
    _frames(behavior, 2)
    view.state.board = C.item("arris:cabbage", 3)
    ray = C.rayTo((behavior.draw.cx + 4.0, 6.0, behavior.draw.cz - 3.0))
    behavior.onPointer(C.Event("move", None, ray))
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.frame(0.001)
    prop = _live(view, "arris:cabbage")[0]
    assert prop.center[1] > 4.0, "从光标上方落下"
    _frames(behavior, 40)
    assert abs(_live(view, "arris:cabbage")[-1].center[0] - behavior.draw.cx) < 0.05 and not behavior.draw.item.mover.moving


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
