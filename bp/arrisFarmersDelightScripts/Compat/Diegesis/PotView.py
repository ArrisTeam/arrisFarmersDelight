# -*- coding: utf-8 -*-
"""PotView - 厨锅站点的客户端表现：俯看锅里、漂着的料、跟手的勺子、上方的菜、底部的物品栏抽屉（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的简化版（基岩版没有液面、拖尾和粒子，只用客户端掉落物）：
- 在锅里按住拖动 = 搅拌；短按一下 = 勺子留在手里跟着鼠标转，再点一下放下。勺尖每 0.12 秒报一次服务端（stir）；
- 短按漂着的料 = 取回那种料（take）；煮好后锅边浮着那道菜，点它 = 盛出（scoop）；点底部抽屉的格子 = 把快捷栏那叠放进锅（add）；
- 顶部徽章（前置包的 view.badge）显示在煮的菜、星星和进度，底部一行提示说下一步做什么。
锅身 12×10×12 像素，汤面是 y = 10 的顶面，开口约 8 像素见方。站点坐标见前置包（16 = 1 格，玩家在北面）。
勺尖在线上用世界朝向（以方块中心为原点、除以 SPOON_REACH），从不同方向打开的人看到的勺子在同一处。
勺子的手感（跟手、带着料转、报服务端的节奏）在 PotSpoon.py。开站期间把厨锅模型自带的木勺藏起来（只在本客户端，
variable.mod_ladle_hidden），手里的勺子换成跟手的道具；关站时还原。
"""
import math

from . import BookSources
from .PotSpoon import SPOON_REACH, SpoonHand
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import PotStation as Rules

CAMERA = {"pos": (8.0, 27.0, -1.5), "target": (8.0, 10.0, 7.5), "fov": 50.0}
SOUP_Y = 10.0
MIDDLE = 8.0
DRIFT = 2.2                       # 料漂在离锅心这么远的一圈上
FOOD_SCALE = 0.42                 # 料的贴图约 3.4 像素见方
FOOD_LIFT = 0.3
FOOD_HALF = 1.6                   # 料的命中盒半宽
SPOON_ITEM = {"newItemName": "minecraft:wooden_shovel", "newAuxValue": 0, "count": 1}
SPOON_SCALE = 0.8
SPOON_ROLL = 135.0                # 竖立、柄朝上、勺头朝下（同砧板的刀，实机标定）
SPOON_TIP = 4.0 * SPOON_SCALE * math.sqrt(2.0)
SPOON_DIP = 1.2                   # 搅的时候勺头没进汤面多深
SPOON_LIFT = 1.5                  # 靠着时抬出汤面多高
LADLE_HIDDEN = "variable.mod_ladle_hidden"   # 厨锅模型里 ladle 骨骼的开关（rp/entity/cooking_pot.json）
DISH_AT = (15.0, 13.0, 9.0)       # 煮好的菜浮在东边把手上方（画面左侧）；远端上方会和顶部徽章叠在一起（实机）
DISH_SCALE = 0.7
CLICK_SECONDS = 0.3               # 比这短、几乎没挪的按一下算"点"
CLICK_TRAVEL = 0.6
HINT_SECONDS = 0.25
FLASH_SECONDS = 2.5
SOUP_BOX = ((3.5, 8.0, 3.5), (12.5, 10.0, 12.5))
HINTS = {
    "not_food": "这个不能下锅",
    "full": "锅里放不下了",
    "need_vessel": "背包里没有盛菜的容器",
    "missing": "背包里的料凑不齐这道菜",
    "pot_busy": "锅里有这道菜用不上的料：先点锅里的料取回",
    "no_recipe": "",
}


