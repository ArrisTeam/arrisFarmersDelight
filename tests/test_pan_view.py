# -*- coding: utf-8 -*-
# runner: both
"""煎锅站点里本人的那一层（Compat/Diegesis/PanView.py，假引擎、真的前置包几何和拾取）：机位在锅柄那一侧（随方块朝向，不随站的位置）、
碰撞盒、抓锅柄往上猛提 = 颠（力度随速度）、点一下锅柄轻轻颠、点食物颠 / 右键取、拿着东西点锅放进去（左键整叠、右键一个）、
托盘只亮煎得了的、食谱书挂上、关站收拾干净。"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgstation
import panclient as C

world = C.install()
dgstation.install()
Pointer = dgstation.load("Client.View")
Pick = C.dgtest.load("Shared.Pick")
Scenes = C.load("Compat.Diegesis.PanScenes")
PanView = C.load("Compat.Diegesis.PanView")
BookSources = C.load("Compat.Diegesis.BookSources")
Math = C.load("Shared.Rules.PanModelMath")
Rules = C.load("Shared.Rules.PanStation")
POS = C.POS
DT = 1.0 / 60.0


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def item(name="minecraft:beef", count=2):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def make(aux=0, yaw=0, hand=None, food="minecraft:beef", count=2, down=0.0, up=0.0):
    """开一次站：方块朝 aux、站点空间按 yaw 转；锅里放 food × count。返回 (表现, 视图)。"""
    world.reset()
    world.blocks[POS] = ("arris:skillet", aux)
    Scenes._scenes.clear()
    Scenes.enable()
    api = C.makeApi()
    cls = PanView.register(api)
    view = C.FakeView(POS, yaw, hand)
    behavior = cls(view)
    behavior.onOpen()
    if food:
        behavior.scene.apply({"dimensionId": 0, "pos": list(POS), "item": item(food, count), "batch": count, "byHand": True, "heated": True,
                              "down": down, "up": up, "rate": 0.0, "both": False})
    return behavior, view


def event(behavior, kind, target, button=0, quick=False, pressed=True):
    """光标射线从相机穿过场景里的 target 点（站点射线），按 View.pointer 的做法拾取后交给表现。"""
    cam = behavior.camera["pos"]
    ray = C.ray(cam, behavior._toStation(target)) if target is not None else None
    hit = Pick.pick(behavior.pickables(), ray) if ray is not None else None
    return behavior.onPointer(Pointer.PointerEvent(kind, (0.0, 0.0), ray, hit, pressed, button, quick))


def run(behavior, seconds):
    for _ in range(int(round(seconds / DT))):
        behavior.scene.frame(DT, True)
        behavior.frame(DT)


def testTheCameraStandsOnTheHandleSideWhateverSideThePlayerIsOn():
    for aux in range(4):
        for yaw in (0, 90, 180, 270):
            behavior, view = make(aux, yaw)
            camera = behavior.camera
            for key, point in (("pos", Math.SCENE_CAMERA["pos"]), ("target", Math.SCENE_CAMERA["target"])):
                want = Math.worldPoint(behavior.facing, POS, point)
                got = view.toWorld(*camera[key])
                assert all(near(a, b, 1e-6) for a, b in zip(got, want)), (aux, yaw, key)
            assert camera["fov"] == 34.0 and near(camera["keepWidth"], 16.0 / 9.0)
            dx, dz = Math.handleSide(behavior.facing)
            cam = view.toWorld(*camera["pos"])
            assert dx * (cam[0] - (POS[0] + 0.5)) + dz * (cam[2] - (POS[2] + 0.5)) > 2.0, "相机在锅柄那一边"


def testTheStyleIsTheJavaOne():
    behavior, _ = make()
    assert behavior.chrome == "java" and behavior.flightSeconds == 0.4
    assert (behavior.workPlane, behavior.carryLift, behavior.carrySize) == (4.0, 2.5, 4.5)
    assert behavior.usable(item("minecraft:beef")) and behavior.usable(item("minecraft:egg"))
    assert not behavior.usable(item("minecraft:cooked_beef")) and not behavior.usable(item("minecraft:stick"))


def testTheHandleAndTheFoodAreWhatTheCursorCanHitAndTheMouthOnlyWithAStackInHand():
    behavior, view = make()
    keys = [box.key for box in behavior.pickables()]
    assert keys == ["handle", "food"]
    view.hand = item("minecraft:beef", 3)
    assert [box.key for box in behavior.pickables()] == ["handle", "mouth", "food"]
    view.hand = None
    assert behavior.pickables()[0].key == "handle"
    for aux in range(4):
        behavior, view = make(aux, 90)
        box = behavior.pickables()[0]
        centre = view.toWorld(*[(box.lo[i] + box.hi[i]) / 2.0 for i in range(3)]) if hasattr(box, "lo") else None
        assert box.key == "handle"
        if centre is not None:
            dx, dz = Math.handleSide(behavior.facing)
            assert dx * (centre[0] - (POS[0] + 0.5)) + dz * (centre[2] - (POS[2] + 0.5)) > 0.8, "锅柄在方块朝向那一侧"


def testPressingTheHandleLiftsThePanAndAQuickPullUpTosses():
    behavior, view = make(down=1.0)
    handle = (8.0, 2.0, 22.0)
    assert event(behavior, "down", handle) is True and behavior.stroking
    start = behavior._strokeY(behavior.ray)                      # 按下那一刻光标在竖直平面上的高度
    run(behavior, 0.1)
    pan = behavior.scene.show.nodes["pan"]
    assert near(pan.pos[1], 0.5, 0.02), "抓着锅柄：锅拎起来"
    assert not [a for a in view.actions if a[0] == "toss"], "手没动：不颠"
    for step in range(1, 5):
        event(behavior, "move", (8.0, start + step * 1.0, 8.0), pressed=True)        # 每帧在竖直平面上往上 1 像素 = 60 像素每秒
        behavior.scene.frame(DT, True)
        behavior.frame(DT)
    sent = [a for a in view.actions if a[0] == "toss"]
    assert len(sent) == 1 and near(sent[0][1]["strength"], (60.0 - 30.0) / 80.0, 0.05), sent
    event(behavior, "up", None)
    assert not behavior.stroking
    assert behavior.scene.show.tossing(), "自己颠的马上演给自己看"


def testAClickOnTheHandleTossesGently():
    behavior, view = make()
    event(behavior, "down", (8.0, 2.0, 22.0))
    run(behavior, 0.1)
    event(behavior, "up", None)
    assert view.actions == [("toss", {"strength": 0.4})]


def testHoldingTheHandleTooLongWithoutPullingTossesNothingAndSetsThePanDown():
    behavior, view = make()
    event(behavior, "down", (8.0, 2.0, 22.0))
    run(behavior, 0.6)
    event(behavior, "up", None)
    run(behavior, 0.3)
    assert view.actions == [] and near(behavior.scene.show.nodes["pan"].pos[1], 0.0, 0.01)


def testClickingTheFoodTossesWithTheLeftButtonAndTakesItAllWithTheRight():
    behavior, view = make()
    assert event(behavior, "down", (8.0, 1.0, 8.0)) is True
    assert view.actions == [("toss", {"strength": 0.4})]
    run(behavior, 0.6)
    assert event(behavior, "down", (8.0, 1.0, 8.0), button=1) is True
    assert view.actions[-1] == ("take", {})


def testTheOwnTossAndTakeBuzzTheMomentTheyAreSentAndTheServersPlacedAndRefusedBuzzThroughTheScene():
    """触屏的轻震：自己的颠 = 翻面、取 = 拿起，点下去这一刻就震（不等服务端）；服务端回的放进来 / 被拒，场景交给本人开着的站点（feel）震。"""
    behavior, view = make()
    event(behavior, "down", (8.0, 1.0, 8.0))
    assert view.actions == [("toss", {"strength": 0.4})] and view.buzzes == ["flip"]
    run(behavior, 0.6)
    event(behavior, "down", (8.0, 1.0, 8.0), button=1)
    assert view.actions[-1] == ("take", {}) and view.buzzes == ["flip", "pick"]
    del view.buzzes[:]
    behavior.scene.event("placed", {})
    behavior.scene.event("refused", {"stack": item("minecraft:beef", 1)})
    behavior.scene.event("tossed", {"strength": 0.4})
    assert view.buzzes == ["put", "refuse"], "放进来、被拒；别人的颠 / 取不是本人的手"
    behavior.onClose()
    behavior.scene = None
    behavior, view = make()
    scene = behavior.scene
    behavior.onClose()
    scene.event("placed", {})
    assert view.buzzes == [] and scene.feel is None, "关了站点：场景不再替这个视图震"


def testDoneFoodIsTakenWithEitherButton():
    behavior, view = make(food="minecraft:cooked_beef")
    event(behavior, "down", (8.0, 1.0, 8.0))
    assert view.actions == [("take", {})]


def testClickingAnEmptyPanDoesNothing():
    behavior, view = make(food=None)
    event(behavior, "down", (8.0, 1.0, 8.0))
    assert view.actions == []


def testWithAStackInHandAnyClickOnThePanPlacesItLeftTheWholeStackRightOne():
    behavior, view = make(hand=item("minecraft:beef", 5), food=None)
    assert event(behavior, "down", (8.0, 3.0, 8.0)) is True
    assert view.actions == [("place", {"one": False})]
    assert event(behavior, "down", (8.0, 3.0, 8.0), button=1) is True
    assert view.actions[-1] == ("place", {"one": True})
    event(behavior, "down", (8.0, 2.0, 22.0))                # 手上拿着东西点锅柄也是放（JE 的 onItemClick 不挑节点）
    assert view.actions[-1] == ("place", {"one": False}) and not behavior.stroking, "拿着东西不是抓锅柄"
    assert view.flew == 3, "锅里放得进：每放一下，触屏点选的那一叠从托盘里它那一格飞过来（前置包的 view.flyIn）"
    view.fitting = None
    event(behavior, "down", (8.0, 3.0, 8.0))
    assert view.actions[-1] == ("place", {"one": False}) and view.flew == 3, "锅里放不进：照发（服务端拒），不飞"


def testWithAStackInHandAClickOutsideThePanIsLeftToTheKernel():
    behavior, view = make(hand=item("minecraft:beef", 5), food=None)
    assert event(behavior, "down", (60.0, 0.0, -40.0), button=1) is False, "右键点在别处：内核把手上的放回背包"
    assert view.actions == []


def testAPressThatNeverGotItsReleaseIsEndedByTheNextPress():
    behavior, view = make()
    event(behavior, "down", (8.0, 2.0, 22.0))
    assert behavior.stroking
    event(behavior, "down", (8.0, 1.0, 8.0), button=1)               # 松手在窗口外：抬起没送到，下一次按下先把上一把收掉
    assert not behavior.stroking and not behavior.scene.show.stroke.held
    assert view.actions[-1] == ("take", {}), "然后照常处理这一下（右键点食物 = 取）"


def testShiftClickOnTheHandleReachesThroughToTheFood():
    behavior, view = make()
    assert event(behavior, "down", (8.0, 2.0, 22.0), quick=True) is True
    assert not behavior.stroking and view.actions == [("toss", {"strength": 0.4})], "Shift 点穿过锅柄（strokes）：当作点食物"


def testTheHandleIsOutlinedUnderTheCursorAndWhileStrokingButNotWithAStackInHand():
    behavior, view = make()
    event(behavior, "move", (8.0, 2.0, 22.0), pressed=False)
    behavior.frame(DT)
    assert behavior.scene.hovered is True
    event(behavior, "move", (8.0, 1.0, 8.0), pressed=False)
    behavior.frame(DT)
    assert behavior.scene.hovered is False, "光标在食物上：不描锅柄"
    event(behavior, "move", (8.0, 2.0, 22.0), pressed=False)
    view.hand = item("minecraft:beef", 3)
    behavior.frame(DT)
    assert behavior.scene.hovered is False, "拿着东西时锅柄不是抓的地方"
    view.hand = None
    event(behavior, "down", (8.0, 2.0, 22.0))
    event(behavior, "move", (60.0, 5.0, -40.0), pressed=True)
    behavior.frame(DT)
    assert behavior.scene.hovered is True, "按着的时候光标离开锅柄也一直描"


def testThePanIsOutlinedWhileWhatIsCarriedFitsIntoIt():
    """手上的东西放得进锅、光标在锅上：锅身描一圈亮边（scene.offering -> variable.mod_pan_lit）；放不进、手空着、光标不在锅上不描。"""
    behavior, view = make()
    view.hand = item("minecraft:beef", 3)
    behavior.frame(DT)
    assert behavior.scene.offering is False, "光标还没到锅上"
    event(behavior, "move", (8.0, 1.0, 8.0), pressed=False)
    behavior.frame(DT)
    assert behavior.scene.offering is True
    view.fitting = None
    behavior.frame(DT)
    assert behavior.scene.offering is False, "锅里是别的东西 / 满了：放不进"
    view.fitting, view.hand = 0, None
    behavior.frame(DT)
    assert behavior.scene.offering is False, "手空着"
    view.hand, view.input = item("minecraft:beef", 3), "touch"
    behavior.onLeave()
    behavior.frame(DT)
    assert behavior.hover is None and behavior.scene.offering is True, "触屏没有悬停：拿着放得进的东西就描"
    behavior.onClose()


def testShiftClickOnTheTrayAsksTheBehaviorFirstAndAFryableStackGoesInWithAPlaceFromTheSlot():
    """前置包的 onInventoryShiftClick 钩子（空手 Shift 点托盘里的一叠先问表现）：有营火配方的发 place {from: 背包格号}，返回真；
    没有配方的返回假、什么也不发（内核照旧）。"""
    behavior, view = make(food=None)
    assert behavior.onInventoryShiftClick(7, item("minecraft:beef", 12)) is True
    assert view.actions[-1] == ("place", {"from": 7})
    assert behavior.onInventoryShiftClick(0, item("minecraft:egg", 3)) is True and view.actions[-1] == ("place", {"from": 0})
    assert behavior.onInventoryShiftClick(5, item("minecraft:stick", 1)) is False and behavior.onInventoryShiftClick(5, None) is False
    assert len(view.actions) == 2


def testOpeningHangsTheSkilletBookAndClosingCleansUp():
    behavior, view = make()
    assert view.booked is not None and view.booked.__class__.__name__ == "PanSource"
    view.items = [item("minecraft:beef", 4), None]
    assert view.booked.inStation() == [item("minecraft:beef", 4)], "书看锅里的东西：站点的 pan 槽组"
    assert view.booked.current() == "minecraft:beef"
    scene = behavior.scene
    assert scene.show.focused and scene.startsOf is not None
    event(behavior, "down", (8.0, 2.0, 22.0))
    behavior.onClose()
    assert not scene.show.focused and scene.startsOf is None and scene.cursorAt is None and not behavior.stroking and behavior.scene is None


def testTheEggAndTheNewPiecesFlyInFromTheBottomOfTheScreenOnlyForTheCook():
    behavior, view = make(food=None)
    behavior.scene.apply({"dimensionId": 0, "pos": list(POS), "item": item("minecraft:beef", 1), "batch": 1, "byHand": True, "heated": True,
                          "down": 0.0, "up": 0.0, "rate": 0.0, "both": False})
    assert behavior._startsOf(4.0, 0, 3) == (0.0, 0.0), "屏幕上的点算不出来（没射线）：不偏移"
    cam = behavior.camera["pos"]
    width, height = world.screen
    middle = C.ray(cam, behavior._toStation((8.0, 4.0, 8.0)))
    start = C.ray(cam, behavior._toStation((8.0 + 3.0, 4.0, 8.0 + 20.0)))
    view.rays[(width * 0.5, height * 0.5)] = middle
    view.rays[(width * 0.5, height * 0.97)] = start
    dx, dz = behavior._startsOf(4.0, 1, 3)
    assert near(dx, 3.0, 1e-4) and near(dz, 20.0, 1e-4), "第 1 件（共 3 件，正中间那件）从屏幕底边正中起飞：偏移 = 那一点 - 屏幕中心那一点"
    behavior.ray = middle
    cursor = behavior._cursorAt(6.0)
    assert cursor is not None and near(cursor[1], 6.0, 1e-4), "光标在 y = 6 的水平面上的点（场景坐标）"


def testStrokeHeightIsWhereTheRayMeetsTheUprightPlaneThroughThePan():
    behavior, _ = make()
    cam = behavior.camera["pos"]
    for y in (0.0, 3.0, 9.5, -4.0):
        ray = C.ray(cam, behavior._toStation((8.0, y, 8.0)))
        assert near(behavior._strokeY(ray), y, 1e-4), y
    on = C.ray(cam, behavior._toStation((12.0, 5.0, 8.0)))
    assert near(behavior._strokeY(on), 5.0, 1e-4), "平面是竖直的、正对镜头：左右怎么偏，高度都一样读"
    along = (0.0, 5.0, 0.0, 1.0, 0.0, 0.0)
    assert behavior._strokeY(along) is None, "和平面平行的射线读不出高度"


def testTheBehaviorIsOnlyRegisteredWithApiTwoOrNewer():
    api = C.makeApi()
    api.API_VERSION = 1
    assert PanView.register(api) is None, "旧前置包：煎锅走经典玩法"


# ---------------------------------------------------------------- 触屏长按（onHold）：右键 / Shift 点击的变体，只给和点一下不一样的

HoldMenu = C.load("Compat.Diegesis.HoldMenu")


def hold(behavior, target):
    """手指按在场景里按住不动：前置包在按下那一刻问表现的 onHold（和按下收到的同一种拾取事件，左键），按 View.pointer 的做法拾取。"""
    cam = behavior.camera["pos"]
    ray = C.ray(cam, behavior._toStation(target)) if target is not None else None
    hit = Pick.pick(behavior.pickables(), ray) if ray is not None else None
    return behavior.onHold(Pointer.PointerEvent("down", (0.0, 0.0), ray, hit, True, 0, False))


def testHoldingAStackOverThePanOffersPutOneWhereTheRightClickPlacesJustOne():
    behavior, view = make(hand=item("minecraft:beef", 5), food=None)
    for target in ((8.0, 3.0, 8.0), (8.0, 1.0, 8.0), (8.0, 2.0, 22.0)):          # 锅口、食物、锅柄：哪处都一样（onItemClick 不挑节点）
        assert hold(behavior, target) == {"menu": [HoldMenu.PUT_ONE]}, target
    assert HoldMenu.PUT_ONE == {"label": "放一个", "button": 1, "quick": False}
    event(behavior, "down", (8.0, 3.0, 8.0))
    event(behavior, "down", (8.0, 3.0, 8.0), button=1)
    assert view.actions == [("place", {"one": False}), ("place", {"one": True})], "点一下整叠、右键一个：真的不一样"
    assert hold(behavior, (60.0, 0.0, -40.0)) is None, "锅外：点一下什么也不接，没有变体"
    view.hand = item("minecraft:beef", 1)
    assert hold(behavior, (8.0, 3.0, 8.0)) is None, "只有一个：放一个就是放整叠"
    view.hand = item("minecraft:beef", 5)
    view.fitting = None
    assert hold(behavior, (8.0, 3.0, 8.0)) is None, "锅里是别的东西 / 满了：放不进"


def testEmptyHandOverTheRawFoodOffersTakeAllBackWhereATapWouldToss():
    behavior, view = make()
    assert hold(behavior, (8.0, 1.0, 8.0)) == {"menu": [HoldMenu.TAKE_ALL_BACK]}
    assert HoldMenu.TAKE_ALL_BACK == {"label": "全部取回", "button": 1, "quick": False}
    event(behavior, "down", (8.0, 1.0, 8.0))
    assert view.actions == [("toss", {"strength": 0.4})], "点一下：颠"
    run(behavior, 0.6)
    event(behavior, "down", (8.0, 1.0, 8.0), button=1)
    assert view.actions[-1] == ("take", {}), "右键：全拿回背包"


def testTheDoneFoodTheHandleAndAnEmptyPanHaveNoMenuSoTheStrokeAndTheTakeStartAtOnce():
    behavior, view = make(food="minecraft:cooked_beef")
    assert hold(behavior, (8.0, 1.0, 8.0)) is None, "熟了：点一下就是全拿回"
    behavior, view = make()
    assert hold(behavior, (8.0, 2.0, 22.0)) is None, "锅柄：抓住往上提 = 颠，一按下就开始"
    event(behavior, "down", (8.0, 2.0, 22.0))
    assert behavior.stroking
    behavior, view = make(food=None)
    assert hold(behavior, (8.0, 1.0, 8.0)) is None, "锅是空的：点一下什么也不发"
    behavior.scene = None
    assert hold(behavior, (8.0, 1.0, 8.0)) is None


if __name__ == "__main__":
    raise SystemExit(C.fdtest.run(globals()))
