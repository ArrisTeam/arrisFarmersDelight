# -*- coding: utf-8 -*-
"""PotHands - 不浮在汤面上的料是怎么进锅的：一只手端过来倒（奶桶、奶瓶、蜂蜜）、在锅沿磕开（蛋）、抖进去（糖、可可这类粉）（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 goesIn / wentIn（812-848 行）和 KitchenMotions 的 Pour / Crack / Shake。每一刻的姿态和
那一刻该发生的事在 Shared/Rules/HandsOn/PotServeHands.py / PotServePour.py（纯计算，逐条照 Java），这里只管画：
- 手里的东西是一件立着的客户端掉落物：正面朝镜头、往后仰 16 度、在贴图平面里倾（倒、抖）；倒空了换成空容器（桶、玻璃瓶）；
  蛋磕开之后蛋液是一件平躺的煎蛋；
- 流出来的液体：JE 是一股连着的水柱，这里每帧从瓶口朝落点撒几滴染了色的水滴；粉末是往下掉的小粒，蛋壳是溅开的碎屑；
- 涟漪、水花、气泡、声音照事件放。
动作在"场景像素"里算（JE 的场景朝着开站的人）：开着站点的人那边是他的站点坐标（PotView 给的 scene.viewFrame），旁观的人按锅自己的朝向看。
"""
import random

from . import PotFx
from .PotSceneFx import play
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Data import PotSunk, Remainders
from ...Shared.Data.BrothColors import MainColors, PouredColors
from ...Shared.Rules import ItemPose
from ...Shared.Rules.HandsOn import PotDrift, PotLiquid, PotServeHands
from ...Shared.Rules.HandsOn.PotServeMath import ITEM_DRAWN, LEAN

RIM_TOP = 10.0              # 锅沿的高度（像素）：蛋磕在这里
EGG_INSIDE = "arris:fried_egg"      # 磕开之后落进汤里的蛋液画成什么
STREAM_TIME = 0.16          # 水滴从瓶口到汤面大约走这么久（定初速）
STREAM_RIPPLES = 0.14       # 流着的时候每隔这么久在落点起一圈水波
STREAM_RIPPLE = 0.1
GRAIN_SCALE, BIT_SCALE = 0.45, 0.6
_CRACKED = frozenset(name for name, _aux in PotSunk.CRACKED)
_POURED = frozenset(name for name, _aux in PotSunk.POURED)


def kindOf(name):
    """这件沉下去的料怎么进锅：cracked 磕开、poured 倒、其余抖（PotBehavior.goesIn 的分支）。"""
    return "cracked" if name in _CRACKED else ("poured" if name in _POURED else "shaken")


