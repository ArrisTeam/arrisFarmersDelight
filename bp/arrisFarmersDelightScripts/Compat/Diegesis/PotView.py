# -*- coding: utf-8 -*-
"""PotView - 厨锅站点里本人的那一层：握勺柄搅、点料取回、拿着料点锅口放、盛出，和右侧的徽章（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 onEvent 和只给本人看的部分。锅里的画面（汤面、漂着的料、勺子、气泡、声音）
是谁都看得见的世界场景（PotScene.py），这里只把本人的手交给它，并照 JE 的规矩把点击变成动作：
- 机位、飞入照 HoD 的 scenes/cooking_pot.json：相机 (8, 41, -21) 看 (8, 6.5, 8)，视野 30 度，0.4 秒，窗口窄时保住左右；
- 勺子只能抓露在锅沿上面的柄（场景文件里 ladle 的碰撞盒，锅里那段杆不算）：手空着、光标在柄上时整根勺子描一圈亮边
  （Diegesis 的 hover outline）；按住拖动搅，一按一松不到 0.3 秒勺子留在手里随光标搅，再按一下放下。勺尖由场景按 HoD 的
  手感算，每 0.12 秒报一次服务端（stir，世界朝向，-1..1 = 勺尖偏移 / 2.3 像素）；
- 底部托盘（前置包按 usable 列出背包里用得上的料和盛菜的容器）点一叠就拿到手上；拿着料点锅 = 放进第一格放得下的
  （左键整叠、右键一个），拿着盛这道菜的容器点锅 = 盛一份（Shift 全盛）；
- 手空着：点漂着的料 = 那一格拿到手上（右键一半、Shift 直接进背包）；汤煮好了、背包里有容器，光标在汤上会悬出那只容器，
  点一下盛一份；汤里只有化掉的东西（牛奶、鸡蛋、糖）时点汤 = 取回最后放的那样。
徽章、悬停提示、悬着的容器和它浸进汤里的动作在 PotHud.py。坐标：站点像素随玩家所在一侧转，场景用锅自己的坐标（随方块朝向），
两边经世界坐标换算。
"""
from . import BookSources, PotScenes
from .PotHud import PotHud
from ...Client.Engine import clientApi, compFactory, levelId
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotDrift, PotDriftExtras, PotSpoonMotion

CAMERA = {"pos": (8.0, 41.0, -21.0), "target": (8.0, 6.5, 8.0), "fov": 30.0, "keepWidth": 16.0 / 9.0}
FLIGHT_SECONDS = 0.4
SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / ControlSpec / SlotRules）
MOUTH = ((2.0, 6.0, 2.0), (14.0, 14.0, 14.0))       # 锅口：拿着东西时整口锅都是它
SOUP = ((4.0, 2.0, 4.0), (12.0, 9.0, 12.0))
ITEM_HALF, ITEM_TALL = 1.6, 0.3                     # 漂着的料的命中盒：左右各 1.6，上下各 0.3
START_SPREAD, START_BOTTOM = 0.05, 0.97             # 一次放进好几件：从屏幕底边一字排开飞进来（FromPlayer）


class PotViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA
    flightSeconds = FLIGHT_SECONDS
    chrome = "java"
    workPlane, carryLift, carrySize = 10.0, 2.5, 3.2

    def __init__(self, view):
        super(PotViewMixin, self).__init__(view)
        self.scene = None
        self.gesture = PotSpoonMotion.SpoonGesture()
        self.hud = PotHud(self)
        self.clock = 0.0
        self.hover = (None, None)

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        return Rules.usable(Rules.keyOf(item))

    def mayDrop(self, group, index, item):
        return group == Rules.GROUP_INGREDIENTS and Rules.mayPlace(item)

    def onOpen(self):
        self.scene = PotScenes.ensure(self.view.dimensionId, self.view.pos)
        if self.scene is not None:
            self.scene.onSend = self._send
            self.scene.startsOf = self._starts
        BookSources.attach(self.view, "pot")

    def onClose(self):
        self.gesture.reset()
        self.hud.close()
        scene, self.scene = self.scene, None
        if scene is not None:
            scene.hand, scene.aim, scene.onSend, scene.startsOf = False, None, None, None
            scene.model.glow(False)

    def onState(self, changes):
        BookSources.refresh(self.view)

    def onEffect(self, name, data):
        if self.scene is not None and name in ("scooped", "served"):
            self.scene.event(name, data)      # 开着站点的人不收旁观者那条广播，这里补给场景
        self.hud.effect(name, data)

    def frame(self, dt):
        self.clock += dt
        if self.scene is not None:
            self.hud.frame(dt)
            self.scene.model.glow(self.hover[0] == "ladle" and self.view.hand is None and not self.scene.hand)

    # ---------------------------------------------------------------- 坐标

    def toLocal(self, point):
        """站点像素 -> 锅自己的坐标（像素）。"""
        return self.scene.local(*self.view.toWorld(point[0], point[1], point[2]))

    def toStation(self, x, y, z):
        """锅自己的坐标 -> 站点像素。"""
        return self.view.toStation(*self.scene.world(x, y, z))

    def _box(self, key, lo, hi, payload=None):
        a, b = self.toStation(*lo), self.toStation(*hi)
        return self.api.box(key, tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3)), payload=payload)

    def pickables(self):
        scene = self.scene
        if scene is None or scene.look is None:
            return []
        if self.view.hand is not None:
            return [self.api.box("mouth", MOUTH[0], MOUTH[1])]
        lo, hi = scene.spoon.pickAabb()
        boxes = [self._box("ladle", (8.0 + lo[0], lo[1], 8.0 + lo[2]), (8.0 + hi[0], hi[1], 8.0 + hi[2]))]
        drift, look = scene.drift, scene.look
        for slot in range(len(look.items)):
            if look.items[slot] is not None and drift.visible[slot] and not drift.waiting[slot]:
                x, y, z = drift.x[slot], drift.y[slot], drift.z[slot]
                boxes.append(self._box("item", (x - ITEM_HALF, y - ITEM_TALL, z - ITEM_HALF),
                                       (x + ITEM_HALF, y + ITEM_TALL, z + ITEM_HALF), slot))
        if look.served is not None:
            x, y, z = PotDriftExtras.servedAt(scene.liquid.surfaceY())
            boxes.append(self.api.box("served", (x - ITEM_HALF, y - ITEM_TALL, z - ITEM_HALF),
                                      (x + ITEM_HALF, y + ITEM_TALL, z + ITEM_HALF)))
        boxes.append(self.api.box("soup", SOUP[0], SOUP[1]))
        return boxes

    # ---------------------------------------------------------------- 指针

    def onPointer(self, event):
        scene = self.scene
        if scene is None or scene.look is None:
            return False
        key = event.hit.node.key if event.hit is not None else None
        payload = event.hit.node.payload if event.hit is not None else None
        if event.kind == "move":
            self.hover = (key, payload)
            self._aim(event.ray)
            return False
        if event.kind == "up":
            if not self.gesture.stroking:
                return False
            if not self.gesture.up(self.clock):
                scene.hand = False            # 拖完了：放下勺子；一按一松的"点"则留在手里
            return True
        if self.gesture.heldByClick:          # 勺子留在手里：这一按把它放下
            self.gesture.down(self.clock)
            scene.hand = False
            return True
        if self.view.hand is not None:
            return self._withStack(event, key)
        if key in ("item", "served"):
            target = (self.api.stationTarget(Rules.GROUP_INGREDIENTS, int(payload)) if key == "item"
                      else self.api.stationTarget(Rules.GROUP_SERVED, 0))
            self.view.click(target, event.button, self.api.QUICK_MOVE if event.quick else self.api.PICKUP)
            return True
        if event.button != 0:
            return False
        if key == "ladle":
            self.gesture.down(self.clock)
            scene.hand = True
            self._aim(event.ray)
            return True
        if key == "soup":
            return self.hud.soupClick(event)
        return False

    def _withStack(self, event, key):
        """手上拿着东西点锅：盛这道菜的容器 = 盛一份（Shift 全盛）；别的 = 放进第一格放得下的（左键整叠、右键一个）。"""
        if key != "mouth":
            return False                      # 右键点在别处：内核把手上的放回背包
        meal = self.view.data.get("meal")
        vessel = self.view.data.get("vessel") or {}
        if meal and vessel.get("newItemName") and self.view.hand.get("newItemName") == vessel["newItemName"]:
            if event.button == 0:
                self.view.sendAction("scoop", {"all": bool(event.quick), "from_inventory": False})
                self.hud.bowlWentIn(event.point)
            return True
        return self.view.dropInto(Rules.GROUP_INGREDIENTS, event.button) is not None

    def _aim(self, ray):
        """光标落在液面上的哪一点（锅自己的坐标，相对锅心）：握着勺子时勺尖往那去。"""
        scene = self.scene
        point = self.api.Geometry.planeAtHeight(ray, scene.liquid.surfaceY()) if ray is not None else None
        if point is None:
            scene.aim = None
            return None
        x, _, z = self.toLocal(point)
        scene.aim = (x - 8.0, z - 8.0)
        return scene.aim

    def _send(self, x, z, at):
        self.view.sendAction("stir", {"x": round(x, 3), "z": round(z, 3), "at": round(at, 3)})

    def _starts(self, count):
        """一次放进 count 件：各从屏幕底边的一点出发（投到液面上方 9 像素的平面上），返回相对锅心的 (x, z) 列表。"""
        size = compFactory.CreateGame(levelId).GetScreenSize()
        height = self.scene.liquid.surfaceY() + PotDrift.ARRIVE_FROM
        starts = []
        for index in range(count):
            screen = (size[0] * (0.5 + (index - (count - 1) / 2.0) * START_SPREAD), size[1] * START_BOTTOM) if size else None
            ray = self.view.rayAt(screen) if screen else None
            point = self.api.Geometry.planeAtHeight(ray, height) if ray is not None else None
            if point is None:
                starts.append(None)
                continue
            x, _, z = self.toLocal(point)
            starts.append((x - 8.0, z - 8.0))
        return starts


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。"""
    behaviorClass = type("CookingPotBehavior", (PotViewMixin, api.StationBehavior), {"api": api})
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.POT_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit),
                         canOpen=PotScenes.opensStation)
    return behaviorClass
