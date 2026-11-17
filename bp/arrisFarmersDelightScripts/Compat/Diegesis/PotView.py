# -*- coding: utf-8 -*-
"""PotView - 厨锅站点里本人的那一层：握勺柄搅、点料取回、拿着料点锅口放、盛出，和右侧的徽章（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 onEvent 和只给本人看的部分。锅里的画面（汤面、漂着的料、勺子、气泡、声音）
是谁都看得见的世界场景（PotScene.py），这里只把本人的手交给它，并照 JE 的规矩把点击变成动作：
- 机位、飞入照 HoD 的 scenes/cooking_pot.json：相机 (8, 41, -21) 看 (8, 6.5, 8)，视野 30 度，0.4 秒，窗口窄时保住左右；
- 勺子只能抓露在锅沿上面的柄（场景文件里 ladle 的碰撞盒，锅里那段杆不算）：手空着、光标在柄上时整根勺子描一圈亮边
  （Diegesis 的 hover outline）；左右键都能握（Stroke 不看键）：按住拖动搅，一按一松不到 0.3 秒勺子留在手里随光标搅，
  再按一下（哪个键、按在哪里都一样）放下。勺尖由场景按 HoD 的手感算，每 0.12 秒报一次服务端（stir，世界朝向，-1..1 = 勺尖偏移 / 2.3 像素）；
- 锅身描一圈同样的亮边（pot.setOutlined(offering)，判定在 PotOffer.offering）：手上的东西放得进、光标在锅口上；拿着盛这道菜的
  容器、光标在汤上；悬着碗；
- 底部托盘（前置包按 usable 列出背包里用得上的料和盛菜的容器）点一叠就拿到手上；拿着料点锅 = 放进第一格放得下的
  （左键整叠、右键一个），拿着盛这道菜的容器点锅口、勺柄、漂着的料、盛好的那格 = 盛一份（Shift 全盛，哪个键都行；能点的盒子在 PotPick.py）；
- 手空着：点漂着的料 = 那一格整叠拿到手上（右键一半、Shift 直接进背包，双击 = 锅里和背包里同一种的都收到手上，
  和原版容器一样）；汤煮好了、背包里有容器，光标在汤上会悬出那只半透明的容器，点一下盛一份；汤里有倒进去 / 打进去 / 化掉的
  东西（牛奶、鸡蛋、糖）时光标在汤面上悬出要取回的那样，点一下取回最后放的。拿在手上的东西点托盘的格子放回背包。
- 触屏（view.input，规矩在前置包的 Shared/Input.py）：没有悬停，一下点完指针就离开（onLeave），悬着的东西收起；点在汤面上
  没做事的那一下让容器 / 要取回的那样悬出来，再点一下才做；刚盛过、取回过的留在老地方等着接着点。勺子一按一松不留在手里。
徽章和悬停提示在 PotHud.py，悬着的容器和它浸进汤里的动作在 PotOffer.py。坐标：站点像素随玩家所在一侧转，场景用锅自己的坐标（随方块朝向），
两边经世界坐标换算。
"""
from . import BookSources, PotPick, PotScenes
from .PotHud import PotHud
from .PotOffer import PotOffer
from ...Client.Engine import clientApi, compFactory, levelId
from ...Shared.Rules import HandsOnOptions as Options
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotDrift, PotSpoonMotion

CAMERA = {"pos": (8.0, 41.0, -21.0), "target": (8.0, 6.5, 8.0), "fov": 30.0, "keepWidth": 16.0 / 9.0}
FLIGHT_SECONDS = 0.4
SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / ControlSpec / SlotRules）
SLOT_SIZE = 3.2                                    # 锅里的料画多大（cooking_pot.json 槽节点的 size）：手上的东西到了锅口上也是它
START_SPREAD, START_BOTTOM = 0.05, 0.97             # 一次放进好几件：从屏幕底边一字排开飞进来（FromPlayer）
DOUBLE_CLICK = 0.25                                 # 双击：拿起之后这么久之内再按一下左键（FocusInput.DOUBLE_CLICK_MS）


class PotViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA
    flightSeconds = FLIGHT_SECONDS
    chrome = "java"
    workPlane, carryLift = 10.0, 2.5         # 手上的东西起始是 Diegesis 的缺省大小 4.5，光标到了锅口上变成锅里东西的大小（见 onPointer）

    def __init__(self, view):
        super(PotViewMixin, self).__init__(view)
        self.scene = None
        self.gesture = PotSpoonMotion.SpoonGesture()
        self.hud = PotHud(self)
        self.serve = PotOffer(self)
        self.clock = 0.0
        self.hover, self.ray = (None, None), None       # 光标底下是什么、光标的射线（站点空间）
        self.picked = None                    # 刚从哪一格拿起来的：(目标, 什么时候)，紧跟着再按一下就是双击

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        return Rules.usable(Rules.keyOf(item))

    def mayDrop(self, group, index, item):
        return group == Rules.GROUP_INGREDIENTS and Rules.mayPlace(item)

    def onOpen(self):
        scene = self.scene = PotScenes.ensure(self.view.dimensionId, self.view.pos)
        if scene is not None:
            view = self.view
            scene.onSend = self._send
            scene.startsOf = self._starts
            scene.cursorOn = self.serve.cursorOn
            # 站点像素和锅自己的坐标互换。演着的手把它带到关站之后接着演完（PotHands.going），所以这里直接拿 scene / view，不经 self.scene（关站时清掉）
            scene.viewFrame = (lambda x, y, z: view.toStation(*scene.world(x, y, z)), lambda x, y, z: scene.local(*view.toWorld(x, y, z)),
                               view.toWorld)
        BookSources.attach(self.view, "pot")

    def onClose(self):
        self.gesture.reset()
        self.hud.close()
        self.serve.close()
        scene, self.scene = self.scene, None
        if scene is not None:
            scene.hand, scene.aim, scene.onSend, scene.startsOf, scene.cursorOn, scene.viewFrame = False, None, None, None, None, None
            scene.model.glow(False)

    def onState(self, changes):
        BookSources.refresh(self.view)

    def onEffect(self, name, data):
        if self.scene is not None and name in ("scooped", "served"):
            self.scene.event(name, data, name == "scooped" and self.serve.scooped())     # 开着站点的人不收旁观者那条广播，这里补给场景
        self.hud.effect(name, data)

    def frame(self, dt):
        self.clock += dt
        if self.scene is not None:
            self.serve.frame(dt)
            self.hud.frame(dt)
            self.scene.model.glow(self.hover[0] == "ladle" and self.view.hand is None and not self.scene.hand, self.serve.offering())

    # ---------------------------------------------------------------- 坐标

    def toLocal(self, point):
        """站点像素 -> 锅自己的坐标（像素）。"""
        return self.scene.local(*self.view.toWorld(point[0], point[1], point[2]))

    def toStation(self, x, y, z):
        """锅自己的坐标 -> 站点像素。"""
        return self.view.toStation(*self.scene.world(x, y, z))

    def pickables(self):
        return PotPick.boxes(self)

    # ---------------------------------------------------------------- 指针

    def onPointer(self, event):
        scene = self.scene
        if scene is None or scene.look is None:
            return False
        key = event.hit.node.key if event.hit is not None else None
        payload = event.hit.node.payload if event.hit is not None else None
        if event.kind == "move":
            self.hover, self.ray = (key, payload), event.ray
            if key == "mouth" and self.view.hand is not None and not PotPick.holdsVessel(self.view):    # 盛这锅菜的容器不是往里放的：锅口不收它，不变
                resize = getattr(self.view, "carryAs", None)        # 光标到了放东西的地方上：手上的东西变成那里的东西的大小，离开不变回去
                if resize is not None:                              # （FocusInput.updateCarry 的 zoneItemSize；老版本的前置包没有这个接口）
                    resize(SLOT_SIZE)
            self._aim(event.ray)
            return False
        if event.kind == "up":
            if not self.gesture.stroking:
                return False
            if not self.gesture.up(self.clock) or self.view.input == self.api.TOUCH:
                self.gesture.reset()          # 触屏没有跟着走的光标：一按一松也放下
                scene.hand = False            # 拖完了：放下勺子；一按一松的"点"则留在手里
            return True
        if self.gesture.heldByClick:          # 勺子留在手里：这一按不管哪个键、按在哪里，只是把它放下（FocusInput.press 开头）
            self.gesture.down(self.clock)
            scene.hand = False
            return True
        if self.gesture.stroking:             # 按着勺子拖的时候另一个键又按下：什么也不做（FocusInput.press 的 gesture != null）
            return True
        picked, self.picked = self.picked, None
        if picked is not None and event.button == 0 and not event.quick and self.clock - picked[1] < DOUBLE_CLICK:
            # 双击：锅里和背包里同一种的都收到手上（FocusInput.clickItem 的 PICKUP_ALL）；手上的东西服务端可能还没发回来，以"刚拿起过"为准
            self.view.click(picked[0], 0, self.api.PICKUP_ALL)
            return True
        if self.view.hand is not None:
            return self._withStack(event, key)
        if key in ("item", "served"):
            target = (self.api.stationTarget(Rules.GROUP_INGREDIENTS, int(payload)) if key == "item"
                      else self.api.stationTarget(Rules.GROUP_SERVED, 0))
            self.view.click(target, event.button, self.api.QUICK_MOVE if event.quick else self.api.PICKUP)
            if event.button == 0 and not event.quick:
                self.picked = (target, self.clock)
            return True
        if key == "sunk":
            return self.serve.sunkClick()     # 取回不看是哪个键（PotBehavior.java:502-505）
        if key == "ladle":                    # 握勺子也不看键：Stroke 左右键都起（FocusInput.java:412-413），START / END 不看按键（PotBehavior.java:466-488）
            self.gesture.down(self.clock)
            scene.hand = True
            self._aim(event.ray)
            return True
        if event.button != 0:
            return False                      # 只有手空着点汤盛出认左键（PotBehavior.java:491 的 click.button() == 0）
        if key == "soup":
            return self.serve.soupClick(event)
        return False

    def busy(self):
        """勺子还在手里（按着拖，或点了一下留着）：内核据此不让光标停在屏幕边上就飞去相邻的站点，也不让托盘接下一次按下——
        那一下只是把勺子放下（JE 的 FocusInput.isBusy 是"有笔画"：mayGoOver 要它为假，press 开头先结束留在手里的笔画）。"""
        return self.gesture.stroking

    def onLeave(self):
        """触屏：一下点完、手指抬起，没有悬着的光标——悬停才有的东西收起；刚盛过 / 取回过的留着，下一只还悬在老地方。"""
        if self.scene is not None and self.serve.dip is None:
            self.hover, self.ray, self.scene.aim = (None, None), None, None

    def _withStack(self, event, key):
        """手上拿着东西点锅：盛这道菜的容器 = 盛一份，点到锅口、勺柄、漂着的料、盛好的那格哪个都行（带碰撞盒的节点），Shift 全盛，
        哪个键都行（PotBehavior.onItemClick 不看节点和 button）；别的 = 放进第一格放得下的（左键整叠、右键一个，只有锅口接）。"""
        if PotPick.holdsVessel(self.view) and key in PotPick.SCOOPS:
            self.view.sendAction("scoop", {"all": bool(event.quick), "from_inventory": False})
            self.serve.bowlWentIn(PotPick.surfacePoint(self, event))
            return True
        if key != "mouth":
            return False                      # 右键点在别处：内核把手上的放回背包
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
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。
    配置里关了厨锅站点（cooking_pot）什么也不登记、返回 None，和服务端的 PotLogic.register 同一个条件。"""
    if not Options.cookingPot():
        return None
    behaviorClass = type("CookingPotBehavior", (PotViewMixin, api.StationBehavior), {"api": api})
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.POT_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit),
                         canOpen=PotScenes.opensStation)
    return behaviorClass
