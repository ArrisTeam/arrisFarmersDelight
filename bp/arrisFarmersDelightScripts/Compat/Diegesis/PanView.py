# -*- coding: utf-8 -*-
"""PanView - 煎锅站点的客户端表现：俯看锅里、锅里的食物、颠锅时食物跳起来转半圈落回、底部物品栏抽屉（客户端）

对应 Hands-On Delight：client/SkilletBehavior.java 的简化版（锅不动，颠锅时食物跳起来转半圈落回锅里）：
- 在锅上按住往上一甩 = 颠锅翻面（toss，力度看甩多远，手势见 PanGesture.py）；点一下 = 取出（take）；
- 点底部抽屉的格子 = 把快捷栏那叠放进锅（place）；顶部徽章显示锅里的东西和贴锅这面的进度，底部一行提示说下一步做什么。
开站期间本客户端不画 Client/BlockItems 那份（hide），由这里画能跳起来的食物；关站时还原。
"""
import math

from .PanGesture import PanGesture
from . import BookSources
from ...Client import BlockItems
from ...Shared.Rules import PanStation as Rules

CAMERA = {"pos": (8.0, 19.0, -2.5), "target": (8.0, 1.5, 7.5), "fov": 50.0}
MIDDLE = 8.0
FLOOR_Y = 1.85                    # 食物躺在锅底（1.5 像素）上
FOOD_SCALE = 0.8
PIECES = ((0.0, 0.0), (-2.2, 1.6), (2.0, -1.8))   # 最多画 3 块（离锅心的 dx, dz）
PAN_BOX = ((2.0, 0.0, 2.0), (14.0, 5.0, 14.0))
HOP_SECONDS = 0.55
HOP_HEIGHT = 7.0
HINT_SECONDS = 0.25
FLASH_SECONDS = 2.5
HINTS = {
    "not_food": "这个不能煎",
    "other_food": "锅里已经有别的东西：先点一下取出来",
    "full": "锅里放不下了（最多 16 个）",
}


class PanViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA

    def __init__(self, view):
        super(PanViewMixin, self).__init__(view)
        self.pieces, self.pieceKey = [], None
        self.gesture = PanGesture()
        self.clock = self.hintLeft = 0.0
        self.hop = None                   # (开始时刻, 力度)
        self.flash, self.shown = None, None

    # ---------------------------------------------------------------- 钩子

    def pickables(self):
        return [self.api.box("pan", PAN_BOX[0], PAN_BOX[1])]

    def onOpen(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, True)
        self._rebuild()
        BookSources.attach(self.view, "pan")

    def onClose(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, False)

    def onState(self, changes):
        if changes.data:
            self._rebuild()
            BookSources.refresh(self.view)

    def onEffect(self, name, data):
        if name == "drawer":
            self.view.drawer(data.get("items") or [])
        elif name == "tossed":
            self.hop = (self.clock, float(data.get("strength") or 0.5))
        elif name == "untossed":
            self._flash("还在空中，等它落下再颠")
        elif name == "fried":
            self._flash("煎好了！点一下取出")
        elif name == "hint":
            self._flash(HINTS.get(data.get("key"), ""))

    def onDrawer(self, index):
        self.view.sendAction("place", {"slot": int(index)})

    def onPointer(self, event):
        if event.kind == "down":
            if event.hit is not None:
                self.gesture.press(event.screen, self.clock)
        elif event.kind == "move":
            force = self.gesture.move(event.screen, self.clock)
            if force is not None:
                self.view.sendAction("toss", {"strength": round(force, 2)})
        elif event.kind == "up":
            if self.gesture.release(event.screen, self.clock) and self.view.data.get("item"):
                self.view.sendAction("take")

    def frame(self, dt):
        self.clock += dt
        if self.hop is not None:
            self._place()
        self.hintLeft -= dt
        if self.hintLeft <= 0.0:
            self.hintLeft = HINT_SECONDS
            self._showHint()

    # ---------------------------------------------------------------- 画

    def _rebuild(self):
        """锅里换了东西（或数量跨过 1、2、3）就换道具。"""
        data, props = self.view.data, self.view.props
        item = data.get("item") or {}
        count = min(len(PIECES), int(item.get("count") or 0)) if item.get("newItemName") else 0
        key = (item.get("newItemName"), item.get("newAuxValue") or 0, count)
        if key != self.pieceKey:
            for prop in self.pieces:
                props.remove(prop)
            one = {"newItemName": item.get("newItemName"), "newAuxValue": item.get("newAuxValue") or 0, "count": 1}
            self.pieces = [props.item(one, (MIDDLE + dx, FLOOR_Y, MIDDLE + dz), flat=True, scale=FOOD_SCALE)
                           for dx, dz in PIECES[:count]]
            self.pieceKey = key
        self._place()
        self.hintLeft = 0.0

    def _place(self):
        """食物躺在锅里；颠锅时整锅跳起来、在空中转半圈落回。"""
        lift, spin = 0.0, 0.0
        if self.hop is not None:
            progress = (self.clock - self.hop[0]) / HOP_SECONDS
            if progress >= 1.0:
                self.hop = None
            else:
                lift = HOP_HEIGHT * (0.4 + 0.6 * self.hop[1]) * 4.0 * progress * (1.0 - progress)
                spin = math.pi * progress
        for index, prop in enumerate(self.pieces):
            dx, dz = PIECES[index]
            angle = index * 1.3 + spin
            prop.move(center=(MIDDLE + dx, FLOOR_Y + index * 0.05 + lift, MIDDLE + dz), along=(math.cos(angle), math.sin(angle)))

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
    behaviorClass = type("SkilletBehavior", (PanViewMixin, api.StationBehavior), {"api": api})
    api.registerBehavior(Rules.STATION_ID, Rules.PAN_BLOCKS, behaviorClass)
    return behaviorClass
