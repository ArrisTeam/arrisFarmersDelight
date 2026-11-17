# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点里本人的点击（Compat/Diegesis/PotView.onPointer）：按哪个键能做什么照 JE（假视图、假前置包 Api，场景用 potclient 的假引擎）。"""
from __future__ import print_function

import dgtest
import potclient as C

PotView = C.load("Compat.Diegesis.PotView")
PotPick = C.load("Compat.Diegesis.PotPick")
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
Rules = C.load("Shared.Rules.PotStation")
Geometry = dgtest.load("Shared.Geometry")        # 前置包的几何：光标射线和液面的交点
Txn = dgtest.load("Shared.ActionTxn")            # 前置包的动作目标 / 点击种类
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
    def __init__(self, button=LEFT, hit=None, quick=False, ray=None, kind="down"):
        self.kind, self.button, self.hit, self.quick = kind, button, hit, quick
        self.point, self.ray = (8.0, 9.0, 8.0), ray


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
    """前置包给表现类的 view：只记下发出去的动作、内核点击和放料的调用。"""

    def __init__(self):
        self.hand = None
        self.data = {}
        self.input = "mouse"
        self.dimensionId = 0
        self.pos = POS
        self.actions, self.drops, self.clicks = [], [], []
        self.plateHover = False

    def sendAction(self, name, payload):
        self.actions.append((name, payload))

    def click(self, target, button=0, kind="PICKUP"):
        self.clicks.append((target, button, kind))

    def plate(self, model):
        pass

    def tooltip(self, lines):
        pass

    def dropInto(self, group, button):
        self.drops.append((group, button))
        return 0

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


def testAnythingElseInHandStillGoesIntoThePotWithTheButtonGiven():
    behavior, view = behaviorOf()
    view.hand = {"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 4}
    view.data = {"meal": {"newItemName": "arris:pumpkin_soup", "count": 3}, "vessel": {"newItemName": "minecraft:bowl"}}
    assert behavior.onPointer(Event(RIGHT, Hit("mouth"))) is True
    assert view.actions == [] and view.drops == [(Rules.GROUP_INGREDIENTS, RIGHT)]


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


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
