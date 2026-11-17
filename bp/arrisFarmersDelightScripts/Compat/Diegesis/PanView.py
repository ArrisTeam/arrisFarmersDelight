# -*- coding: utf-8 -*-
"""PanView - 煎锅站点里本人的那一层：抓锅柄颠锅、点食物、拿着东西点锅放进去、底部托盘（客户端）

对应 Hands-On Delight：client/SkilletBehavior.java 的 onEvent / stroked / onItemClick 和 scenes/skillet.json（机位、碰撞盒、work_plane、托盘）。
锅里的画面（食物怎么落进来、颠起来翻面、油星热气、锅柄描边、声音）是谁都看得见的世界场景（PanScene.py），这里只把本人的手交给它，
并照 JE 的规矩把点击变成动作：
- 机位照场景文件：相机 (8, 40, 50) 看 (8, 1, 14)、视野 34 度，在锅柄那一侧（锅柄朝方块的朝向，不管开站的人站在哪边：Orientation.BLOCK）；
  0.4 秒飞入，窗口窄时保住左右两边；chrome = java：没有提示行、没有抽屉，托盘代替；
- 锅柄（handle 的碰撞盒，strokes）：按住 = 锅拎起来一点，往上猛提到每秒 30 像素以上就颠（力度到 110 像素每秒满），点一下（不到 0.35 秒）轻轻颠一下；
  光标放上去、或食物等着翻面时锅柄描一圈亮边（hover outline）；
- 锅里的食物（food 的碰撞盒）：点一下（左键）颠一下，熟了、或点右键：全拿回背包；
- 手上拿着东西（托盘里拿起一叠，或开站这一下就拿着）点锅的任何地方（mouth / food / handle 的碰撞盒）：放进去，左键整叠、右键一个，
  放不进的那一件弹开（服务端判，回 refused）；托盘里空手 Shift 点（前置包 onInventoryShiftClick 钩子）发 place {from: 背包格号}，整叠进锅（一批为止），
  放不进同样弹开；前置包没有这个钩子的老版本走内核自己的 QUICK_MOVE；
- 托盘只列煎得了的东西（usable）；食谱书照旧挂（BookSources），只看。
坐标：HoD 的场景坐标（锅柄朝 +z）经 PanModelMath 换到世界，再经 view.toStation 到站点像素，所以随方块朝向转。
"""
import math

from . import BookSources, PanScenes, TouchFeel
from ...Client.Engine import clientApi, compFactory, levelId
from ...Shared.Rules import HandsOnOptions as Options
from ...Shared.Rules import PanModelMath as Math
from ...Shared.Rules import PanStation as Rules

CAMERA = dict(Math.SCENE_CAMERA, keepWidth=16.0 / 9.0)
FLIGHT_SECONDS = 0.4
SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / SlotRules）
START_SPREAD, START_BOTTOM = 0.05, 0.97                # 一次放进好几件：从屏幕底边一字排开飞进来（FromPlayer）
MIN_API_VERSION = 2                                    # 托盘、光标栈随状态同步


class PanViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    flightSeconds = FLIGHT_SECONDS
    chrome = "java"
    workPlane, carryLift, carrySize = 4.0, 2.5, 4.5      # skillet.json 的 work_plane；carrySize 是 Diegesis 的缺省（没有槽节点就不改）

    def __init__(self, view):
        super(PanViewMixin, self).__init__(view)
        block = compFactory.CreateBlockInfo(levelId).GetBlock(view.pos)
        self.facing = Math.facingOf(block[1] if block else 0)
        self.scene = None
        self.hover = None
        self.ray = None                      # 光标此刻的射线（站点空间）
        self.stroking = False
        self.strokeButton = 0
        self._cam = None

    # ---------------------------------------------------------------- 机位与坐标

    @property
    def camera(self):
        """场景文件的机位（锅柄那一侧）换成这次开站的站点空间（站点空间随玩家站的那一侧转，所以要经世界算）。"""
        yaw = self.view.yaw
        if self._cam is None or self._cam[0] != yaw:
            pos, target = (self._toStation(CAMERA[key]) for key in ("pos", "target"))
            self._cam = (yaw, {"pos": pos, "target": target, "fov": CAMERA["fov"], "keepWidth": CAMERA["keepWidth"]})
        return self._cam[1]

    def _toStation(self, point):
        """场景坐标 -> 站点像素。"""
        return self.view.toStation(*Math.worldPoint(self.facing, self.view.pos, point))

    def _toScene(self, point):
        """站点像素 -> 场景坐标。"""
        return Math.scenePoint(self.facing, self.view.pos, *self.view.toWorld(point[0], point[1], point[2]))

    def _box(self, key, box):
        a, b = self._toStation(box[0]), self._toStation(box[1])
        return self.api.box(key, tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3)))

    def _screenOn(self, x, y, height):
        """屏幕上一点（占屏的几分之几）落在场景里高度 height 的水平面上的哪一点（场景坐标）；算不出 None。"""
        size = compFactory.CreateGame(levelId).GetScreenSize()
        ray = self.view.rayAt((size[0] * x, size[1] * y)) if size else None
        point = self.api.Geometry.planeAtHeight(ray, height) if ray is not None else None
        return self._toScene(point) if point is not None else None

    def _startsOf(self, height, index, count):
        """一次放进 count 件：第 index 件从屏幕底边的哪一点起飞，相对屏幕中心那一点的偏移（FromPlayer.offset）。"""
        start = self._screenOn(0.5 + (index - (count - 1) / 2.0) * START_SPREAD, START_BOTTOM, height)
        middle = self._screenOn(0.5, 0.5, height)
        return (0.0, 0.0) if start is None or middle is None else (start[0] - middle[0], start[2] - middle[2])

    def _cursorAt(self, height):
        point = self.api.Geometry.planeAtHeight(self.ray, height) if self.ray is not None else None
        return self._toScene(point) if point is not None else None

    def _strokeNow(self):
        """抓着锅柄时光标此刻在竖直平面上的高度（场景每帧读它，和场景的钟同一个帧间隔）；没抓着 None。"""
        return self._strokeY(self.ray) if self.stroking and self.ray is not None else None

    def _strokeY(self, ray):
        """光标射线和"过锅柄原点、正对镜头的竖直平面"的交点的高度（Diegesis 的 strokePoint）；平行时 None。"""
        cam = self.camera
        nx, nz = cam["target"][0] - cam["pos"][0], cam["target"][2] - cam["pos"][2]
        length = math.hypot(nx, nz)
        if length < 1.0e-9:
            return None
        nx, nz = nx / length, nz / length
        ox, oy, oz, dx, dy, dz = ray
        denom = dx * nx + dz * nz
        if abs(denom) < 1.0e-6:
            return None
        base = self._toStation(Math.SCENE_PAN)
        return oy + ((base[0] - ox) * nx + (base[2] - oz) * nz) / denom * dy

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        return Rules.usable(item.get("newItemName"))

    def pickables(self):
        boxes = [self._box("handle", Math.HANDLE_BOX), self._box("food", Math.FOOD_BOX)]
        if self.view.hand is not None:
            boxes.insert(1, self._box("mouth", Math.MOUTH_BOX))          # 拿着东西时锅口也认（drop zone）
        return boxes

    def onInventoryShiftClick(self, slot, item):
        """空手 Shift 点托盘里背包槽 slot 的那一叠（SkilletBehavior.onInventoryShiftClick）：有营火配方的发 place {from}，返回真 = 自己处理了，
        内核不再发 QUICK_MOVE；没有配方的返回假。"""
        if not item or not Rules.canFry(item.get("newItemName")):
            return False
        self.view.sendAction("place", {"from": slot})
        return True

    def onOpen(self):
        self.scene = PanScenes.ensure(self.view.dimensionId, self.view.pos)
        if self.scene is not None:
            self.scene.show.focused = True
            self.scene.startsOf, self.scene.cursorAt, self.scene.strokeAt = self._startsOf, self._cursorAt, self._strokeNow
            self.scene.feel = lambda kind: TouchFeel.buzz(self.view, kind)
        BookSources.attach(self.view, "pan")

    def onClose(self):
        scene, self.scene = self.scene, None
        if scene is not None:
            scene.show.close()
            scene.show.focused, scene.hovered, scene.offering = False, False, False
            scene.startsOf = scene.cursorAt = scene.strokeAt = scene.feel = None
        self.stroking = False

    def onState(self, changes):
        BookSources.refresh(self.view)

    def frame(self, dt):
        scene = self.scene
        if scene is None:
            return
        scene.hovered = self.stroking or (self.hover == "handle" and self.view.hand is None)
        scene.offering = self._offering()
        self._flush()

    def _offering(self):
        """锅身描不描边：手上的东西放得进锅、光标在锅上（照厨锅的 pot.setOutlined；触屏没有悬停，拿着就描）。"""
        if self.view.hand is None or self.view.fits(Rules.GROUP_PAN) is None:
            return False
        return self.hover is not None or self.view.input == self.api.TOUCH

    def onLeave(self):
        """触屏：一下点完、手指抬起，没有悬着的光标。"""
        self.hover = None

    def _flush(self):
        """场景里本人的手要告诉服务端的动作（颠、取）发出去。"""
        for name, data in self.scene.show.takeActions():
            self.view.sendAction(name, data)
            TouchFeel.buzz(self.view, TouchFeel.FLIP if name == "toss" else TouchFeel.PICK)      # 颠 = 翻面、取 = 拿起：点下去这一刻就震（不等服务端）

    # ---------------------------------------------------------------- 指针

    def onPointer(self, event):
        scene = self.scene
        if scene is None:
            return False
        key = event.hit.node.key if event.hit is not None else None
        if event.kind == "move":
            self.hover, self.ray = key, event.ray
            return False
        if event.kind == "up":
            if not self.stroking or event.button != self.strokeButton:
                return False
            self.stroking = False
            scene.show.strokeEnd()
            self._flush()
            return True
        self.ray = event.ray
        if self.stroking:                              # 上一次按住没等到抬起（松手在窗口外）：先收尾
            self.stroking = False
            scene.show.strokeEnd()
            self._flush()
        if self.view.hand is not None:
            return self._withStack(event, key)
        if key == "handle" and not event.quick:       # Shift 点穿过锅柄（strokes）去够后面的
            y = self._strokeY(event.ray) if event.ray is not None else None
            self.stroking, self.strokeButton = True, event.button
            scene.show.strokeStart(0.0 if y is None else y)
            return True
        if key in ("handle", "food"):
            scene.show.clickFood(event.button)
            self._flush()
            return True
        return False

    def _withStack(self, event, key):
        """手上拿着东西点锅的任何一处：放进去（onItemClick）；点在别处不处理，右键由内核把手上的放回背包。"""
        if key is None:
            return False
        self.view.sendAction("place", {"one": event.button == 1})
        return True


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。
    配置里关了煎锅站点（skillet）什么也不登记、返回 None，和服务端的 PanLogic.register 同一个条件。"""
    if not Options.skillet() or getattr(api, "API_VERSION", 0) < MIN_API_VERSION:
        return None
    behaviorClass = type("SkilletBehavior", (PanViewMixin, api.StationBehavior), {"api": api})
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.PAN_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit))
    return behaviorClass
