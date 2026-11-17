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
    def __init__(self, button=LEFT, hit=None, quick=False, ray=None):
        self.kind, self.button, self.hit, self.quick = "down", button, hit, quick
        self.point, self.ray = (8.0, 9.0, 8.0), ray


class Box(object):
    """前置包的 Api.box 给的拾取盒：只记下是什么、在哪。"""

    def __init__(self, key, lo, hi, payload=None):
        self.key, self.lo, self.hi, self.payload = key, tuple(lo), tuple(hi), payload


class Api(object):
    TOUCH = "touch"
    Geometry = Geometry

    @staticmethod
    def box(key, lo, hi, payload=None):
        return Box(key, lo, hi, payload)


class FakeView(object):
    """前置包给表现类的 view：只记下发出去的动作和放料的调用。"""

    def __init__(self):
        self.hand = None
        self.data = {}
        self.input = "mouse"
        self.dimensionId = 0
        self.pos = POS
        self.actions, self.drops = [], []

    def sendAction(self, name, payload):
        self.actions.append((name, payload))

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


def testTheSpoonAndTheSoupStillTakeOnlyTheLeftButton():
    behavior, _view = behaviorOf()
    scooped = []
    behavior.serve.soupClick = lambda event: scooped.append(event.button) or True
    assert behavior.onPointer(Event(RIGHT, Hit("soup"))) is False and scooped == []
    assert behavior.onPointer(Event(LEFT, Hit("soup"))) is True and scooped == [LEFT]
    assert behavior.onPointer(Event(RIGHT, Hit("ladle"))) is False and not behavior.scene.hand
    assert behavior.onPointer(Event(LEFT, Hit("ladle"))) is True and behavior.scene.hand


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
