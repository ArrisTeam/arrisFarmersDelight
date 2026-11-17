# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点里本人的点击（Compat/Diegesis/PotView.onPointer）：按哪个键能做什么照 JE（假视图、假前置包 Api，场景用 potclient 的假引擎）。"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import potclient as C

PotView = C.load("Compat.Diegesis.PotView")
PotPick = C.load("Compat.Diegesis.PotPick")
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
Rules = C.load("Shared.Rules.PotStation")
Geometry = dgtest.load("Shared.Geometry")        # 前置包的几何：光标射线和液面的交点
Txn = dgtest.load("Shared.ActionTxn")            # 前置包的动作目标 / 点击种类
SpreadState = dgtest.load("Client.Spread").SpreadState      # 前置包真的平分手势：按下记着、松手才发
Pointer = dgtest.load("Client.Pointer")          # 前置包真的指针路由（托盘拖到场景里松手补的那一按一松）
TrayClient = dgtest.load("Client.Tray")
POS = C.POS
LEFT, RIGHT, MIDDLE = 0, 1, 2
BOWL = {"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 1}
SOUP_DATA = {"meal": {"newItemName": "arris:pumpkin_soup", "count": 3}, "vessel": {"newItemName": "minecraft:bowl"}}


class Node(object):
    def __init__(self, key, payload=None):
        self.key, self.payload = key, payload


class Hit(object):
    def __init__(self, key, payload=None):
        self.node = Node(key, payload)


class Event(object):
    def __init__(self, button=LEFT, hit=None, quick=False, ray=None, kind="down", screen=(100.0, 50.0)):
        self.kind, self.button, self.hit, self.quick = kind, button, hit, quick
        self.point, self.ray, self.screen = (8.0, 9.0, 8.0), ray, screen


class Box(object):
    """前置包的 Api.box 给的拾取盒：只记下是什么、在哪。"""

    def __init__(self, key, lo, hi, payload=None):
        self.key, self.lo, self.hi, self.payload = key, tuple(lo), tuple(hi), payload


class Api(object):
    TOUCH = "touch"
    PICKUP, QUICK_MOVE, PICKUP_ALL = Txn.PICKUP, Txn.QUICK_MOVE, Txn.PICKUP_ALL
    Geometry = Geometry
    stationTarget = staticmethod(Txn.stationTarget)

    @staticmethod
    def box(key, lo, hi, payload=None):
        return Box(key, lo, hi, payload)


class FakeView(object):
    """前置包给表现类的 view：只记下发出去的动作、内核点击、拿放的轻响和放料的调用；平分手势用前置包真的。"""

    def __init__(self):
        self.hand = None
        self.data = {}
        self.input = "mouse"
        self.dimensionId = 0
        self.pos = POS
        self.actions, self.drops, self.clicks, self.sounds = [], [], [], []
        self.plateHover = False
        self.fitIndex = 0                          # fits() 的回答：手上的东西落在哪一格，放不进是 None
        self.behavior = None
        self.spread = SpreadState(self, None)
        self.lifts = []                            # carryFrom(点, 大小)：拿起的一叠从哪起飞
        self.dropping = False                      # 内核正在送拖着放补的那一下点击
        self.buzzes = []                           # buzz(种类)：触屏的轻震（前置包有才有）
        self.window = 0.25                         # doubleSeconds() 的回答（前置包有才有；键鼠 0.25，触屏 0.4）

    def buzz(self, kind):
        self.buzzes.append(kind)

    def doubleSeconds(self):
        return self.window

    def carryFrom(self, point, size=None):
        self.lifts.append((tuple(point), size))

    def fits(self, group):
        return self.fitIndex if self.hand is not None else None

    def foley(self, putDown=False):
        self.sounds.append("put" if putDown else "pick")

    def traySlot(self, pos):
        return None

    def overUi(self, pos):
        return False

    def sendAction(self, name, payload):
        self.actions.append((name, payload))

    def click(self, target, button=0, kind="PICKUP"):
        self.clicks.append((target, button, kind))

    def plate(self, model):
        pass

    def tooltip(self, lines):
        pass

    def rayAt(self, screen):
        return None                                # 没有相机：端走的终点回到缺省

    def dropInto(self, group, button):
        index = self.fits(group)
        if index is not None:
            self.drops.append((group, button))
        return index

    def toWorld(self, x, y, z):
        return (POS[0] + x / 16.0, POS[1] + y / 16.0, POS[2] + z / 16.0)

    def toStation(self, wx, wy, wz):
        return ((wx - POS[0]) * 16.0, (wy - POS[1]) * 16.0, (wz - POS[2]) * 16.0)


class Base(object):
    def __init__(self, view):
        self.view = view


def behaviorOf():
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    view = FakeView()
    behavior = type("TestBehavior", (PotView.PotViewMixin, Base), {"api": Api})(view)
    view.behavior = behavior
    behavior.scene = Scenes.ensure(0, POS)
    behavior.scene.apply(C.look([("minecraft:carrot", 1)]))
    return behavior, view


def testTheLastSunkThingComesBackOnAnyMouseButton():
    # PotBehavior.java:502-505：Click sunk 不看 button
    for button in (LEFT, RIGHT, MIDDLE):
        behavior, _view = behaviorOf()
        taken = []
        behavior.serve.sunkClick = lambda: taken.append(True) or True
        assert behavior.onPointer(Event(button, Hit("sunk"))) is True and taken == [True], button


def testOnlyTheSoupTakesJustTheLeftButton():
    # PotBehavior.java:491：Click soup && button == 0（握勺子的 Stroke 不在这里，见下面几条）
    behavior, _view = behaviorOf()
    scooped = []
    behavior.serve.soupClick = lambda event: scooped.append(event.button) or True
    assert behavior.onPointer(Event(RIGHT, Hit("soup"))) is False and scooped == []
    assert behavior.onPointer(Event(LEFT, Hit("soup"))) is True and scooped == [LEFT]


def testBothMouseButtonsGraspTheSpoonHandle():
    # FocusInput.java:412-413：笔画左右键都起；PotBehavior.java:466-488：START / END 不看按键
    for button in (LEFT, RIGHT):
        behavior, view = behaviorOf()
        assert behavior.onPointer(Event(button, Hit("ladle"))) is True, button
        assert behavior.scene.hand and behavior.gesture.stroking and view.clicks == [] and view.actions == [], button
        behavior.clock += 0.6                                  # 按得久：拖着搅，松手就放下
        assert behavior.onPointer(Event(button, kind="up")) is True
        assert not behavior.scene.hand and not behavior.gesture.stroking and not behavior.gesture.heldByClick, button


def testAQuickClickWithEitherButtonKeepsTheSpoonInHandAndTheNextPressAnywhereOnlyPutsItDown():
    # FocusInput.java:360-363：留在手里的笔画，下一次按下不管哪个键、按在哪里（料上也一样）只是把它放下，不做别的
    for button, next_button in ((LEFT, LEFT), (RIGHT, RIGHT), (RIGHT, LEFT), (LEFT, RIGHT)):
        behavior, view = behaviorOf()
        behavior.onPointer(Event(button, Hit("ladle")))
        behavior.clock += 0.1
        assert behavior.onPointer(Event(button, kind="up")) is True
        assert behavior.scene.hand and behavior.gesture.heldByClick, (button, "点一下：勺子留在手里")
        assert behavior.onPointer(Event(next_button, Hit("item", 0))) is True, (button, next_button)
        assert not behavior.scene.hand and not behavior.gesture.stroking and view.clicks == [], (button, next_button, "只放下，没有拿料")
        assert behavior.onPointer(Event(next_button, kind="up")) is False and not behavior.scene.hand, "放下那一按的抬起：没有后续"
        assert behavior.onPointer(Event(button, Hit("item", 0))) is True and view.clicks, "放下之后料照常点得到"


def testAnotherButtonPressedWhileDraggingTheSpoonDoesNothing():
    # FocusInput.press：gesture != null 就 return；原来右键根本进不来握勺子，现在两个键都能起笔画，别让拖着搅的时候点料也拿起来
    behavior, view = behaviorOf()
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    assert behavior.onPointer(Event(RIGHT, Hit("item", 0))) is True
    assert view.clicks == [] and behavior.scene.hand and behavior.gesture.stroking, "还握着勺子，料没动"
    behavior.clock += 0.6
    behavior.onPointer(Event(LEFT, kind="up"))
    assert not behavior.scene.hand, "松开按着的那个键，笔画结束"


def testTheBehaviourIsBusyExactlyWhileTheSpoonIsInTheHand():
    # FocusInput.isBusy（有笔画就忙）：内核的 mayGoOver 和托盘的按下都问它（表现的 busy() 钩子）
    behavior, view = behaviorOf()
    assert behavior.busy() is False, "空闲"
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    assert behavior.busy() is True, "按着勺柄拖"
    behavior.clock += 0.6
    behavior.onPointer(Event(LEFT, kind="up"))
    assert behavior.busy() is False, "拖完松手：勺子放下了"
    behavior.onPointer(Event(RIGHT, Hit("ladle")))
    behavior.clock += 0.1
    behavior.onPointer(Event(RIGHT, kind="up"))
    assert behavior.busy() is True and behavior.gesture.heldByClick, "点一下：勺子留在手里，还没放下就还忙着"
    behavior.onPointer(Event(LEFT, Hit("mouth")))
    assert behavior.busy() is False, "下一按放下了"
    behavior.onPointer(Event(LEFT, kind="up"))
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    behavior.onClose()
    assert behavior.busy() is False, "关站：勺子放下"


RAY = (8.0, 41.0, -21.0, 0.0, -0.6, 0.8)          # 机位射向液面


def _move(key=None, payload=None, ray=None):
    return Event(LEFT, Hit(key, payload) if key else None, ray=ray, kind="move")


def testTheHoverFollowsTheCursorUntilTheSpoonIsInHandAndThenStaysOnTheSpoon():
    # FocusInput.java:798：只有 gesture == null（或在搬东西）才更新悬停；笔画里悬停冻在勺子上
    behavior, view = behaviorOf()
    behavior.onPointer(_move("item", 0))
    assert behavior.hover == ("item", 0)
    behavior.onPointer(_move("ladle"))
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    behavior.onPointer(_move("item", 0, RAY))                      # 勺子拖过一件料
    assert behavior.hover == ("ladle", None), "冻在勺子上，不是那件料"
    assert behavior.ray == RAY and behavior.scene.aim is not None, "光标的射线、勺尖的目标照常跟着（那是 mouseX / mouseY，不是悬停）"
    behavior.onPointer(_move(None, None, RAY))
    assert behavior.hover == ("ladle", None), "挪到什么也没有的地方也一样"
    behavior.clock += 0.6
    behavior.onPointer(Event(LEFT, kind="up"))                     # 拖完松手：没有笔画了
    behavior.onPointer(_move("item", 0))
    assert behavior.hover == ("item", 0), "悬停又跟着光标走"


def testTheHoverStaysFrozenWhileTheSpoonIsHeldByAClickToo():
    behavior, view = behaviorOf()
    behavior.onPointer(_move("ladle"))
    behavior.onPointer(Event(RIGHT, Hit("ladle")))
    behavior.clock += 0.1
    behavior.onPointer(Event(RIGHT, kind="up"))
    assert behavior.gesture.heldByClick
    behavior.onPointer(_move("item", 0, RAY))
    behavior.onPointer(_move("served"))
    assert behavior.hover == ("ladle", None), "点一下留在手里的勺子也是笔画：悬停不动"
    behavior.onPointer(Event(LEFT, Hit("mouth")))                  # 下一按放下
    behavior.onPointer(Event(LEFT, kind="up"))
    behavior.onPointer(_move("served"))
    assert behavior.hover == ("served", None)


def testPressingTheSpoonMakesItTheHoveredNodeEvenIfTheCursorJumpedThereWithoutAFrameBetween():
    behavior, view = behaviorOf()
    behavior.onPointer(_move("item", 0))
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    assert behavior.hover == ("ladle", None), "冻住的不能是上一帧路过的料（它会一直卡在那里）"


def _frame(behavior):
    """表现的一帧，不带徽章 / 悬着的容器那两块（它们要完整的内核视图）：只看光标指着的那件怎么交给场景。"""
    behavior.serve.frame = behavior.hud.frame = lambda dt: None
    behavior.serve.offering = lambda: False
    behavior.frame(1.0 / 60.0)


def testTheFloatingItemOrTheServedSlotUnderTheCursorIsTheOneHandedToTheSceneToRise():
    # NodeInstance.java:808-810：槽节点（item_N、served）被指着才抬；勺柄、锅口、soup、sunk 不抬
    behavior, view = behaviorOf()
    scene = behavior.scene
    _frame(behavior)
    assert scene.lift.target is None
    for key, payload, index in (("item", 2, 2), ("item", 0, 0), ("served", None, 6)):
        behavior.onPointer(_move(key, payload))
        _frame(behavior)
        assert scene.lift.target == index, (key, payload)
    for key in ("mouth", "ladle", "soup", "sunk", None):
        behavior.onPointer(_move(key))
        _frame(behavior)
        assert scene.lift.target is None, key
    behavior.onPointer(_move("item", 1))
    behavior.onLeave()                                          # 触屏：点完指针离开
    _frame(behavior)
    assert scene.lift.target is None
    behavior.onPointer(_move("item", 1))
    _frame(behavior)
    behavior.onClose()
    assert scene.lift.target is None, "关站：没有光标指着了，抬起的料自己落回去"


def testDraggingTheSpoonOverTheItemsDoesNotRaiseThem():
    # 勺子在手里悬停冻在勺子上（FocusInput.java:798），所以划过去的料不抬
    behavior, view = behaviorOf()
    behavior.onPointer(_move("ladle"))
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    behavior.onPointer(_move("item", 0, RAY))
    _frame(behavior)
    assert behavior.scene.lift.target is None
    behavior.clock += 0.6
    behavior.onPointer(Event(LEFT, kind="up"))
    behavior.onPointer(_move("item", 0))
    _frame(behavior)
    assert behavior.scene.lift.target == 0


def testTheHitBoxesIgnoreTheLift():
    # NodeInstance.java:48-52：命中盒用不含抬起的矩阵，抬起不挪点击的地方
    behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
    boxes = lambda: [(box.key, box.lo, box.hi) for box in behavior.pickables() if box.key in ("item", "served")]
    rest = boxes()
    behavior.scene.lift.target = 0
    for _ in range(60):
        behavior.scene.lift.step(1.0 / 60.0)
    assert behavior.scene.lift.amount[0] > 0.99 and boxes() == rest


def testNoTooltipAtAllWhileTheSpoonIsInHand():
    # FocusScreen.java:455：isBusy() 就一个提示都不画（节点的、徽章的都算）
    behavior, view = behaviorOf()
    view.plateHover = True
    state = {"servings": 3, "mealName": "Soup"}
    assert behavior.hud._tip(state) == ["3 × Soup"], "没握勺子：徽章的提示照常"
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    assert behavior.hud._tip(state) is None, "按着拖"
    behavior.clock += 0.6
    behavior.onPointer(Event(LEFT, kind="up"))
    assert behavior.hud._tip(state) == ["3 × Soup"], "松手：又有了"
    behavior.onPointer(Event(RIGHT, Hit("ladle")))
    behavior.clock += 0.1
    behavior.onPointer(Event(RIGHT, kind="up"))
    assert behavior.hud._tip(state) is None, "点一下留在手里"
    behavior.onPointer(Event(LEFT, Hit("mouth")))
    assert behavior.hud._tip(state) == ["3 × Soup"], "放下了"


def testTouchStillNeverKeepsTheSpoonInHandWhicheverButtonTheTapWasSentAs():
    for button in (LEFT, RIGHT):                               # "单个"档把点按送成右键
        behavior, view = behaviorOf()
        view.input = Api.TOUCH
        behavior.onPointer(Event(button, Hit("ladle")))
        behavior.clock += 0.1
        behavior.onPointer(Event(button, kind="up"))
        assert not behavior.scene.hand and not behavior.gesture.heldByClick, button


def testTheMealsContainerInHandScoopsOnAnyMouseButton():
    # PotBehavior.java:516-539：onItemClick 不看 button，Shift 是全盛
    for button, quick in ((LEFT, False), (RIGHT, False), (MIDDLE, False), (RIGHT, True)):
        behavior, view = behaviorOf()
        view.hand = {"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 1}
        view.data = {"meal": {"newItemName": "arris:pumpkin_soup", "count": 3}, "vessel": {"newItemName": "minecraft:bowl"}}
        assert behavior.onPointer(Event(button, Hit("mouth"), quick)) is True
        assert view.actions == [("scoop", {"all": quick, "from_inventory": False})], (button, quick, view.actions)
        assert behavior.serve.scoopedHere == behavior.clock, "碗落进去的地方敲过水波了"


CARROTS = {"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 4}


def _slot(index):
    return Txn.stationTarget(Rules.GROUP_INGREDIENTS, index)


def testAnythingElseInHandGoesIntoThePotWithTheButtonGivenButOnlyOnRelease():
    # FocusInput.clickItem 末尾（:514-519）+ release（:656-661）：锅口是放置区、onItemClick 不接它，按下只记下（哪一格、哪个键），松手才发
    for button in (LEFT, RIGHT):
        behavior, view = behaviorOf()
        view.hand = dict(CARROTS)
        view.data = dict(SOUP_DATA)                            # 锅里有菜，但手上不是它的容器
        assert behavior.onPointer(Event(button, Hit("mouth"))) is True, button
        assert view.actions == [] and view.clicks == [] and view.drops == [] and view.sounds == [], "按下什么都不发、不响"
        assert view.spread.active and view.spread.button == button, "记下了这一下"
        assert behavior.onPointer(Event(button, kind="up")) is False and view.clicks == [], "表现自己的抬起不发"
        assert view.spread.release(button, (100.0, 50.0)) is True        # 指针路由在抬起时调
        assert view.clicks == [(_slot(0), button, "PICKUP")], button
        assert view.sounds == ["put"], "放下的轻响由内核在松手时放（FocusInput.java:659）"
        assert not view.spread.active


def testTheSlotIsTheOneChosenWhenPressedNoMatterWhereOrWhenItIsLetGo():
    # JE 的 zoneSlot 在按下时选（同种没满的优先，否则第一个空格），松手发的就是那一格；松在哪都行
    behavior, view = behaviorOf()
    view.hand, view.fitIndex = dict(CARROTS), 2
    behavior.onPointer(Event(LEFT, Hit("mouth")))
    view.fitIndex = 4                                          # 按着的这会儿锅里别的格变了
    view.spread.release(LEFT, (400.0, 300.0))                  # 松在场景另一头
    assert view.clicks == [(_slot(2), LEFT, "PICKUP")]


def testWhenNothingFitsTheMouthTakesNoClickAndAnythingBelongingToTheKernelStaysWithIt():
    behavior, view = behaviorOf()
    view.hand, view.fitIndex = dict(CARROTS), None
    assert behavior.onPointer(Event(RIGHT, Hit("mouth"))) is False, "没有格子放得下：锅口不接（右键由内核放回背包）"
    assert not view.spread.active and view.clicks == [] and view.sounds == []


def testTheStackLeavesTheHandBeforeTheReleaseAndNothingIsSent():
    behavior, view = behaviorOf()
    view.hand = dict(CARROTS)
    behavior.onPointer(Event(LEFT, Hit("mouth")))
    view.hand = None                                           # 服务端先把它收走了（站点关了、被别的动作拿走）
    assert view.spread.release(LEFT, (100.0, 50.0)) is False and view.clicks == [] and view.sounds == []


def testAnOldPrerequisiteWithoutTheSpreadGestureStillDropsOnPress():
    behavior, view = behaviorOf()
    view.hand, view.spread = dict(CARROTS), None
    assert behavior.onPointer(Event(RIGHT, Hit("mouth"))) is True
    assert view.drops == [(Rules.GROUP_INGREDIENTS, RIGHT)] and view.clicks == []


class RoutedView(FakeView):
    """前置包的指针路由（真的 Pointer）要的口子：左边 40 个单位是托盘（按下拿起一叠，服务端立刻把它放到手上），右边是场景（点哪里都是锅口）。"""

    def pointer(self, kind, pos, button=0, quick=False, dropping=False):
        return bool(self.behavior.onPointer(Event(button, Hit("mouth"), quick, kind=kind, screen=tuple(pos))))

    def trayPress(self, pos, button, quick):
        if pos[0] >= 40.0:
            return TrayClient.NONE
        self.hand = dict(CARROTS)
        return TrayClient.PICKED

    def traySlot(self, pos):
        return 3 if pos[0] < 40.0 else None

    def overUi(self, pos):
        return pos[0] < 40.0


def _routed():
    behavior, _ = behaviorOf()
    view = RoutedView()
    view.behavior, behavior.view = behavior, view
    return behavior, view, Pointer.Pointer(lambda: view, lambda: 100.0)


def testDraggingAStackFromTheTrayOntoThePotIsStillCompletedByTheKernelsReleaseClick():
    # 前置包在场景里松手时补一次同一个键的按下 + 抬起（Pointer._settle），再结算平分：补的这一下按下只记下，抬起那一刻发
    behavior, view, pointer = _routed()
    pointer.push("down", (10.0, 10.0), LEFT)
    pointer.frame(None)
    assert view.hand is not None and view.clicks == [], "托盘拿起：这里还没有点锅"
    pointer.push("up", (200.0, 100.0), LEFT)                   # 拖到锅上松手
    pointer.frame(None)
    assert view.clicks == [(_slot(0), LEFT, "PICKUP")] and view.sounds == ["put"], (view.clicks, view.sounds)
    assert not view.spread.active


def testPressingOnThePotWithAStackThenReleasingElsewhereInTheSceneStillPutsItInTheSlotChosenAtPress():
    behavior, view, pointer = _routed()
    view.hand, view.fitIndex = dict(CARROTS), 1
    pointer.push("down", (200.0, 100.0), RIGHT)
    pointer.frame(None)
    assert view.clicks == [], "按下：还没发"
    view.fitIndex = 3
    pointer.push("up", (300.0, 200.0), RIGHT)
    pointer.frame(None)
    assert view.clicks == [(_slot(1), RIGHT, "PICKUP")], view.clicks


def testOverTheMouthTheCarriedStackTakesTheSizeOfWhatLiesThereButTheMealsContainerDoesNot():
    """FocusInput.updateCarry 的 zoneItemSize：光标到了放东西的地方上，手上的东西变成那里的东西的大小。锅口不收盛这锅菜的容器
    （它是来盛的，不是往里放的），所以拿着碗移到锅口上碗不缩。"""
    behavior, view = behaviorOf()
    sizes = []
    view.carryAs = sizes.append
    move = Event(LEFT, Hit("mouth"))
    move.kind = "move"
    view.hand = {"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 4}
    behavior.onPointer(move)
    assert sizes == [PotView.SLOT_SIZE], "料：变成锅里料的大小"
    view.hand = dict(BOWL)
    view.data = dict(SOUP_DATA)
    behavior.onPointer(move)
    assert sizes == [PotView.SLOT_SIZE], "盛这锅菜的碗：不变"
    view.data = {}
    behavior.onPointer(move)
    assert len(sizes) == 2, "锅里没有菜时碗就是一样要放进去的东西"


# ---------------------------------------------------------------- 哪些节点算（PotBehavior.onItemClick：任意带碰撞盒的节点）

def _withMeal(items=(("minecraft:carrot", 1),), hand=BOWL):
    """锅里有料有煮好的菜（盛好的那格也有），手上拿着 hand；漂着的料都落定了（拾取盒要料到了、不在等）。"""
    behavior, view = behaviorOf()
    behavior.scene.apply(C.look(items, served=C.item("arris:pumpkin_soup"), meal=C.item("arris:pumpkin_soup", 3)))
    drift = behavior.scene.drift
    for slot in range(len(items)):
        drift.visible[slot], drift.waiting[slot] = True, False
        drift.x[slot], drift.y[slot], drift.z[slot] = 6.0 + slot, 5.0, 9.0
    view.hand, view.data = hand, dict(SOUP_DATA)
    return behavior, view


def _keys(behavior):
    return [(box.key, box.payload) for box in behavior.pickables()]


def testTakingAFloatingItemOrTheServedSlotMakesTheKernelsPickUpSound():
    # FocusInput.java:496（Shift 点槽）、:507（从槽拿起）：厨锅的 onItemClick 不接这两种，内核出声；右键拿一半也是 PICKUP
    for key, payload, button, quick in (("item", 0, LEFT, False), ("item", 1, RIGHT, False), ("item", 0, LEFT, True),
                                        ("served", None, LEFT, False), ("served", None, RIGHT, False), ("served", None, LEFT, True)):
        behavior, view = _withMeal((("minecraft:carrot", 1), ("minecraft:potato", 1)), hand=None)
        assert behavior.onPointer(Event(button, Hit(key, payload), quick)) is True
        assert len(view.clicks) == 1 and view.sounds == ["pick"], (key, button, quick, view.sounds)
        assert view.clicks[0][2] == ("QUICK_MOVE" if quick else "PICKUP")


def testAStackPickedFromThePotFliesUpFromWhereItLayAtTheSlotsSize():
    """Diegesis 的 FocusInput.snapCarryTo：从站点的槽里拿起的一叠，从那一件的位置起飞、先是槽里的大小（厨锅 3.2），不是直接出现在光标上。
    Shift 移走不到手上：不起飞。"""
    for key, payload, button in (("item", 0, LEFT), ("item", 0, RIGHT), ("served", None, LEFT)):
        behavior, view = _withMeal((("minecraft:carrot", 2),), hand=None)
        behavior.onPointer(Event(button, Hit(key, payload)))
        assert view.lifts == [((8.0, 9.0, 8.0), 3.2)], (key, button, view.lifts)
    behavior, view = _withMeal((("minecraft:carrot", 2),), hand=None)
    behavior.onPointer(Event(LEFT, Hit("item", 0), quick=True))
    assert view.lifts == [] and view.clicks[0][2] == "QUICK_MOVE"


def testOnlyASecondLeftClickOnTheSameSlotGathersAndNotTheClickADragDropMakes():
    """双击聚拢照 JE（FocusInput.clickItem）：同一格、左键、不按 Shift。点了别的格子不聚拢；拖着放的时候内核补的那一下点击（view.dropping）
    也不算——原来 0.25 秒内点哪都变成 PICKUP_ALL，拖着放到锅口的那一下被转成聚拢、什么都没放下。"""
    behavior, view = _withMeal((("minecraft:carrot", 1), ("minecraft:potato", 1)), hand=None)
    behavior.onPointer(Event(LEFT, Hit("item", 0)))
    behavior.onPointer(Event(LEFT, Hit("item", 1)))
    assert [click[2] for click in view.clicks] == ["PICKUP", "PICKUP"], view.clicks
    behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
    behavior.onPointer(Event(LEFT, Hit("item", 0)))
    view.dropping = True
    behavior.onPointer(Event(LEFT, Hit("item", 0)))
    assert [click[2] for click in view.clicks] == ["PICKUP", "PICKUP"], view.clicks


def testTheDoubleClickThatGathersTheRestMakesNoSecondSound():
    # FocusInput.java:498-500：PICKUP_ALL 没有声音；第一下拿起的那一声照有
    behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
    behavior.onPointer(Event(LEFT, Hit("item", 0)))
    behavior.onPointer(Event(LEFT, Hit("item", 0)))
    assert [click[2] for click in view.clicks] == ["PICKUP", "PICKUP_ALL"] and view.sounds == ["pick"]


def testTheDoubleClickWindowIsTheKernelsForTheCurrentInputAndTheirOwnQuarterSecondForOldKernels():
    """触屏两下按下之间要抬手、再落准同一格：前置包按输入方式给间隔（触屏 0.4 秒，view.doubleSeconds），厨锅自己的 0.25 秒不再是唯一的数；
    老版本的前置包没有它，照旧 0.25 秒。"""
    for window, gaps in ((0.4, ((0.35, "PICKUP_ALL"), (0.45, "PICKUP"))), (0.25, ((0.2, "PICKUP_ALL"), (0.3, "PICKUP"))), (None, ((0.2, "PICKUP_ALL"), (0.3, "PICKUP")))):
        for gap, want in gaps:
            behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
            if window is None:
                view.doubleSeconds = None                           # 老版本的前置包：没有这个方法
            else:
                view.window = window
            behavior.onPointer(Event(LEFT, Hit("item", 0)))
            behavior.clock += gap
            behavior.onPointer(Event(LEFT, Hit("item", 0)))
            assert view.clicks[-1][2] == want, (window, gap, view.clicks)


def testAScoopedBowlBuzzsAsAPickUpAndAnOldKernelWithoutBuzzJustSkipsIt():
    behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
    behavior.onEffect("scooped", {"count": 1})
    behavior.onEffect("served", {"grade": 1, "bonus": 0})
    assert view.buzzes == ["pick"], "盛到一份：拿起的那一震（整批出锅不是本人的动作）"
    behavior, view = _withMeal((("minecraft:carrot", 1),), hand=None)
    view.buzz = None                                              # 老版本的前置包：没有 buzz
    behavior.onEffect("scooped", {"count": 1})


def testTheClicksThatHaveTheirOwnSoundOrNoneStayAsTheyWere():
    # 盛汤、取回、握勺子、放进锅口（松手才响）：这几下表现自己的声音 / 服务端的声音照旧，不再多一声拿起
    behavior, view = _withMeal(hand=BOWL)
    behavior.onPointer(Event(LEFT, Hit("mouth")))                              # 拿着碗盛
    assert view.actions and view.sounds == []
    behavior, view = _withMeal(hand=None)
    behavior.serve.sunkClick = lambda: True
    behavior.onPointer(Event(LEFT, Hit("sunk")))
    behavior.onPointer(Event(LEFT, Hit("ladle")))
    assert view.sounds == []
    behavior, view = _withMeal(hand=dict(CARROTS))
    behavior.onPointer(Event(LEFT, Hit("mouth")))                              # 放进锅口：按下不响
    assert view.sounds == []


def testTheMealsContainerInHandScoopsFromTheSpoonHandleTheFloatingPiecesAndTheServedOneToo():
    # cooking_pot.json 里带碰撞盒、手上有东西时还开着的节点：ladle、mouth、item_N、served；onItemClick 对它们一视同仁
    for key, payload in (("mouth", None), ("ladle", None), ("item", 0), ("item", 1), ("served", None)):
        for button, quick in ((LEFT, False), (RIGHT, False), (MIDDLE, True)):
            behavior, view = _withMeal((("minecraft:carrot", 1), ("minecraft:potato", 1)))
            assert behavior.onPointer(Event(button, Hit(key, payload), quick)) is True, (key, button)
            assert view.actions == [("scoop", {"all": quick, "from_inventory": False})], (key, button, quick, view.actions)
            assert view.drops == [] and behavior.serve.scoopedHere == behavior.clock, "盛，不是放料；碗下去的地方敲过水波"


def testWithTheContainerInHandTheKernelPicksAmongAllTheNodesThatHaveABox():
    behavior, view = _withMeal((("minecraft:carrot", 1), ("minecraft:potato", 1)))
    assert sorted(_keys(behavior), key=repr) == sorted([("mouth", None), ("ladle", None), ("item", 0), ("item", 1), ("served", None)], key=repr)
    boxes = dict((box.key, box) for box in behavior.pickables() if box.key != "item")
    assert (boxes["mouth"].lo, boxes["mouth"].hi) == (PotPick.MOUTH[0], PotPick.MOUTH[1]), "锅口还是整口锅"
    lo, hi = behavior.scene.spoon.pickAabb()
    assert boxes["ladle"].lo[1] == lo[1] and boxes["ladle"].hi[1] == hi[1], "勺柄的盒子就是手空着时能抓的那个（跟着勺子走）"
    assert not any(key in ("soup", "sunk") for key, _ in _keys(behavior)), "soup、sunk 只在手空着时开"


def testAnythingButTheMealsContainerStillOffersOnlyTheMouth():
    for hand in ({"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 4}, dict(BOWL, newItemName="minecraft:glass_bottle")):
        behavior, view = _withMeal(hand=hand)
        assert _keys(behavior) == [("mouth", None)], hand
        for key in ("ladle", "served", "item"):
            assert behavior.onPointer(Event(LEFT, Hit(key, 0))) is False and view.actions == [] and view.drops == [], key
    behavior, view = _withMeal()
    view.data = {"vessel": {"newItemName": "minecraft:bowl"}}
    assert _keys(behavior) == [("mouth", None)], "锅里没有煮好的菜：碗只是碗"
    assert behavior.onPointer(Event(LEFT, Hit("ladle"))) is False and view.actions == []


def testWithAnEmptyHandNothingChangedAndTheSpoonStillStirs():
    behavior, view = _withMeal(hand=None)
    assert [key for key, _ in _keys(behavior)] == ["ladle", "item", "served"], "手空着：勺柄、料、盛好的那格（悬着碗 / 能取回时还有 soup / sunk）"
    assert behavior.onPointer(Event(LEFT, Hit("ladle"))) is True and behavior.scene.hand and view.actions == []


def testWithAnEmptyHandTheSoupAndSunkBoxesAreThereOnlyWhileTheirOfferHangs():
    # cooking_pot.json 的 soup（悬着碗时才接点击）和 sunk（能取回沉底的东西时）：手空着才开，soup 先于 sunk（offerBowl / offerTakeBack）
    behavior, view = _withMeal(hand=None)
    serve, level = behavior.serve, behavior.scene.liquid.surfaceY()
    boxes = lambda: dict((box.key, box) for box in behavior.pickables())
    sunk = ((PotPick.SOUP[0][0], level - PotPick.SUNK_HALF, PotPick.SOUP[0][2]), (PotPick.SOUP[1][0], level + PotPick.SUNK_HALF, PotPick.SOUP[1][2]))
    assert "soup" not in boxes() and "sunk" not in boxes(), "什么也没悬着：没有这两个盒子"
    serve.offer, serve.offered = {"block": False}, ("minecraft:bowl", {"pos": (8.0, 9.0, 8.0), "size": 2.0}, None)
    found = boxes()
    assert (found["soup"].lo, found["soup"].hi) == PotPick.SOUP and "sunk" not in found, "悬着碗：soup 盒，盖着整个汤面"
    serve.takesBack = True
    found = boxes()
    assert "soup" in found and "sunk" not in found, "两样都有时 soup 先（elif）：不再开 sunk"
    serve.offer, serve.offered = None, None
    found = boxes()
    assert "soup" not in found and (found["sunk"].lo, found["sunk"].hi) == sunk, "没悬着碗、能取回：sunk 是贴着汤面上下各 0.3 的一层"
    serve.offer = {"block": False}                           # 有位置但没有要悬的东西：soup 不开，轮到 sunk
    found = boxes()
    assert "soup" not in found and "sunk" in found
    serve.offer, serve.offered = {"block": False}, ("minecraft:bowl", {"pos": (8.0, 9.0, 8.0), "size": 2.0}, None)
    for hand in (BOWL, {"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 1}):
        view.hand = hand
        assert not [key for key, _ in _keys(behavior) if key in ("soup", "sunk")], "手上拿着东西：这两个盒子点不到（%r）" % hand


def testTheSoupRingsWhereTheCursorMeetsTheSurfaceNotWhereItHitTheBox():
    # PotBehavior.java:529-531：view.cursorOn(surface)，点哪个节点都一样；点勺柄时盒子上的点在锅外面
    behavior, view = _withMeal()
    rings = []
    behavior.serve.bowlWentIn = rings.append
    surface = behavior.scene.liquid.surfaceY()
    ray = (8.0, 41.0, -21.0, 0.0, -0.6, 0.8)
    on = Geometry.planeAtHeight(ray, surface)
    event = Event(LEFT, Hit("ladle"), ray=ray)
    event.point = (14.2, 15.0, 8.0)
    assert behavior.onPointer(event) is True
    assert rings == [on] and on[1] == surface and event.point not in rings, "液面上的交点"
    rings[:] = []
    event = Event(LEFT, Hit("mouth"))
    assert behavior.onPointer(event) is True and rings == [event.point], "没有射线（触屏点完指针离开了）：盒子上的点"
    rings[:] = []
    assert behavior.onPointer(Event(LEFT, Hit("mouth"), ray=(8.0, 41.0, -21.0, 0.0, 0.0, 1.0))) is True
    assert rings == [(8.0, 9.0, 8.0)], "射线和液面平行（没有交点）：盒子上的点"


def _splashes():
    return [spec for spec in C.world.particles if spec["id"] == "arris_diegesis:splash"]


def testTheBowlThatWentInUnderTheCursorSplashesFourAtSixPixelsPerSecond():
    # PotBehavior.java:535：spawnParticles(SPLASH, 光标落在液面的点, (0, 6, 0), 0.6, 4, 汤色)
    behavior, _view = behaviorOf()
    behavior.serve.bowlWentIn((8.0, 9.0, 8.0))
    found = _splashes()
    assert len(found) == 1 and found[0]["vars"]["variable.count"] == 4.0, [spec["vars"] for spec in found]
    assert (found[0]["vars"]["variable.vx"], found[0]["vars"]["variable.vy"], found[0]["vars"]["variable.vz"]) == (0.0, 6.0, 0.0)
    assert found[0]["vars"]["variable.speed_set"] == 1.0


def testTheOfferedBowlDippedIntoTheSoupSplashesFourAtSixPixelsPerSecond():
    # KitchenMotions.java:639（Dip 浸到的那一刻）：spawnParticles(SPLASH, 落点, (0, 6, 0), 0.6, 4, 汤色)
    behavior, _view = behaviorOf()
    serve = behavior.serve
    serve._dipOffered("minecraft:bowl", {"pos": (8.0, 9.5, 8.0), "scale": 1.0, "size": 2.0}, "arris:pumpkin_soup")
    serve._dipping(0.2, behavior.scene.liquid.surfaceY())               # 过了 DOWN（0.14 秒）：浸到了
    found = _splashes()
    assert len(found) == 1 and found[0]["vars"]["variable.count"] == 4.0, [spec["vars"] for spec in found]
    assert (found[0]["vars"]["variable.vx"], found[0]["vars"]["variable.vy"], found[0]["vars"]["variable.vz"]) == (0.0, 6.0, 0.0)
    assert found[0]["vars"]["variable.speed_set"] == 1.0


# ---------------------------------------------------------------- 触屏长按（onHold）：右键 / Shift 点击的变体，只给和点一下不一样的

HoldMenu = C.load("Compat.Diegesis.HoldMenu")
PotHold = C.load("Compat.Diegesis.PotHold")


def _hold(behavior, key=None, payload=None):
    """手指按在场景里按住不动：前置包在按下那一刻问表现的 onHold，event 和按下收到的是同一种拾取事件（左键）。"""
    return behavior.onHold(Event(LEFT, Hit(key, payload) if key else None, kind="down"))


def testHoldingAStackOfIngredientsOverTheMouthOffersPutOneWhereTheRightClickPlacesJustOne():
    behavior, view = behaviorOf()
    view.hand = dict(CARROTS)
    assert _hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]} and HoldMenu.PUT_ONE == {"label": "放一个", "button": 1, "quick": False}
    assert behavior.onPointer(Event(LEFT, Hit("mouth"))) is True and view.spread.button == LEFT, "点一下是整叠（松手才放）"
    view.spread.cancel()
    assert behavior.onPointer(Event(RIGHT, Hit("mouth"))) is True and view.spread.button == RIGHT, "菜单补的右键：放一个"
    for key in ("ladle", "item", "served", "soup", "sunk", None):
        assert _hold(behavior, key, 0) is None, "锅口以外的地方：手上的料点不进去，没有变体"
    view.hand = dict(CARROTS, count=1)
    assert _hold(behavior, "mouth") is None, "只有一个：放一个就是放整叠"
    view.hand = dict(CARROTS)
    view.fitIndex = None
    assert _hold(behavior, "mouth") is None, "哪一格都放不下：点一下什么也不发，右键也一样"


def testHoldingTheMealsContainerOffersScoopAllOnlyWhenThereIsMoreThanOneServingAndMoreThanOneContainer():
    # PotPick.withStack：点一下盛一份，Shift 盛到没菜或没容器；哪个节点都一样（mouth、ladle、item_N、served）
    behavior, view = _withMeal((("minecraft:carrot", 1), ("minecraft:potato", 1)), hand=dict(BOWL, count=4))
    assert HoldMenu.SCOOP_ALL == {"label": "全部盛出", "button": 0, "quick": True}
    for key, payload in (("mouth", None), ("ladle", None), ("item", 0), ("item", 1), ("served", None)):
        assert _hold(behavior, key, payload) == {"menu": [HoldMenu.SCOOP_ALL]}, key
    for key in ("soup", "sunk", None):
        assert _hold(behavior, key) is None
    behavior.onPointer(Event(LEFT, Hit("mouth")))
    behavior.onPointer(Event(LEFT, Hit("mouth"), True))
    assert [action for action in view.actions if action[0] == "scoop"] == [("scoop", {"all": False, "from_inventory": False}),
                                                                          ("scoop", {"all": True, "from_inventory": False})], "点一下和 Shift 真的不一样"
    view.hand = dict(BOWL)
    assert _hold(behavior, "mouth") is None, "手上只有一个容器：全盛也只是一份"
    view.hand = dict(BOWL, count=4)
    view.data = {"meal": {"newItemName": "arris:pumpkin_soup", "count": 1}, "vessel": {"newItemName": "minecraft:bowl"}}
    assert _hold(behavior, "mouth") is None, "锅里只剩一份"


def testTheMealsContainerOfAnotherKindIsJustAStackToPutIn():
    behavior, view = _withMeal(hand=dict(CARROTS))
    assert _hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}, "手上不是这锅菜的容器：当料，在锅口放一个"
    assert _hold(behavior, "ladle") is None and _hold(behavior, "served") is None


def testEmptyHandOnAFloatingStackOrTheServedStackOffersTheTakeBarForThatSlot():
    behavior, view = _withMeal((("minecraft:carrot", 5), ("minecraft:potato", 1)), hand=None)
    assert _hold(behavior, "item", 0) == {"take": _slot(0), "count": 5}, "点一下整格拿起、右键拿一半：份量从 1 到 5 由手指定"
    assert _hold(behavior, "item", 1) is None, "只有一个：没有份量可取，按下立刻拿起"
    behavior.scene.apply(C.look((("minecraft:carrot", 5), ("minecraft:potato", 1)), served=C.item("arris:pumpkin_soup", 3), meal=C.item("arris:pumpkin_soup", 3)))
    assert _hold(behavior, "served") == {"take": Txn.stationTarget(Rules.GROUP_SERVED, 0), "count": 3}
    behavior.scene.apply(C.look((("minecraft:carrot", 5),), served=C.item("arris:pumpkin_soup", 1), meal=C.item("arris:pumpkin_soup", 1)))
    assert _hold(behavior, "served") is None


def testTheSpoonHandleTheSunkThingsAndNothingAreNeverHeldSoTheStrokeStartsAtOnce():
    behavior, view = _withMeal((("minecraft:carrot", 5),), hand=None)
    for key in ("ladle", "sunk", "mouth", None):
        assert _hold(behavior, key) is None, key
    assert behavior.onPointer(Event(LEFT, Hit("ladle"))) is True and behavior.gesture.stroking, "握勺柄照旧按下就开始"


def testEmptyHandOnTheHungBowlOffersScoopAllWhenTheSoupAndTheInventoryHaveMoreThanOne():
    behavior, view = _withMeal(hand=None)
    real = PotHold.PotOffer.carried
    try:
        PotHold.PotOffer.carried = lambda name: 3 if name == "minecraft:bowl" else 0
        assert _hold(behavior, "soup") == {"menu": [HoldMenu.SCOOP_ALL]}, "悬着碗点汤：点一下盛一份，Shift 全盛（PotOffer.soupClick）"
        PotHold.PotOffer.carried = lambda name: 1
        assert _hold(behavior, "soup") is None, "背包里只有一个容器"
        PotHold.PotOffer.carried = lambda name: 3
        view.data = {"meal": {"newItemName": "arris:pumpkin_soup", "count": 1}, "vessel": {"newItemName": "minecraft:bowl"}}
        assert _hold(behavior, "soup") is None, "锅里只剩一份"
        view.data = {}
        assert _hold(behavior, "soup") is None, "没有煮好的菜"
    finally:
        PotHold.PotOffer.carried = real


def testNoSceneOrNoLookMeansNoMenu():
    behavior, view = _withMeal((("minecraft:carrot", 5),), hand=None)
    behavior.scene.look = None
    assert _hold(behavior, "item", 0) is None
    behavior.scene = None
    assert _hold(behavior, "item", 0) is None


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
