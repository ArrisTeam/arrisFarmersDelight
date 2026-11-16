# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点里本人的点击（Compat/Diegesis/PotView.onPointer）：按哪个键能做什么照 JE（假视图、假前置包 Api，场景用 potclient 的假引擎）。"""
from __future__ import print_function

import potclient as C

PotView = C.load("Compat.Diegesis.PotView")
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
Rules = C.load("Shared.Rules.PotStation")
POS = C.POS
LEFT, RIGHT, MIDDLE = 0, 1, 2


class Node(object):
    def __init__(self, key, payload=None):
        self.key, self.payload = key, payload


class Hit(object):
    def __init__(self, key, payload=None):
        self.node = Node(key, payload)


class Event(object):
    def __init__(self, button=LEFT, hit=None, quick=False):
        self.kind, self.button, self.hit, self.quick = "down", button, hit, quick
        self.point, self.ray = (8.0, 9.0, 8.0), None


class Api(object):
    TOUCH = "touch"


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


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
