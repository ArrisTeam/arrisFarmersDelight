# -*- coding: utf-8 -*-
# runner: both
"""站点关上（或打开）的时候，锅里正在演的手不挪地方（Compat/Diegesis/PotHands.py 的 going、PotView.onOpen / onClose）。

JE：PotBehavior.onClose（451-457）只 refresh(view, true)，going[i] 不动，手在场景像素里接着演完。手的姿态是开始那一刻按当时的坐标算的：
开着站点的人用他的站点坐标（站点朝着他站的那一侧），旁观的人用锅自己的朝向；两者差 90 / 180 / 270 度时，要是中途换了换算，剩下的帧
就把站点坐标当锅坐标摆（或反过来），整只手转到另一边。每只手带着它开始时的换算演完。
"""
from __future__ import print_function

import random

import dgtest
import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
PotView = C.load("Compat.Diegesis.PotView")
BrothColors = C.load("Shared.Data.BrothColors")
Geometry = dgtest.load("Shared.Geometry")        # 前置包的几何：站点像素 <-> 世界
POS = C.POS
DT = 1.0 / 60.0
YAWS = (0, 90, 180, 270)                         # 站点朝哪（北 0、东 90、南 180、西 270），锅自己的朝向是其中一个，别的三个和它不一样
THINGS = ("minecraft:egg", "minecraft:milk_bucket", "minecraft:sugar")        # 磕蛋、倒奶、抖糖


def setup():
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    return Scenes.ensure(0, POS)


def stationFrame(scene, yaw):
    """PotView.onOpen 交给场景的换算：(锅自己的坐标 -> 站点像素, 站点像素 -> 锅自己的坐标, 站点像素 -> 世界)，站点朝 yaw。"""
    bx, by, bz = scene.pos
    toWorld = lambda x, y, z: Geometry.stationPointToWorld(yaw, x, y, z, bx, by, bz)
    toStation = lambda x, y, z: Geometry.worldPointToStation(yaw, *(tuple(scene.world(x, y, z)) + (bx, by, bz)))
    toPot = lambda x, y, z: scene.local(*toWorld(x, y, z))
    return toStation, toPot, toWorld


def _watch(name, yaw, change=None, at=0.5, seconds=3.0):
    """锅里放进一件 name（会沉的），站点朝 yaw 的人（None：旁观的人）看着手演；到 at 秒时 change(scene) 一下。
    返回每一帧手端着的东西（和蛋液）在世界里摆在哪：[((节点, 位置), ...) 或 None]。"""
    random.seed(11)
    scene = setup()
    scene.viewFrame = stationFrame(scene, yaw) if yaw is not None else None
    return _play(scene, name, change, at, seconds)


def _play(scene, name, change, at, seconds):
    scene.apply(C.look([("minecraft:carrot", 1)]))
    for _ in range(12):
        scene.frame(DT, True)
    scene.apply(C.look([("minecraft:carrot", 1), (name, 1)], sunk=[1]))
    frames, changed = [], False
    for index in range(int(seconds / DT)):
        if change is not None and not changed and index * DT >= at:
            changed = True
            change(scene)
        scene.frame(DT, True)
        entry = scene.hands.going.get(1)
        frames.append(None if entry is None else tuple(sorted((node, world.drops[prop[0]]["pivot"]) for node, prop in entry["props"].items())))
    return frames


def _close(scene):
    scene.viewFrame = None              # PotView.onClose 清掉的就是它


class RotatedView(object):
    """前置包给表现类的 view：站点朝 yaw，只有 PotView 开关站点和演手会碰到的那几个。"""

    def __init__(self, yaw):
        self.yaw, self.dimensionId, self.pos = yaw, 0, POS
        self.hand, self.data, self.input = None, {}, "mouse"

    def toWorld(self, x, y, z):
        return Geometry.stationPointToWorld(self.yaw, x, y, z, POS[0], POS[1], POS[2])

    def toStation(self, wx, wy, wz):
        return Geometry.worldPointToStation(self.yaw, wx, wy, wz, POS[0], POS[1], POS[2])

    def plate(self, *args):
        pass

    def tooltip(self, *args):
        pass


class Base(object):
    def __init__(self, view):
        self.view = view


class Api(object):
    TOUCH = "touch"
    Geometry = Geometry


def _watchThroughTheView(name, yaw, close):
    """同 _watch，但开关站点走真的 PotViewMixin.onOpen / onClose（它给场景的换算、关站时清掉的东西）。"""
    random.seed(11)
    scene = setup()
    behavior = type("TestBehavior", (PotView.PotViewMixin, Base), {"api": Api})(RotatedView(yaw))
    behavior.onOpen()
    assert behavior.scene is scene and scene.viewFrame is not None
    frames = _play(scene, name, (lambda _scene: behavior.onClose()) if close else None, 0.5, 3.0)
    assert not close or (behavior.scene is None and scene.viewFrame is None)
    return frames


def testClosingTheStationWhileAHandIsAtWorkLeavesTheHandWhereItWas():
    for yaw in YAWS:
        for name in THINGS:
            kept = _watch(name, yaw)
            closed = _watch(name, yaw, change=_close)
            assert any(frame for frame in kept), "手演了起来（%s）" % name
            assert closed == kept, "站点朝 %d、%s：关站之后手挪了地方" % (yaw, name)


def testTheStationViewsOwnCloseLeavesTheHandsWhereTheyWereToo():
    # 手演到关站之后还要把站点像素换回锅的坐标（涟漪、水花）：换算不能经关站时清掉的 PotView.scene
    for yaw in YAWS:
        for name in THINGS:
            assert _watchThroughTheView(name, yaw, True) == _watchThroughTheView(name, yaw, False), (yaw, name)


def testOpeningTheStationWhileABystandersHandIsAtWorkLeavesItWhereItWas():
    for yaw in YAWS:
        for name in THINGS:
            kept = _watch(name, None)
            opened = _watch(name, None, change=lambda scene, yaw=yaw: setattr(scene, "viewFrame", stationFrame(scene, yaw)))
            assert opened == kept, "站点朝 %d、%s：开站之后手挪了地方" % (yaw, name)


def testAHandThatStartsAfterTheStationClosedIsDrawnInThePotsOwnFrame():
    # 手开始那一刻没有站点：和旁观的人看到的一样，按锅自己的朝向演
    for yaw in YAWS:
        assert _watch("minecraft:egg", yaw, change=_close, at=0.0) == _watch("minecraft:egg", None), yaw


def testAHandThatStartsWhileTheStationIsOpenIsDrawnInTheStationsFrame():
    for yaw in YAWS:
        opened = _watch("minecraft:egg", None, change=lambda scene, yaw=yaw: setattr(scene, "viewFrame", stationFrame(scene, yaw)), at=0.0)
        assert opened == _watch("minecraft:egg", yaw), yaw


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