def _one(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": 1}


class PotViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA

    def __init__(self, view):
        super(PotViewMixin, self).__init__(view)
        self.foods, self.foodKeys = [], None
        self.dish, self.dishKey, self.spoon = None, None, None
        self.hand = SpoonHand()
        self.stroking = self.sticky = False
        self.pending, self.pressedAt = None, 0.0
        self.clock = self.hintLeft = 0.0
        self.flash, self.shown = None, None

    # ---------------------------------------------------------------- 钩子

    def pickables(self):
        boxes = []
        for slot, prop in self.foods:
            x, _, z = prop.center
            boxes.append(self.api.box("slot", (x - FOOD_HALF, SOUP_Y, z - FOOD_HALF),
                                      (x + FOOD_HALF, SOUP_Y + 1.5, z + FOOD_HALF), payload=slot))
        if self.dish is not None and self.view.data.get("meals"):
            half = 4.0 * DISH_SCALE
            boxes.append(self.api.box("dish", (DISH_AT[0] - half, DISH_AT[1] - 1.0, DISH_AT[2] - half),
                                      (DISH_AT[0] + half, DISH_AT[1] + 1.0, DISH_AT[2] + half)))
        boxes.append(self.api.box("soup", SOUP_BOX[0], SOUP_BOX[1]))
        return boxes

    def onOpen(self):
        self._hideLadle(True)
        self._rebuild()
        BookSources.attach(self.view, "pot")

    def onClose(self):
        self._hideLadle(False)

    def onState(self, changes):
        if changes.data:
            self._rebuild()
            BookSources.refresh(self.view)

    def onEffect(self, name, data):
        if name == "drawer":
            self.view.drawer(data.get("items") or [])
        elif name == "served":
            grade, bonus = int(data.get("grade") or 0), int(data.get("bonus") or 0)
            extra = "，多送 %d 份" % bonus if bonus > 0 else ""
            self._flash("出锅了：%d 星%s" % (grade, extra))
        elif name == "scooped":
            self._flash("盛好了")
        elif name == "hint":
            text = HINTS.get(data.get("key"), "")
            vessel = self.view.data.get("vesselName")
            self._flash(text + ("（%s）" % vessel if data.get("key") == "need_vessel" and vessel else ""))

    def onDrawer(self, index):
        self.view.sendAction("add", {"slot": int(index)})

    def onPointer(self, event):
        key = event.hit.node.key if event.hit is not None else None
        if event.kind == "down":
            if self.sticky:
                self.sticky = self.stroking = False
            elif key == "dish":
                self.view.sendAction("scoop")
            elif key in ("slot", "soup"):
                self.pending = event.hit.node.payload if key == "slot" else None
                self.stroking, self.pressedAt = True, self.clock
                self.hand.press()
                self._aim(event.ray)
        elif event.kind == "move":
            if self.stroking:
                self._aim(event.ray)
        elif event.kind == "up" and self.stroking and not self.sticky:
            quick = self.clock - self.pressedAt < CLICK_SECONDS and self.hand.travel < CLICK_TRAVEL
            if quick and self.pending is not None:
                self.view.sendAction("take", {"slot": int(self.pending)})
                self.stroking = False
            elif quick:
                self.sticky = True
            else:
                self.stroking = False
            self.pending = None

    def frame(self, dt):
        self.clock += dt
        data = self.view.data
        synced = self._fromWire(data.get("spoon")) if data.get("stirring") else None
        if self.hand.step(dt, self.stroking, bool(data.get("stirring")), synced, bool(data.get("heated"))):
            x, z = self._toWire(self.hand.tip)
            self.view.sendAction("stir", {"x": x, "z": z, "at": round(self.clock, 3)})
        self._place()
        self.hintLeft -= dt
        if self.hintLeft <= 0.0:
            self.hintLeft = HINT_SECONDS
            self._showHint()
            self._hideLadle(True)        # 方块实体在客户端重建（区块重载、刚进世界）时 initialize 会把它清回 0

    # ---------------------------------------------------------------- 勺子

    def _aim(self, ray):
        point = self.api.Geometry.planeAtHeight(ray, SOUP_Y) if ray is not None else None
        if point is not None:
            self.hand.aim(point[0] - MIDDLE, point[2] - MIDDLE)

    def _toWire(self, tip):
        wx, _, wz = self.view.toWorld(MIDDLE + tip[0], SOUP_Y, MIDDLE + tip[1])
        px, _, pz = self.view.pos
        return round((wx - px - 0.5) * 16.0 / SPOON_REACH, 3), round((wz - pz - 0.5) * 16.0 / SPOON_REACH, 3)

    def _fromWire(self, spoon):
        if not isinstance(spoon, (list, tuple)) or len(spoon) != 2:
            return None
        px, py, pz = self.view.pos
        sx, _, sz = self.view.toStation(px + 0.5 + spoon[0] * SPOON_REACH / 16.0, py + SOUP_Y / 16.0,
                                        pz + 0.5 + spoon[1] * SPOON_REACH / 16.0)
        return (sx - MIDDLE, sz - MIDDLE)

    # ---------------------------------------------------------------- 画

    def _rebuild(self):
        """锅里的料、上方的菜变了就换道具；勺子只建一次。"""
        data, props = self.view.data, self.view.props
        inputs = data.get("inputs") or []
        keys = [(slot, Rules.keyOf(item)) for slot, item in enumerate(inputs) if Rules.keyOf(item)]
        if keys != self.foodKeys:
            for _, prop in self.foods:
                props.remove(prop)
            self.foods = [(slot, props.item(_one(inputs[slot]), (MIDDLE, SOUP_Y + FOOD_LIFT, MIDDLE), flat=True,
                                            scale=FOOD_SCALE)) for slot, _ in keys]
            self.foodKeys = keys
        meal = data.get("meal") if data.get("meals") else None     # 浮在锅上方的菜只在有得盛时出现（在煮的菜在徽章上）
        dishKey = Rules.keyOf(meal) if meal else None
        if dishKey != self.dishKey:
            if self.dish is not None:
                props.remove(self.dish)
            self.dish = props.item(_one(meal), DISH_AT, flat=True, scale=DISH_SCALE) if dishKey else None
            self.dishKey = dishKey
        if self.spoon is None:
            self.spoon = props.item(SPOON_ITEM, self._spoonCenter(), flat=False, facing=(0.0, -1.0), roll=SPOON_ROLL,
                                    scale=SPOON_SCALE)
        self._place()
        self.hintLeft = 0.0

    def _spoonCenter(self):
        tip = self.hand.tip
        return (MIDDLE + tip[0], SOUP_Y - SPOON_DIP + SPOON_TIP + self.hand.lift * SPOON_LIFT, MIDDLE + tip[1])

    def _place(self):
        count = len(self.foods)
        for index, (slot, prop) in enumerate(self.foods):
            angle = self.hand.turn + 2.0 * math.pi * index / max(1, count)
            radius = DRIFT if count > 1 else 0.9
            bob = 0.15 * math.sin(2.2 * self.clock + index * 1.7)
            prop.move(center=(MIDDLE + math.cos(angle) * radius, SOUP_Y + FOOD_LIFT + bob, MIDDLE + math.sin(angle) * radius),
                      along=(-math.sin(angle), math.cos(angle)))
        if self.spoon is not None:
            self.spoon.move(center=self._spoonCenter())
        if self.dish is not None:
            self.dish.move(center=(DISH_AT[0], DISH_AT[1] + 0.3 * math.sin(1.6 * self.clock), DISH_AT[2]))

    def _hideLadle(self, hidden):
        compFactory.CreateBlockInfo(levelId).SetBlockEntityMolangValue(tuple(self.view.pos), LADLE_HIDDEN,
                                                                       1.0 if hidden else 0.0)

    def _flash(self, text):
        self.flash = (text, self.clock + FLASH_SECONDS)
        self.hintLeft = 0.0

    def _showHint(self):
        flashing = self.flash is not None and self.clock < self.flash[1]
        text = self.flash[0] if flashing else Rules.statusText(self.view.data)
        if text != self.shown:
            self.shown = text
            self.view.hint(text)
        self.view.badge(Rules.badgeOf(self.view.data))


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记。"""
    behaviorClass = type("CookingPotBehavior", (PotViewMixin, api.StationBehavior), {"api": api})
    api.registerBehavior(Rules.STATION_ID, Rules.POT_BLOCKS, behaviorClass)
    return behaviorClass
