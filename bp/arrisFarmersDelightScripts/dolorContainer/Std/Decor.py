# -*- coding: utf-8 -*-
"""
标准库：格子装饰（docs/ARCHITECTURE.md 第 3.3 节的 decorate；docs/DESIGN.md 第 3、7 节）。给格子类型的 decor 参数，
两端共用：锁住与布局两端的规则都按它算，画的部分（占位图标、覆盖条、底色、数量写法、锁住的样子、位置）客户端按它画。

    Decor(placeholder="textures/ui/empty_armor_slot_helmet")          空着时画原版的空盔甲格图标
    Decor(bar="progress", style=FILL, color=(1.0, 0.5, 0.1))         每格进度（Data.SlotValues(Data.Float(), 集合)，0–1）
    Decor(bar="heat", style=LINE, color="heatColor")                  颜色也可以来自每格数据（Data.SlotValues(Data.Int())，0xRRGGBB）
    Decor(tint=(0.2, 0.4, 1.0))                                       底格的颜色（颜色标记）
    Decor(count=abbreviate)                                           数量写成 1.2k、12k、1.2M
    Decor(locked="unlocked", lockHint="需要升级")                      锁住的格子：数据是 Data.Int（解锁了几格，格号不小于它的锁住）
                                                                      或 Data.SlotValues(Data.Bool())（为真的格锁住）
    Decor(layout="positions")                                         每格的位置（Data.SlotValues(Data.List(Data.Int()))：[x, y]）

锁住的格子不收不出，画成暗的、中间一把锁，悬停（空着时）写 lockHint（格式串或语言文件的键）。布局：数据里写了位置的格子摆到
那里（相对格子区的左上角，只对固定的格子区：grid、slot），没写的格子不在布局里，不收东西、空着时藏起来，有东西时留在原处、
拿得走（照工具台）。界面数据都要是这个集合的每格数据（锁住的也可以是一个整数），界面模型建好时核对。
"""
from ..Common import Data, Items
from ..Common.Slots import Decoration

FILL = "fill"   # 从下往上盖一层半透明的颜色（进度、熔化）
LINE = "line"   # 底边一道横条（热量、电量）
BAR_STYLES = (FILL, LINE)
WHITE = (1.0, 1.0, 1.0)


abbreviate = Items.shortCount   # 数量的缩写（照常见的存储界面）：999 以下照写，1.2k、12k、123k、1.2M、12M、1.2G


def _color(value):
    """0xRRGGBB 或 (r, g, b)（0–1）-> (r, g, b)；不认识的为 None。"""
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return tuple(float(part) for part in value)
    if isinstance(value, int) and not isinstance(value, bool):
        return ((value >> 16 & 255) / 255.0, (value >> 8 & 255) / 255.0, (value & 255) / 255.0)
    return None


class Decor(object):
    """格子装饰（见模块说明）。各项都可以不写。"""

    def __init__(self, placeholder=None, bar=None, style=FILL, color=None, tint=None, count=None, locked=None,
                 lockHint=None, layout=None):
        if style not in BAR_STYLES:
            raise ValueError("bar style must be FILL or LINE: %r" % (style,))
        if count is not None and not callable(count):
            raise ValueError("count must be callable: %r" % (count,))
        for name, value in (("color", color), ("tint", tint)):
            if value is not None and not isinstance(value, str) and _color(value) is None:
                raise ValueError("%s must be (r, g, b), 0xRRGGBB or a data name: %r" % (name, value))
        self.placeholder = placeholder
        self.bar = bar
        self.style = style
        self.color = color
        self.tint = tint
        self.count = count
        self.locked = locked
        self.lockHint = lockHint
        self.layout = layout

    # ---------------------------------------------------------------- 规则（两端）

    def isLocked(self, ws, ref):
        if self.locked is None:
            return False
        value = ws.data(self.locked)
        if isinstance(value, dict):
            return bool(value.get(ref[1]))
        return isinstance(value, int) and ref[1] >= value

    def position(self, ws, ref):
        """布局里这一格的位置 (x, y)；不在布局里为 None（没有布局时也为 None）。"""
        if self.layout is None:
            return None
        entry = (ws.data(self.layout) or {}).get(ref[1])
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            return (entry[0], entry[1])
        return None

    def active(self, ws, ref):
        """收不收东西：锁住的、不在布局里的不收。"""
        if self.isLocked(ws, ref):
            return False
        return self.layout is None or self.position(ws, ref) is not None

    def takeable(self, ws, ref):
        """拿不拿得走：锁住的拿不走（不在布局里的拿得走）。"""
        return not self.isLocked(ws, ref)

    def hint(self, ws, ref):
        return self.lockHint if self.lockHint and self.isLocked(ws, ref) else None

    def check(self, menu, name):
        """界面模型建好时核对用到的界面数据。"""
        if self.bar is not None:
            menu.checkSlotData(name, self.bar, "Float")
        for value in (self.color, self.tint):
            if isinstance(value, str):
                menu.checkSlotData(name, value, "Int")
        if self.layout is not None:
            menu.checkSlotData(name, self.layout, "List")
        if self.locked is not None:
            field = menu.data.get(self.locked)
            if not isinstance(field, Data.Int):
                menu.checkSlotData(name, self.locked, "Bool")

    # ---------------------------------------------------------------- 画（客户端）

    def _colorAt(self, ws, ref, value):
        if isinstance(value, str):
            return _color((ws.data(value) or {}).get(ref[1]))
        return _color(value) if value is not None else None

    def render(self, ws, ref, stack):
        out = Decoration()
        empty = Items.isEmpty(stack)
        out.locked = self.isLocked(ws, ref)
        if empty and self.placeholder and not out.locked:
            out.placeholder = self.placeholder
        if self.bar is not None:
            value = (ws.data(self.bar) or {}).get(ref[1])
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                out.bar = (self.style, min(1.0, float(value)), self._colorAt(ws, ref, self.color) or WHITE)
        out.tint = self._colorAt(ws, ref, self.tint)
        if self.count is not None and not empty and Items.count(stack) > 1:
            out.count = self.count(Items.count(stack))
        if self.layout is not None:
            out.position = self.position(ws, ref)
            out.visible = out.position is not None or not empty
        return out