class PotHands(object):
    def __init__(self, scene):
        self.scene = scene
        self.going = {}                      # 槽 -> {"motion", "kind", "name", "props": {节点: [掉落物 id, 物品名]}, "rings"}

    # ---------------------------------------------------------------- 开始 / 推进

    def start(self, slot):
        """第 slot 格进来了一件不浮着的料：让一只手把它带到汤上方。"""
        scene = self.scene
        item = scene.look.items[slot] if scene.look is not None else None
        if not item or slot in self.going:
            return
        name = item["newItemName"]
        kind = kindOf(name)
        start = self._frame()[0](*self._startPoint(slot))
        color = 0xFF000000 | (PouredColors.get(name) or MainColors.get(name) or PotLiquid.FALLBACK)
        motion = PotServeHands.goesIn(kind, slot, start, scene.liquid.surfaceY(), RIM_TOP, random.random, name.endswith("_bucket"), color)
        self.going[slot] = {"motion": motion, "kind": kind, "name": name, "props": {}, "rings": 0.0}

    def _startPoint(self, slot):
        """手从哪来（锅自己的坐标；PotBehavior.java:786-790、859）：一次放好几件的，轮到的那一件从各自的出发点来（屏幕底边一字排开）；
        放一件的，开着站点的人那一下手从光标落在液面上方那一层的点来，没有光标（触屏点完）是锅口正上方；旁观的人也是锅口正上方。"""
        scene = self.scene
        height = scene.liquid.surfaceY() + PotDrift.ARRIVE_FROM
        staged = scene.drift.arrivals.takeStart(slot)
        if staged is not None:
            return (8.0 + staged[0], height, 8.0 + staged[1])
        cursor = scene.cursorOn(height) if scene.cursorOn is not None else None
        return (cursor[0], height, cursor[1]) if cursor is not None else (8.0, height, 8.0)

    def _frame(self):
        """(锅坐标 -> 场景坐标, 场景坐标 -> 锅坐标, 场景坐标 -> 世界)：开着站点的人用他的站点坐标，别人用锅自己的。"""
        frame = self.scene.viewFrame
        if frame is not None:
            return frame
        return (lambda x, y, z: (x, y, z)), (lambda x, y, z: (x, y, z)), self.scene.world

    def step(self, dt, near=True):
        scene = self.scene
        surface = scene.liquid.surfaceY()
        for slot in list(self.going):
            entry = self.going[slot]
            motion = entry["motion"]
            poses, events = motion.step(dt, surface)
            if entry["kind"] != "cracked":
                poses = {"hand": poses}
            self._place(entry, "hand", poses.get("hand") or poses.get("egg"), entry["name"], ITEM_DRAWN)
            if "inside" in poses:
                self._place(entry, "inside", poses["inside"], EGG_INSIDE, PotServeHands.EGG_INSIDE, lying=True)
            for event in events:
                self._event(entry, event, dt, near)
            if motion.done:
                for event in PotServeHands.wentIn(entry["kind"], scene.liquid.bubbleColor):
                    self._event(entry, event, dt, near)
                self._drop(entry)
                del self.going[slot]
                scene.drift.handDone(slot)        # 手忙着时又放进来的：再来一只

    def clear(self):
        for entry in self.going.values():
            self._drop(entry)
        self.going = {}

    # ---------------------------------------------------------------- 画

    def _axes(self):
        """场景的 x / y / z 轴在世界里的方向（3x3，列是轴）。"""
        world = self._frame()[2]
        origin, alongX, alongZ = world(8.0, 0.0, 8.0), world(9.0, 0.0, 8.0), world(8.0, 0.0, 9.0)
        x = [(alongX[i] - origin[i]) * 16.0 for i in range(3)]
        z = [(alongZ[i] - origin[i]) * 16.0 for i in range(3)]
        return [[x[0], 0.0, z[0]], [x[1], 1.0, z[1]], [x[2], 0.0, z[2]]]

    def _turned(self, vector):
        """场景里的一个方向换到世界里。"""
        axes = self._axes()
        return tuple(sum(axes[row][column] * vector[column] for column in range(3)) for row in range(3))

    def _place(self, entry, node, pose, name, span, lying=False):
        """把一个节点（手里的东西 / 蛋液）摆成 pose；不可见就收掉。倒空了的容器换成它的空壳。span：这个节点缩放 1 时有多大（像素）——
        手里的东西是物品的显示（ITEM_DRAWN），蛋液是按自己的大小搭的形状（Crack 的 insideSize）。"""
        scene = self.scene
        if pose is not None and pose.get("item") == "empty":
            name = Remainders.potRemainderOf(name)
        prop = entry["props"].get(node)
        if pose is None or not pose.get("visible") or pose.get("scale", 0.0) <= 0.01 or not name:
            if prop is not None:
                scene.removeProp(prop[0])
                del entry["props"][node]
            return
        where = self._frame()[2](*pose["pos"])
        if prop is not None and prop[1] != name:
            scene.removeProp(prop[0])
            prop = None
        if prop is None:
            one = {"newItemName": name, "newAuxValue": 0, "count": 1}
            entityId = addDropItem(one, scene.dimensionId, where)
            if not entityId:
                return
            prop = entry["props"][node] = [entityId, name]
        size = pose["scale"] * span / ItemPose.ITEM_SPAN
        if lying:
            matrix = ItemPose.framed(self._axes(), ItemPose.lyingMatrix(pose["rot"][1]))
        else:
            matrix = ItemPose.standingMatrix(self._axes(), LEAN, pose["rot"][2])
        pivot = ItemPose.pivotFor(where, matrix, size)
        compFactory.CreateItem(levelId).SetDropItemTransform(prop[0], pivot, ItemPose.engineEuler(matrix), size)

    def _drop(self, entry):
        for prop in entry["props"].values():
            self.scene.removeProp(prop[0])
        entry["props"] = {}

    def _event(self, entry, event, dt, near):
        scene, kind = self.scene, event["type"]
        _toFrame, toPot, toWorld = self._frame()
        if kind == "ripple":
            x, _y, z = toPot(event["x"], scene.liquid.surfaceY(), event["z"])
            scene.model.ripple(x, z, event["strength"])
        elif kind == "stream":
            entry["rings"] -= dt
            if entry["rings"] <= 0.0:
                entry["rings"] = STREAM_RIPPLES
                x, _y, z = toPot(*event["to"])
                scene.model.ripple(x, z, STREAM_RIPPLE)
            if near:
                start, end = event["from"], event["to"]
                speed = self._turned(tuple((end[i] - start[i]) / STREAM_TIME for i in range(3)))
                PotFx.particle(PotFx.DROPLET, toWorld(*start), color=event["color"] & 0xFFFFFF,
                               count=1 + int(event["strength"] * 2.0 + random.random()), velocity=speed)
        elif not near:
            return
        elif kind == "sound":
            play(event["name"], scene.world(8.0, scene.liquid.surfaceY(), 8.0), event["volume"], event["pitch"])
        elif kind in ("droplets", "grains", "dust"):
            scale = GRAIN_SCALE if kind == "grains" else (BIT_SCALE if kind == "dust" else None)
            PotFx.particle(PotFx.DROPLET, toWorld(*event["pos"]), color=event["color"] & 0xFFFFFF, count=event["count"],
                           scale=scale, velocity=self._turned(event["rise"]))
        elif kind == "splash":
            PotFx.particle(PotFx.SPLASH, toWorld(*event["pos"]), color=event["color"] & 0xFFFFFF, count=event["count"])
        elif kind == "bubbles":
            scene.fx.bubbles(event["count"])
