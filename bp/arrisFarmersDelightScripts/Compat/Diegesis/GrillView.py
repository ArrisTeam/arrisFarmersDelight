# -*- coding: utf-8 -*-
"""GrillView - 炉灶站点的客户端表现：俯看灶台、六个烤位上的食物、翻面时跳起来转半圈、金线标出该翻的那件（客户端）

对应 Hands-On Delight：client/StoveBehavior.java 的简化版：
- 点一下烤位上的食物 = 翻面（turn）；烤好的点一下 = 取下（take）；点底部抽屉的格子 = 每个空烤位摆一件（place）；
- 该翻面的那件（贴灶台那面熟了、上面还生）远端画一道金色虚线（近端那排的会被底部抽屉挡住，实机）；底部一行提示说下一步做什么。
烤位按方块里的固定位置（Shared/Rules/BlockDisplay.STOVE_SLOTS）换到站点空间，从哪边打开都对得上。
开站期间本客户端不画 Client/BlockItems 那份（hide），关站时还原。
"""
import math

from . import BookSources
from ...Client import BlockItems
from ...Shared.Rules import GrillStation as Rules

CAMERA = {"pos": (8.0, 33.0, -2.0), "target": (8.0, 16.0, 8.0), "fov": 50.0}
TOP_Y = 16.3                      # 食物躺在灶台顶面（1 格高）上
FOOD_SCALE = 0.6
HALF = 2.2                        # 烤位命中盒的半宽
MARK_HALF = 1.8                   # 金线半长
HOP_SECONDS = 0.45
HOP_HEIGHT = 4.0
HINT_SECONDS = 0.25
FLASH_SECONDS = 2.0
HINTS = {"not_food": "这个不能烤", "full": "灶台上没有空位了"}


def _one(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": 1}


class GrillViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA

    def __init__(self, view):
        super(GrillViewMixin, self).__init__(view)
        self.pieces, self.marks, self.hops = {}, {}, {}
        self.centers = None
        self.clock = self.hintLeft = 0.0
        self.flash, self.shown = None, None

    # ---------------------------------------------------------------- 钩子

    def pickables(self):
        boxes = []
        for place in range(Rules.PLACES):
            x, y, z = self._center(place)
            boxes.append(self.api.box("place", (x - HALF, y - 0.5, z - HALF), (x + HALF, y + 1.5, z + HALF), payload=place))
        return boxes

    def onOpen(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, True)
        self._rebuild()
        BookSources.attach(self.view, "grill")

    def onClose(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, False)

    def onState(self, changes):
        if changes.data:
            self._rebuild()
            BookSources.refresh(self.view)

    def onEffect(self, name, data):
        if name == "drawer":
            self.view.drawer(data.get("items") or [])
        elif name == "turned" and isinstance(data.get("place"), int):
            self.hops[data["place"]] = self.clock
        elif name == "grilled":
            self._flash("烤好了：点一下取下")
        elif name == "hint":
            self._flash(HINTS.get(data.get("key"), ""))

    def onDrawer(self, index):
        self.view.sendAction("place", {"slot": int(index)})

    def onPointer(self, event):
        if event.kind != "down" or event.hit is None:
            return
        place = event.hit.node.payload
        slot = self._slot(place)
        if slot.get("item"):
            self.view.sendAction("take" if slot.get("done") else "turn", {"place": int(place)})

    def frame(self, dt):
        self.clock += dt
        if self.hops:
            self._place()
        self.hintLeft -= dt
        if self.hintLeft <= 0.0:
            self.hintLeft = HINT_SECONDS
            self._showHint()

    # ---------------------------------------------------------------- 画

    def _center(self, place):
        """第 place 个烤位的中心（站点像素）：方块里的固定位置换到站点空间。"""
        if self.centers is None:
            px, py, pz = self.view.pos
            self.centers = []
            for index in range(Rules.PLACES):
                fx, fz = Rules.slotCenter(index)
                sx, _, sz = self.view.toStation(px + fx, py + 1.0, pz + fz)
                self.centers.append((sx, TOP_Y, sz))
        return self.centers[place]

    def _slot(self, place):
        slots = self.view.data.get("slots") or []
        slot = slots[place] if 0 <= place < len(slots) else None
        return slot if isinstance(slot, dict) else {}

    def _rebuild(self):
        """哪个烤位换了东西就换那个道具；该翻的那件前面画金线。"""
        props = self.view.props
        for place in range(Rules.PLACES):
            slot = self._slot(place)
            item = slot.get("item") or {}
            key = (item.get("newItemName"), item.get("newAuxValue") or 0) if item.get("newItemName") else None
            old = self.pieces.get(place)
            if (old[0] if old else None) != key:
                if old:
                    props.remove(old[1])
                    del self.pieces[place]
                if key:
                    self.pieces[place] = (key, props.item(_one(item), self._center(place), flat=True, scale=FOOD_SCALE))
            waits, mark = Rules.waitsToTurn(slot), self.marks.get(place)
            if waits and mark is None:
                x, y, z = self._center(place)
                self.marks[place] = props.line((x - MARK_HALF, y - 0.2, z + HALF), (x + MARK_HALF, y - 0.2, z + HALF), hot=True)
            elif not waits and mark is not None:
                props.remove(mark)
                del self.marks[place]
        self._place()
        self.hintLeft = 0.0

    def _place(self):
        for place, (key, prop) in self.pieces.items():
            lift, spin = 0.0, 0.0
            start = self.hops.get(place)
            if start is not None:
                progress = (self.clock - start) / HOP_SECONDS
                if progress >= 1.0:
                    del self.hops[place]
                else:
                    lift, spin = HOP_HEIGHT * 4.0 * progress * (1.0 - progress), math.pi * progress
            x, y, z = self._center(place)
            prop.move(center=(x, y + lift, z), along=(math.cos(spin), math.sin(spin)))
        for place in list(self.hops):
            if place not in self.pieces:
                del self.hops[place]

    def _flash(self, text):
        self.flash = (text, self.clock + FLASH_SECONDS)
        self.hintLeft = 0.0

    def _showHint(self):
        flashing = self.flash is not None and self.clock < self.flash[1]
        text = self.flash[0] if flashing else Rules.statusText(self.view.data)
        if text != self.shown:
            self.shown = text
            self.view.hint(text)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记。"""
    behaviorClass = type("StoveBehavior", (GrillViewMixin, api.StationBehavior), {"api": api})
    api.registerBehavior(Rules.STATION_ID, Rules.STOVE_BLOCKS, behaviorClass)
    return behaviorClass
