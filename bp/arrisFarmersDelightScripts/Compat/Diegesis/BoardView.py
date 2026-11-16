# -*- coding: utf-8 -*-
"""BoardView - 切菜板站点的客户端表现：机位、刀口虚线、悬在下一刀上的刀、点击即切（客户端）

对应 Hands-On Delight：刀吸附到下一条虚线，点一下落刀。食材本身由农夫乐事的展示实体画（所有人都看得见），
这里只画给使用者自己看的东西：刀口虚线（下一刀是金色）和悬着的刀（落刀时往下一扎）。
点击板面：板空着 -> place；板上有东西 -> use（服务端判断是切、取回，还是摆盘的做成 / 拿走）。坐标是站点像素（16 = 1 格，玩家在北面）。
摆盘（HoD 的 dishes on the board）：底部抽屉列出快捷栏里现在能放上砧板的，点一格 = lay；板上的层由 Client/BlockItems 给所有人画。
"""
import math

from ...Shared.Rules import CuttingStation as Rules
from ...Shared.Rules import DishStation
from ...Shared.Rules.HandsOn import Cutting

CAMERA = {"pos": (8.0, 21.0, -3.0), "target": (8.0, 1.0, 7.5), "fov": 55.0}
FOOD = (3.0, 13.0, 3.0, 13.0)       # 食材在板上的范围 x0, x1, z0, z1（z1 是离玩家远的一端）
MARK_Y = 2.0                        # 虚线贴在食材上面
KNIFE_SCALE = 0.8                   # 刀的贴图 6.4 像素见方
KNIFE_ROLL = 135.0                  # 竖立的刀在贴图平面内顺时针转 135 度：刀柄朝上、刀尖朝下（实机标定）
KNIFE_TIP = 3.2 * math.sqrt(2.0)    # 刀尖在视觉中心正下方多远（贴图对角线的一半）
KNIFE_HOVER = 9.0                   # 刀的视觉中心悬多高：刀尖离食材约 2.5 像素
CHOP_SECONDS = 0.22
BOARD_BOX = ((1.0, 0.0, 1.0), (15.0, 4.0, 15.0))
HINTS = {
    "empty": "点击砧板放上手里的食材，或点下方物品栏：能切的切、能打底的摆盘   潜行右键 = 原来的玩法",
    "cut": "点击食材：切第 %d / %d 刀",
    "no_tool": "背包里没有合适的刀具：点击取回",
    "take": "点击取回",
    "only_food": "只有能切的食材、或能打底的（面包、碗、签子……）才能放上砧板",
    "no_layer": "这个放不上去：不是哪道菜的下一层",
}


def markLine(style, spot, angle):
    """第 i 刀的虚线两端（站点像素）。spot 是离远端的比例；angle 随布局：横切是 -1..1（占最大斜度），楔形是弧度。"""
    x0, x1, z0, z1 = FOOD
    half = (x1 - x0) * 0.5
    cx, cz = (x0 + x1) * 0.5, (z0 + z1) * 0.5
    if style == Cutting.STYLE_WEDGES:
        dx, dz = math.cos(angle) * half, math.sin(angle) * half
        return (cx - dx, MARK_Y, cz - dz), (cx + dx, MARK_Y, cz + dz)
    z = z1 - spot * (z1 - z0)
    lean = math.tan(angle * Cutting.MOST_LEAN) * half if style == Cutting.STYLE_ACROSS else 0.0
    return (x0, MARK_Y, z - lean), (x1, MARK_Y, z + lean)


class BoardViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA

    def __init__(self, view):
        super(BoardViewMixin, self).__init__(view)
        self.strokes = []
        self.knife = None
        self.toolName = ""
        self.chopLeft = 0.0

    # ---------------------------------------------------------------- 钩子

    def pickables(self):
        return [self.api.box("board", BOARD_BOX[0], BOARD_BOX[1])]

    def onOpen(self):
        self._redraw()

    def onState(self, changes):
        if changes.data:
            self._redraw()

    def onEffect(self, name, data):
        if name == "tool":
            self.toolName = data.get("item") or ""
            self._redraw()
        elif name == "chop":
            self.chopLeft = CHOP_SECONDS
        elif name == "hint":
            self.view.hint(HINTS.get(data.get("key"), ""))
        elif name == "drawer":
            self.view.drawer(data.get("items") or [])
        elif name == "plated":
            self.view.hint("做好了：点一下砧板拿走")

    def onDrawer(self, index):
        self.view.sendAction("lay", {"slot": int(index)})

    def onPointer(self, event):
        if event.kind != "down" or event.hit is None:
            return
        data = self.view.data
        if data.get("layers") or data.get("dish"):
            self.view.sendAction("use", {"mark": 0})
        elif not data.get("item"):
            self.view.sendAction("place")
        else:
            self.view.sendAction("use", {"mark": int(data.get("marks") or 0)})

    def frame(self, dt):
        if self.knife is None or self.chopLeft <= 0.0:
            return
        self.chopLeft = max(0.0, self.chopLeft - dt)
        center = self._knifeCenter()
        if center is not None:
            dip = math.sin(math.pi * (1.0 - self.chopLeft / CHOP_SECONDS)) * (KNIFE_HOVER - KNIFE_TIP - MARK_Y)
            self.knife.move(center=(center[0], center[1] - dip, center[2]))

    # ---------------------------------------------------------------- 画

    def _redraw(self):
        props = self.view.props
        for prop in self.strokes:
            props.remove(prop)
        self.strokes = []
        if self.knife is not None:
            props.remove(self.knife)
            self.knife = None
        data = self.view.data
        item, plan, done = data.get("item"), int(data.get("plan") or 0), int(data.get("marks") or 0)
        spots, angles = data.get("spots") or [], data.get("angles") or []
        for index in range(done, min(plan, len(spots), len(angles))):
            a, b = markLine(data.get("style"), spots[index], angles[index])
            self.strokes.append(props.line(a, b, hot=(index == done)))
        center = self._knifeCenter()
        if center is not None and self.toolName:
            knifeItem = {"newItemName": self.toolName, "newAuxValue": 0, "count": 1}
            self.knife = props.item(knifeItem, center, flat=False, facing=(0.0, -1.0), roll=KNIFE_ROLL, scale=KNIFE_SCALE)
        self.view.hint(self._hintText(item, plan, done))

    def _knifeCenter(self):
        data = self.view.data
        done, spots, angles = int(data.get("marks") or 0), data.get("spots") or [], data.get("angles") or []
        if not data.get("item") or done >= min(len(spots), len(angles)):
            return None
        a, b = markLine(data.get("style"), spots[done], angles[done])
        return ((a[0] + b[0]) * 0.5, KNIFE_HOVER, (a[2] + b[2]) * 0.5)

    def _hintText(self, item, plan, done):
        data = self.view.data
        if data.get("layers") or data.get("dish"):
            return DishStation.statusText(data, lambda name: data.get("readyName") or name)
        if not item:
            return HINTS["empty"]
        if not self.view.data.get("cuttable"):
            return HINTS["take"]
        if not self.toolName:
            return HINTS["no_tool"]
        return HINTS["cut"] % (min(done + 1, plan), plan)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记。"""
    behaviorClass = type("CuttingBoardBehavior", (BoardViewMixin, api.StationBehavior), {"api": api})
    api.registerBehavior(Rules.STATION_ID, Rules.BOARD_BLOCKS, behaviorClass)
    return behaviorClass
